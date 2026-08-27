"""Deterministic gates that keep novelty verdicts within verified evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_skills_os.capabilities.literature_intelligence.gates import EvidenceStatus
from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult


class NoveltyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateContribution(NoveltyModel):
    classification: Literal[
        "theoretical", "empirical", "methodological", "conceptual", "integrative"
    ]
    statement: str = Field(min_length=1)


class ComparisonDimension(NoveltyModel):
    dimension: str = Field(min_length=1)
    candidate_position: str = Field(min_length=1)
    nearest_work_position: str = Field(min_length=1)
    evidence_refs: list[str]


class NearestWork(NoveltyModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    verification_status: EvidenceStatus
    comparisons: list[ComparisonDimension] = Field(min_length=1)


class NoveltyClaim(NoveltyModel):
    claim_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    evidence_refs: list[str]
    certainty: Literal["low", "moderate", "high"]


class NoveltyAudit(NoveltyModel):
    schema_version: Literal["1.0"] = "1.0"
    research_question: str = Field(min_length=1)
    candidate_contribution: CandidateContribution
    nearest_work: list[NearestWork]
    novelty_claims: list[NoveltyClaim]
    verdict: Literal["defensible", "conditional", "insufficient_evidence", "contradicted"]
    verdict_rationale: str = Field(min_length=1)
    revision_recommendation: str | None
    search_absence_as_evidence: bool
    coverage_limits: list[str] = Field(min_length=1)


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


def _validation_findings(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]


def _source_id(evidence_ref: str) -> str:
    return evidence_ref.split("#", 1)[0]


def evaluate_novelty_audit(raw_audit: Mapping[str, Any]) -> list[GateResult]:
    """Evaluate required structure, evidence, certainty, and verdict independently."""

    try:
        audit = NoveltyAudit.model_validate(raw_audit)
    except ValidationError as exc:
        return [
            _result(
                "novelty.required",
                GateStatus.FAIL,
                findings=_validation_findings(exc),
                remediation=["Complete every required novelty-audit field."],
            ),
            _result("novelty.evidence_support", GateStatus.NOT_APPLICABLE),
            _result("novelty.certainty_consistency", GateStatus.NOT_APPLICABLE),
            _result("novelty.verdict_consistency", GateStatus.NOT_APPLICABLE),
        ]

    required = _result("novelty.required", GateStatus.PASS)
    status_by_source = {
        source.source_id: source.verification_status for source in audit.nearest_work
    }
    evidence_findings: list[str] = []
    if audit.search_absence_as_evidence:
        evidence_findings.append("Absence of search results is not evidence of novelty.")
    for source in audit.nearest_work:
        for comparison in source.comparisons:
            if not comparison.evidence_refs:
                evidence_findings.append(
                    "nearest-work comparison "
                    f"{source.source_id}/{comparison.dimension} lacks evidence."
                )
    for claim in audit.novelty_claims:
        if not claim.evidence_refs:
            evidence_findings.append(f"novelty claim {claim.claim_id} lacks evidence.")
        for evidence_ref in claim.evidence_refs:
            if _source_id(evidence_ref) not in status_by_source:
                evidence_findings.append(
                    f"novelty claim {claim.claim_id} references unknown evidence {evidence_ref}."
                )
    evidence_result = _result(
        "novelty.evidence_support",
        GateStatus.FAIL if evidence_findings else GateStatus.PASS,
        findings=evidence_findings,
        remediation=["Link each comparison and claim to inspected nearest-work evidence."]
        if evidence_findings
        else [],
    )

    certainty_findings: list[str] = []
    for claim in audit.novelty_claims:
        statuses = {
            status_by_source.get(_source_id(reference)) for reference in claim.evidence_refs
        }
        if claim.certainty == "high" and statuses != {"verified_content"}:
            certainty_findings.append(
                f"high-certainty claim {claim.claim_id} lacks exclusively verified content."
            )
        if claim.certainty == "moderate" and any(
            status not in {"verified_content", None} for status in statuses
        ):
            certainty_findings.append(
                f"moderate-certainty claim {claim.claim_id} relies on non-content verification."
            )
    certainty_result = _result(
        "novelty.certainty_consistency",
        GateStatus.FAIL if certainty_findings else GateStatus.PASS,
        findings=certainty_findings,
        remediation=["Lower certainty or verify the relevant source content."]
        if certainty_findings
        else [],
    )

    verdict_findings: list[str] = []
    if audit.verdict == "defensible" and (
        evidence_findings
        or audit.search_absence_as_evidence
        or not audit.nearest_work
        or not audit.novelty_claims
        or any(source.verification_status != "verified_content" for source in audit.nearest_work)
    ):
        verdict_findings.append("A defensible verdict requires verified-content nearest work.")
    if audit.verdict != "defensible" and not (
        audit.revision_recommendation and audit.revision_recommendation.strip()
    ):
        verdict_findings.append(
            f"{audit.verdict} verdict requires a concrete revision recommendation."
        )
    verdict_result = _result(
        "novelty.verdict_consistency",
        GateStatus.FAIL if verdict_findings else GateStatus.PASS,
        findings=verdict_findings,
        remediation=["Calibrate the verdict and recommend a bounded revision."]
        if verdict_findings
        else [],
    )
    return [required, evidence_result, certainty_result, verdict_result]
