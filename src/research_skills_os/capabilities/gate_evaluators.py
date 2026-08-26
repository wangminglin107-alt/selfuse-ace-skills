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
from research_skills_os.core.contracts.enums import GateStatus
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
        lines = resolve_project_path(project_root, artifact.path).read_text(
            encoding="utf-8"
        ).splitlines()
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
    return []
