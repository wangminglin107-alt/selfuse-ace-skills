"""Kernel-owned adapters from verified capability artifacts to scholarly gates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from research_skills_os.capabilities.citation_verification.gates import (
    evaluate_citation_verification,
)
from research_skills_os.capabilities.evidence_synthesis.gates import (
    evaluate_evidence_synthesis,
)
from research_skills_os.capabilities.literature_intelligence.gates import (
    evaluate_literature_artifacts,
)
from research_skills_os.capabilities.novelty_audit.gates import evaluate_novelty_audit
from research_skills_os.capabilities.paper_knowledge_base.gates import (
    evaluate_paper_knowledge_base,
)
from research_skills_os.capabilities.research_framing.gates import evaluate_research_brief
from research_skills_os.capabilities.theory_architecture.gates import (
    evaluate_theory_architecture,
)
from research_skills_os.core.artifacts.paths import resolve_project_path
from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import ArtifactEnvelope, GateResult

OVERCLAIM_PATTERN = re.compile(
    r"\b(first(?:-ever)? study|no prior studies|unstudied|unexplored|unprecedented)\b"
    r"|首次|首个|填补.{0,12}空白|从未.{0,12}研究",
    re.IGNORECASE,
)


def _load_mapping(project_root: Path, artifact: ArtifactEnvelope) -> Mapping[str, Any]:
    path = resolve_project_path(project_root, artifact.path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, Mapping) else {}


def _load_text(project_root: Path, artifact: ArtifactEnvelope | None) -> str:
    if artifact is None:
        return ""
    try:
        return resolve_project_path(project_root, artifact.path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _load_json(project_root: Path, artifact: ArtifactEnvelope | None) -> Mapping[str, Any]:
    if artifact is None:
        return {}
    try:
        raw = json.loads(
            resolve_project_path(project_root, artifact.path).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, Mapping) else {}


def _load_jsonl(project_root: Path, artifact: ArtifactEnvelope | None) -> list[Mapping[str, Any]]:
    if artifact is None:
        return []
    try:
        lines = (
            resolve_project_path(project_root, artifact.path)
            .read_text(encoding="utf-8")
            .splitlines()
        )
    except (OSError, UnicodeError):
        return [{"line 0": "JSONL artifact cannot be read"}]
    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            return [{f"line {line_number}": "malformed JSONL record"}]
        if not isinstance(raw, Mapping):
            return [{f"line {line_number}": "JSONL record must be an object"}]
        records.append(raw)
    return records


def _fail_gate(results: list[GateResult], gate_id: str, finding: str) -> list[GateResult]:
    return [
        result.model_copy(
            update={
                "status": GateStatus.FAIL,
                "findings": [*result.findings, finding],
                "remediation": [
                    *result.remediation,
                    "Remove the unsupported user-facing claim or add it to "
                    "verified metadata evidence.",
                ],
            }
        )
        if result.gate_id == gate_id
        else result
        for result in results
    ]


def _semantic_gate(gate_id: str, passed: bool, finding: str) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        severity=GateSeverity.BLOCKING,
        findings=[] if passed else [finding],
        remediation=[]
        if passed
        else ["Regenerate the declared writing artifact from verified inputs."],
    )


def evaluate_capability_artifacts(
    capability_id: str,
    project_root: Path,
    artifacts: list[ArtifactEnvelope],
) -> list[GateResult]:
    """Derive scholarly gate results from project-contained artifacts, never caller assertions."""

    by_type = {artifact.type: artifact for artifact in artifacts}
    if capability_id == "research-framing":
        metadata = by_type.get("research_brief_metadata")
        results = evaluate_research_brief(
            _load_mapping(project_root, metadata) if metadata is not None else {}
        )
        markdown = _load_text(project_root, by_type.get("research_brief_markdown"))
        if OVERCLAIM_PATTERN.search(markdown):
            return _fail_gate(
                results,
                "framing.claim_boundaries",
                "Research brief Markdown contains an unsupported novelty overclaim.",
            )
        return results
    if capability_id == "literature-intelligence":
        required = ("search_ledger", "source_registry", "evidence_map")
        loaded = [
            _load_mapping(project_root, by_type[item]) if item in by_type else {}
            for item in required
        ]
        return evaluate_literature_artifacts(*loaded)
    if capability_id == "novelty-audit":
        audit = by_type.get("novelty_audit")
        audit_mapping = _load_mapping(project_root, audit) if audit is not None else {}
        results = evaluate_novelty_audit(audit_mapping)
        matrix = _load_text(project_root, by_type.get("novelty_matrix"))
        if OVERCLAIM_PATTERN.search(matrix):
            results = _fail_gate(
                results,
                "novelty.evidence_support",
                "Novelty matrix contains an unsupported user-facing overclaim.",
            )
        verdict = audit_mapping.get("verdict")
        if isinstance(verdict, str) and verdict.casefold() not in matrix.casefold():
            results = _fail_gate(
                results,
                "novelty.verdict_consistency",
                "Novelty matrix does not report the authoritative audit verdict.",
            )
        return results
    if capability_id == "paper-knowledge-base":
        return evaluate_paper_knowledge_base(
            _load_json(project_root, by_type.get("document_index")),
            _load_json(project_root, by_type.get("corpus_status")),
        )
    if capability_id == "evidence-synthesis":
        return evaluate_evidence_synthesis(
            _load_jsonl(project_root, by_type.get("evidence_rows")),
            _load_json(project_root, by_type.get("synthesis_matrix")),
            _load_json(project_root, by_type.get("contradiction_ledger")),
            _load_json(project_root, by_type.get("coverage_report")),
        )
    if capability_id == "citation-verification":
        return evaluate_citation_verification(
            _load_json(project_root, by_type.get("citation_identity_audit")),
            _load_json(project_root, by_type.get("citation_support_audit")),
            _load_json(project_root, by_type.get("citation_blockers")),
        )
    if capability_id == "theory-architecture":
        return evaluate_theory_architecture(
            _load_json(project_root, by_type.get("theory_candidates")),
            _load_json(project_root, by_type.get("construct_map")),
            _load_json(project_root, by_type.get("theory_decision_packet")),
            _load_text(project_root, by_type.get("theory_rationale")),
        )
    if capability_id == "ssci-argument-architecture":
        argument = _load_text(project_root, by_type.get("paper_argument_map")).strip()
        outline = _load_text(project_root, by_type.get("section_outline")).strip()
        plan = _load_json(project_root, by_type.get("claim_evidence_plan"))
        ledger = _load_json(project_root, by_type.get("terminology_ledger"))
        raw_claims = plan.get("claims")
        claims: list[Any] = raw_claims if isinstance(raw_claims, list) else []
        raw_terms = ledger.get("terms")
        terms: list[Any] = raw_terms if isinstance(raw_terms, list) else []
        claim_coverage = bool(claims) and all(
            isinstance(claim, Mapping)
            and isinstance(claim.get("evidence_ids"), list)
            and bool(claim["evidence_ids"])
            for claim in claims
        )
        terminology_complete = bool(terms) and all(
            isinstance(term, Mapping)
            and all(
                isinstance(term.get(field), str) and term[field].strip()
                for field in ("zh", "en", "definition")
            )
            for term in terms
        )
        return [
            _semantic_gate(
                "writing.architecture_complete",
                bool(argument and outline and claims and terms),
                "Argument map, section outline, claim plan, or terminology ledger is incomplete.",
            ),
            _semantic_gate(
                "writing.claim_evidence_coverage",
                claim_coverage,
                "Every planned claim must name at least one verified evidence ID.",
            ),
            _semantic_gate(
                "writing.terminology_consistent",
                terminology_complete,
                "Every terminology entry requires Chinese, English, and a definition.",
            ),
        ]
    if capability_id == "ssci-section-drafting":
        manuscript = _load_text(
            project_root,
            by_type.get("revised_chinese_manuscript") or by_type.get("chinese_manuscript"),
        )
        trace = _load_json(project_root, by_type.get("draft_trace"))
        raw_claims = trace.get("claims")
        claims = raw_claims if isinstance(raw_claims, list) else []
        raw_anchors = trace.get("protected_anchors")
        anchors: list[Any] = raw_anchors if isinstance(raw_anchors, list) else []
        coverage = bool(claims) and all(
            isinstance(claim, Mapping)
            and isinstance(claim.get("evidence_ids"), list)
            and bool(claim["evidence_ids"])
            for claim in claims
        )
        anchors_preserved = bool(manuscript.strip()) and all(
            isinstance(anchor, str) and anchor in manuscript for anchor in anchors
        )
        return [
            _semantic_gate(
                "writing.claim_evidence_coverage",
                coverage,
                "Every drafted claim must retain at least one evidence ID.",
            ),
            _semantic_gate(
                "writing.protected_anchors_preserved",
                anchors_preserved,
                "The manuscript is empty or a protected meaning anchor is missing.",
            ),
            _semantic_gate(
                "writing.terminology_consistent",
                trace.get("terminology_status") == "pass",
                "The draft trace does not confirm terminology consistency.",
            ),
        ]
    if capability_id == "academic-prose-style-audit":
        prose_report = _load_json(project_root, by_type.get("prose_style_report"))
        matrix = _load_text(project_root, by_type.get("prose_revision_matrix"))
        metrics = prose_report.get("metrics")
        coverage = (
            isinstance(metrics, Mapping)
            and isinstance(metrics.get("character_count"), int)
            and metrics["character_count"] > 0
            and bool(matrix.strip())
        )
        anchors_preserved = (
            prose_report.get("ok") is True and prose_report.get("missing_anchors") == []
        )
        return [
            _semantic_gate(
                "style.coverage",
                coverage,
                "Style metrics or the bounded revision matrix is missing.",
            ),
            _semantic_gate(
                "style.protected_anchors",
                anchors_preserved,
                "The style report records one or more missing protected anchors.",
            ),
        ]
    if capability_id == "ssci-revision-audit":
        revision_audit_text = _load_text(project_root, by_type.get("revision_audit"))
        blockers = _load_json(project_root, by_type.get("revision_blockers"))
        regressions = blockers.get("regressions")
        regression_states = regressions if isinstance(regressions, Mapping) else {}
        gates = {
            "revision.argument_regression": "argument",
            "revision.evidence_regression": "evidence",
            "revision.terminology_regression": "terminology",
            "revision.protected_anchor_regression": "protected_anchors",
        }
        return [
            _semantic_gate(
                gate_id,
                bool(revision_audit_text.strip()) and regression_states.get(field) == "pass",
                f"The revision audit does not record a passing {field} regression check.",
            )
            for gate_id, field in gates.items()
        ]
    if capability_id == "ssci-peer-review":
        peer_report_text = _load_text(project_root, by_type.get("peer_review_report"))
        review_ledger = _load_json(project_root, by_type.get("reviewer_issue_ledger"))
        setup = review_ledger.get("review_setup")
        raw_issues = review_ledger.get("issues")
        issues: list[Any] = raw_issues if isinstance(raw_issues, list) else []
        material_limits = (
            bool(peer_report_text.strip())
            and isinstance(setup, Mapping)
            and isinstance(setup.get("material_received"), list)
            and bool(setup["material_received"])
            and isinstance(setup.get("unassessable_items"), list)
        )
        issue_fields = {
            "concern_id",
            "severity",
            "location",
            "evidence_pointer",
            "concern",
            "resolution_test",
        }
        issue_traceability = bool(issues) and all(
            isinstance(issue, Mapping)
            and all(
                isinstance(issue.get(field), str) and issue[field].strip() for field in issue_fields
            )
            for issue in issues
        )
        recommendation = review_ledger.get("recommendation")
        severity_calibrated = recommendation in {
            "Reject",
            "Major Revision",
            "Minor Revision",
            "Accept",
        } and all(
            isinstance(issue, Mapping) and issue.get("severity") in {"P0", "P1", "P2"}
            for issue in issues
        )
        return [
            _semantic_gate(
                "review.material_limits",
                material_limits,
                "Peer review must record received and unassessable material.",
            ),
            _semantic_gate(
                "review.issue_traceability",
                issue_traceability,
                "Every reviewer issue requires a location, evidence pointer, and resolution test.",
            ),
            _semantic_gate(
                "review.severity_calibration",
                severity_calibrated,
                "Recommendation or issue severity is outside the review contract.",
            ),
        ]
    return []
