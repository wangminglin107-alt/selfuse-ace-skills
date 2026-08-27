"""Deterministic gates that preserve exact passages and contradictions."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from pydantic import TypeAdapter, ValidationError

from research_skills_os.capabilities.evidence_common import EvidenceRole
from research_skills_os.capabilities.evidence_synthesis.models import (
    ContradictionLedger,
    CoverageReport,
    EvidenceRow,
    SynthesisMatrix,
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
        remediation=["Repair the cited evidence artifact without deleting adverse evidence."]
        if issues
        else [],
    )


def _validation_findings(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]


def _not_applicable(gate_id: str) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=GateStatus.NOT_APPLICABLE,
        severity=GateSeverity.BLOCKING,
    )


def evaluate_evidence_synthesis(
    rows: list[Mapping[str, Any]],
    matrix: Mapping[str, Any],
    ledger: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> list[GateResult]:
    """Evaluate exact traceability, synthesis boundaries, conflicts, and coverage."""

    try:
        parsed_rows = TypeAdapter(list[EvidenceRow]).validate_python(rows)
        parsed_matrix = SynthesisMatrix.model_validate(matrix)
        parsed_ledger = ContradictionLedger.model_validate(ledger)
        parsed_coverage = CoverageReport.model_validate(coverage)
    except ValidationError as exc:
        return [
            _result("synthesis.required", _validation_findings(exc)),
            _not_applicable("synthesis.content_trace"),
            _not_applicable("synthesis.source_inference_boundary"),
            _not_applicable("synthesis.contradiction_preserved"),
            _not_applicable("synthesis.material_contradictions"),
            _not_applicable("synthesis.coverage"),
        ]

    required = _result("synthesis.required")

    trace_findings: list[str] = []
    known_sources = set(parsed_coverage.source_ids)
    for row in parsed_rows:
        if not row.exact_passage.strip():
            trace_findings.append(f"row {row.row_id} lacks an exact original passage.")
        expected_hash = sha256(row.exact_passage.encode("utf-8")).hexdigest()
        if row.locator.content_sha256 != expected_hash:
            trace_findings.append(f"row {row.row_id} exact-passage hash does not match locator.")
        if row.source_id not in known_sources:
            trace_findings.append(f"row {row.row_id} references unknown source {row.source_id}.")
        if row.reviewed_translation and not row.exact_passage.strip():
            trace_findings.append(f"row {row.row_id} translation replaces the original passage.")
    content_trace = _result("synthesis.content_trace", trace_findings)

    boundary_findings: list[str] = []
    for row in parsed_rows:
        same_statement = row.author_inference and (
            row.source_claim.strip().casefold() == row.author_inference.strip().casefold()
        )
        if same_statement:
            boundary_findings.append(
                f"row {row.row_id} collapses source claim and analyst inference."
            )
    source_boundary = _result("synthesis.source_inference_boundary", boundary_findings)

    rows_by_group: dict[str, list[EvidenceRow]] = defaultdict(list)
    for row in parsed_rows:
        rows_by_group[row.synthesis_group].append(row)
    ledger_groups = {entry.synthesis_group for entry in parsed_ledger.entries}
    contradiction_findings: list[str] = []
    for group_id, group_rows in rows_by_group.items():
        roles = {row.evidence_role for row in group_rows}
        has_opposition = EvidenceRole.SUPPORTS in roles and EvidenceRole.CONTRADICTS in roles
        if has_opposition and group_id not in ledger_groups:
            contradiction_findings.append(
                f"opposing evidence in synthesis group {group_id} lacks a contradiction entry."
            )
    known_rows = {row.row_id for row in parsed_rows}
    for entry in parsed_ledger.entries:
        unknown = sorted(set(entry.row_ids) - known_rows)
        if unknown:
            contradiction_findings.append(
                f"contradiction {entry.contradiction_id} references unknown rows: "
                f"{', '.join(unknown)}."
            )
    contradiction_preserved = _result("synthesis.contradiction_preserved", contradiction_findings)

    material_findings: list[str] = []
    for entry in parsed_ledger.entries:
        if entry.material and entry.resolution_state == "open":
            material_findings.append(
                f"material contradiction {entry.contradiction_id} remains unresolved."
            )
        if (
            not entry.material
            and entry.resolution_state == "open"
            and not (entry.boundary_note and entry.boundary_note.strip())
        ):
            material_findings.append(
                f"non-material contradiction {entry.contradiction_id} lacks a boundary note."
            )
    material_contradictions = _result("synthesis.material_contradictions", material_findings)

    coverage_findings: list[str] = []
    duplicate_rows = sorted(
        row_id for row_id, count in Counter(row.row_id for row in parsed_rows).items() if count > 1
    )
    if duplicate_rows:
        coverage_findings.append(f"duplicate evidence row IDs: {', '.join(duplicate_rows)}.")
    known_claims = set(parsed_coverage.downstream_claim_ids)
    for row in parsed_rows:
        unknown_claims = sorted(set(row.downstream_claim_ids) - known_claims)
        if unknown_claims:
            coverage_findings.append(
                f"row {row.row_id} references unknown downstream claims: "
                f"{', '.join(unknown_claims)}."
            )
    for matrix_group in parsed_matrix.groups:
        unknown = sorted(set(matrix_group.row_ids) - known_rows)
        if unknown:
            coverage_findings.append(
                f"matrix group {matrix_group.group_id} references unknown rows: "
                f"{', '.join(unknown)}."
            )
    if parsed_coverage.uncovered_dimensions:
        coverage_findings.append(
            "uncovered question dimensions: " + ", ".join(parsed_coverage.uncovered_dimensions)
        )
    coverage_result = _result("synthesis.coverage", coverage_findings)
    return [
        required,
        content_trace,
        source_boundary,
        contradiction_preserved,
        material_contradictions,
        coverage_result,
    ]
