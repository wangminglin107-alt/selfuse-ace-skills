"""Deterministic gates for evidence-bounded and human-owned theory decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from research_skills_os.capabilities.theory_architecture.models import (
    ConstructMap,
    TheoryCandidates,
    TheoryDecisionPacket,
)
from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult


def _result(gate_id: str, findings: list[str] | None = None) -> GateResult:
    issues = findings or []
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=GateStatus.FAIL if issues else GateStatus.PASS,
        severity=GateSeverity.BLOCKING,
        findings=issues,
        remediation=["Revise the theory packet or keep the recommendation descriptive."]
        if issues
        else [],
    )


def _not_applicable(gate_id: str) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=GateStatus.NOT_APPLICABLE,
        severity=GateSeverity.BLOCKING,
    )


def _validation_findings(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]


def evaluate_theory_architecture(
    candidates: Mapping[str, Any],
    constructs: Mapping[str, Any],
    decision: Mapping[str, Any],
    rationale: str,
) -> list[GateResult]:
    """Validate evidence fit while preserving descriptive and user-owned decisions."""

    try:
        parsed_candidates = TheoryCandidates.model_validate(candidates)
        parsed_constructs = ConstructMap.model_validate(constructs)
        parsed_decision = TheoryDecisionPacket.model_validate(decision)
        if not rationale.strip():
            raise ValueError("theory rationale must not be empty")
    except (ValidationError, ValueError) as exc:
        findings = _validation_findings(exc) if isinstance(exc, ValidationError) else [str(exc)]
        return [
            _result("theory.required", findings),
            _not_applicable("theory.evidence_fit"),
            _not_applicable("theory.construct_consistency"),
            _not_applicable("theory.level_consistency"),
            _not_applicable("theory.contradictions_acknowledged"),
            _not_applicable("theory.no_forced_theory"),
            _not_applicable("theory.user_decision"),
        ]

    required = _result("theory.required")
    known_evidence = set(parsed_constructs.known_evidence_row_ids)
    evidence_findings: list[str] = []
    for candidate in parsed_candidates.candidates:
        unknown = sorted(set(candidate.evidence_row_ids) - known_evidence)
        if unknown:
            evidence_findings.append(
                f"candidate {candidate.candidate_id} references unknown evidence: "
                f"{', '.join(unknown)}."
            )
        if not candidate.assumptions:
            evidence_findings.append(
                f"candidate {candidate.candidate_id} leaves assumptions hidden."
            )
    for construct in parsed_constructs.constructs:
        unknown = sorted(set(construct.evidence_row_ids) - known_evidence)
        if unknown:
            evidence_findings.append(
                f"construct {construct.construct_id} references unknown evidence: "
                f"{', '.join(unknown)}."
            )
    for relation in parsed_constructs.relations:
        unknown = sorted(set(relation.evidence_row_ids) - known_evidence)
        if unknown:
            evidence_findings.append(
                "construct relation references unknown evidence: " + ", ".join(unknown) + "."
            )
    evidence_fit = _result("theory.evidence_fit", evidence_findings)

    construct_findings: list[str] = []
    known_constructs = {construct.construct_id for construct in parsed_constructs.constructs}
    for candidate in parsed_candidates.candidates:
        unknown = sorted(set(candidate.construct_ids) - known_constructs)
        if unknown:
            construct_findings.append(
                f"candidate {candidate.candidate_id} references unknown constructs: "
                f"{', '.join(unknown)}."
            )
        if len(candidate.theories) > 1 and not (
            candidate.compatibility_rationale and candidate.compatibility_rationale.strip()
        ):
            construct_findings.append(
                f"candidate {candidate.candidate_id} integrates theories without "
                "compatibility rationale."
            )
    for relation in parsed_constructs.relations:
        unknown_construct_ids = {
            relation.from_construct_id,
            relation.to_construct_id,
        } - known_constructs
        if unknown_construct_ids:
            construct_findings.append(
                "relation references unknown constructs: "
                + ", ".join(sorted(unknown_construct_ids))
                + "."
            )
    construct_consistency = _result("theory.construct_consistency", construct_findings)

    level_findings: list[str] = []
    level_by_construct = {
        construct.construct_id: construct.level_of_analysis
        for construct in parsed_constructs.constructs
    }
    for relation in parsed_constructs.relations:
        from_level = level_by_construct.get(relation.from_construct_id)
        to_level = level_by_construct.get(relation.to_construct_id)
        if (
            from_level
            and to_level
            and from_level != to_level
            and not (relation.cross_level_rationale and relation.cross_level_rationale.strip())
        ):
            level_findings.append(
                f"relation {relation.from_construct_id}->{relation.to_construct_id} "
                "crosses levels without rationale."
            )
    level_consistency = _result("theory.level_consistency", level_findings)

    contradiction_findings: list[str] = []
    material = set(parsed_constructs.material_contradiction_ids)
    decision_acknowledged = set(parsed_decision.acknowledged_contradiction_ids)
    missing_decision = sorted(material - decision_acknowledged)
    if missing_decision:
        contradiction_findings.append(
            "decision omits material contradictions: " + ", ".join(missing_decision) + "."
        )
    for candidate in parsed_candidates.candidates:
        missing = sorted(material - set(candidate.acknowledged_contradiction_ids))
        if missing:
            contradiction_findings.append(
                f"candidate {candidate.candidate_id} omits material contradictions: "
                f"{', '.join(missing)}."
            )
    contradictions = _result("theory.contradictions_acknowledged", contradiction_findings)

    no_forced_findings: list[str] = []
    if parsed_decision.recommendation != "descriptive":
        candidate_ids = {candidate.candidate_id for candidate in parsed_candidates.candidates}
        if not candidate_ids:
            no_forced_findings.append("non-descriptive recommendation requires a candidate.")
        if parsed_decision.selected_candidate_id not in candidate_ids:
            no_forced_findings.append("recommended candidate is absent from the candidate set.")
    no_forced = _result("theory.no_forced_theory", no_forced_findings)

    user_findings: list[str] = []
    if parsed_decision.authorization_state == "selected" and not parsed_decision.user_decision_id:
        user_findings.append("selected theory requires a user decision ID.")
    user_decision = _result("theory.user_decision", user_findings)
    return [
        required,
        evidence_fit,
        construct_consistency,
        level_consistency,
        contradictions,
        no_forced,
        user_decision,
    ]
