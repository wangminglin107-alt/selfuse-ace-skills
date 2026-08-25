"""Deterministic, evidence-bound checks for research brief metadata."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult


class BriefModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BoundedScope(BriefModel):
    status: Literal["known", "unknown"]
    value: str | None
    basis: str = Field(min_length=1)

    @model_validator(mode="after")
    def status_matches_value(self) -> BoundedScope:
        if self.status == "known" and not self.value:
            raise ValueError("known scope requires a value")
        if self.status == "unknown" and self.value is not None:
            raise ValueError("unknown scope cannot silently contain a value")
        return self


class Construct(BriefModel):
    name: str = Field(min_length=1)
    working_definition: str = Field(min_length=1)
    basis: str = Field(min_length=1)


class ProvisionalContribution(BriefModel):
    type: Literal["theoretical", "empirical", "methodological", "conceptual"]
    statement: str = Field(min_length=1)
    status: Literal["provisional"] = "provisional"


class FramingClaim(BriefModel):
    kind: Literal["framing", "empirical_observation", "literature", "novelty"]
    statement: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class ResearchBrief(BriefModel):
    schema_version: Literal["1.0"] = "1.0"
    phenomenon: str = Field(min_length=1)
    research_problem: str = Field(min_length=1)
    unit_of_analysis: str = Field(min_length=1)
    level_of_analysis: str = Field(min_length=1)
    population_context: BoundedScope
    temporal_scope: BoundedScope
    geographic_scope: BoundedScope
    constructs: list[Construct] = Field(min_length=1)
    research_questions: list[str] = Field(min_length=1)
    provisional_contribution: ProvisionalContribution
    assumptions: list[str]
    uncertainties: list[str]
    user_decisions: list[str]
    claims: list[FramingClaim] = Field(default_factory=list)


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


def evaluate_research_brief(raw_brief: Mapping[str, Any]) -> list[GateResult]:
    """Return every framing gate result without inventing missing metadata."""

    try:
        brief = ResearchBrief.model_validate(raw_brief)
    except ValidationError as exc:
        return [
            _result(
                "framing.required",
                GateStatus.FAIL,
                findings=_validation_findings(exc),
                remediation=["Record every required element or mark scope explicitly unknown."],
            ),
            _result("framing.scope_traceable", GateStatus.NOT_APPLICABLE),
            _result("framing.claim_boundaries", GateStatus.NOT_APPLICABLE),
        ]

    required = _result("framing.required", GateStatus.PASS)
    traceable_bases = {"user_input", "source_artifact", "user_decision"}
    scope_findings: list[str] = []
    for field_name in ("population_context", "temporal_scope", "geographic_scope"):
        scope = getattr(brief, field_name)
        if scope.status == "known" and scope.basis not in traceable_bases:
            scope_findings.append(f"{field_name} uses an untraceable model-supplied scope.")
        if scope.status == "unknown" and scope.basis != "explicit_unknown":
            scope_findings.append(f"{field_name} must record explicit_unknown as its basis.")
    scope_result = _result(
        "framing.scope_traceable",
        GateStatus.FAIL if scope_findings else GateStatus.PASS,
        findings=scope_findings,
        remediation=["Replace hidden guesses with user/source traceability or explicit unknowns."]
        if scope_findings
        else [],
    )

    claim_findings: list[str] = []
    for claim in brief.claims:
        if claim.kind == "novelty":
            claim_findings.append("Research framing cannot make a novelty claim.")
        elif claim.kind == "literature" and not claim.evidence_refs:
            claim_findings.append("A literature claim lacks evidence references.")
    claim_result = _result(
        "framing.claim_boundaries",
        GateStatus.FAIL if claim_findings else GateStatus.PASS,
        findings=claim_findings,
        remediation=["Remove novelty claims and link literature claims to verified evidence."]
        if claim_findings
        else [],
    )
    return [required, scope_result, claim_result]
