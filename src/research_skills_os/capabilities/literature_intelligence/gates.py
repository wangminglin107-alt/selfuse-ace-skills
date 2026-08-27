"""Deterministic traceability gates for offline-first literature intelligence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult


class LiteratureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchEntry(LiteratureModel):
    search_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    searched_at: datetime
    provider: str = Field(min_length=1)
    status: Literal["planned", "executed", "blocked"]
    result_count: int | None = Field(default=None, ge=0)

    @field_validator("searched_at")
    @classmethod
    def searched_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("searched_at must include timezone information")
        return value


class SearchLedger(LiteratureModel):
    schema_version: Literal["1.0"] = "1.0"
    search_question: str = Field(min_length=1)
    searches: list[SearchEntry] = Field(min_length=1)
    inclusion_criteria: list[str] = Field(min_length=1)
    exclusion_criteria: list[str] = Field(min_length=1)
    coverage_limits: list[str] = Field(min_length=1)
    blockers: list[str]


class SourceProvenance(LiteratureModel):
    provider: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    retrieved_at: datetime
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include timezone information")
        return value


EvidenceStatus = Literal[
    "candidate",
    "retrieved",
    "screened",
    "verified_metadata",
    "verified_content",
    "excluded",
]


class SourceRecord(LiteratureModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: EvidenceStatus
    decision: Literal["include", "exclude", "pending"]
    decision_reason: str = Field(min_length=1)
    provenance: SourceProvenance
    metadata_verification: Literal["unverified", "verified"]
    content_verification: Literal["unavailable", "unverified", "verified"]


class SourceRegistry(LiteratureModel):
    schema_version: Literal["1.0"] = "1.0"
    sources: list[SourceRecord]


class EvidenceLink(LiteratureModel):
    source_id: str = Field(min_length=1)
    relation: Literal["supports", "contradicts", "context", "partial"]
    evidence_note: str = Field(min_length=1)


class EvidenceClaim(LiteratureModel):
    claim_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    links: list[EvidenceLink] = Field(min_length=1)


class EvidenceMap(LiteratureModel):
    schema_version: Literal["1.0"] = "1.0"
    claims: list[EvidenceClaim]
    coverage_limits: list[str] = Field(min_length=1)
    unsupported_claims: list[str]


def _result(
    gate_id: str,
    status: GateStatus,
    *,
    findings: list[str] | None = None,
    remediation: list[str] | None = None,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=status,
        severity=GateSeverity.BLOCKING,
        findings=findings or [],
        remediation=remediation or [],
    )


def _findings(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]


def _validate(
    model: type[SearchLedger] | type[SourceRegistry] | type[EvidenceMap],
    raw: Mapping[str, Any],
) -> tuple[SearchLedger | SourceRegistry | EvidenceMap | None, list[str]]:
    try:
        return model.model_validate(raw), []
    except ValidationError as exc:
        return None, _findings(exc)


def _status_findings(registry: SourceRegistry) -> list[str]:
    findings: list[str] = []
    for source in registry.sources:
        metadata = source.metadata_verification
        content = source.content_verification
        consistent = {
            "candidate": metadata == "unverified" and content == "unavailable",
            "retrieved": metadata == "unverified" and content == "unverified",
            "screened": content == "unverified",
            "verified_metadata": metadata == "verified" and content != "verified",
            "verified_content": metadata == "verified" and content == "verified",
            "excluded": source.decision == "exclude",
        }[source.status]
        if not consistent:
            findings.append(
                f"source {source.source_id} collapses or contradicts metadata/content verification."
            )
        if (source.status == "excluded") != (source.decision == "exclude"):
            findings.append(f"source {source.source_id} has inconsistent exclusion status.")
    return findings


def evaluate_literature_artifacts(
    raw_ledger: Mapping[str, Any],
    raw_registry: Mapping[str, Any],
    raw_evidence_map: Mapping[str, Any],
) -> list[GateResult]:
    """Validate each artifact independently, then check cross-artifact traceability."""

    _ledger, ledger_findings = _validate(SearchLedger, raw_ledger)
    registry, registry_findings = _validate(SourceRegistry, raw_registry)
    evidence_map, map_findings = _validate(EvidenceMap, raw_evidence_map)
    search_result = _result(
        "literature.search_trace",
        GateStatus.FAIL if ledger_findings else GateStatus.PASS,
        findings=ledger_findings,
        remediation=["Record query, timestamp, provider, criteria, limits, and blockers."]
        if ledger_findings
        else [],
    )
    source_result = _result(
        "literature.source_trace",
        GateStatus.FAIL if registry_findings else GateStatus.PASS,
        findings=registry_findings,
        remediation=["Record screening reason, provenance, hash, and evidence status."]
        if registry_findings
        else [],
    )

    link_findings = list(map_findings)
    if isinstance(registry, SourceRegistry) and isinstance(evidence_map, EvidenceMap):
        source_ids = {source.source_id for source in registry.sources}
        for claim in evidence_map.claims:
            for link in claim.links:
                if link.source_id not in source_ids:
                    link_findings.append(
                        f"claim {claim.claim_id} links unknown source {link.source_id}."
                    )
    claim_result = _result(
        "literature.claim_links",
        GateStatus.FAIL if link_findings else GateStatus.PASS,
        findings=link_findings,
        remediation=["Link every material claim to a registered source or mark it unsupported."]
        if link_findings
        else [],
    )

    if isinstance(registry, SourceRegistry):
        status_findings = _status_findings(registry)
        status = GateStatus.FAIL if status_findings else GateStatus.PASS
    else:
        status_findings = []
        status = GateStatus.NOT_APPLICABLE
    status_result = _result(
        "literature.status_consistency",
        status,
        findings=status_findings,
        remediation=["Keep metadata verification separate from content verification."]
        if status_findings
        else [],
    )
    return [search_result, source_result, claim_result, status_result]
