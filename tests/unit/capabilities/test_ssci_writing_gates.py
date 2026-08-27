from __future__ import annotations

import json
from pathlib import Path

from research_skills_os.capabilities.gate_evaluators import evaluate_capability_artifacts
from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import GateStatus


def artifact(project: Path, name: str, artifact_type: str, content: str):
    path = project / "writing" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return ArtifactStore(project).register(
        path.relative_to(project).as_posix(),
        artifact_id=f"test-{artifact_type}",
        artifact_type=artifact_type,
        schema_version="1.0",
        producing_capability="ssci-argument-architecture",
        provenance_references=["user-input:test"],
    )


def test_argument_architecture_gates_are_derived_from_artifacts(tmp_path: Path) -> None:
    artifacts = [
        artifact(tmp_path, "argument.md", "paper_argument_map", "# Map\nA bounded argument."),
        artifact(tmp_path, "outline.md", "section_outline", "# Outline\nOne paragraph job."),
        artifact(
            tmp_path,
            "claims.json",
            "claim_evidence_plan",
            json.dumps(
                {"claims": [{"claim_id": "c1", "evidence_ids": ["row-1"]}]},
                ensure_ascii=False,
            ),
        ),
        artifact(
            tmp_path,
            "terms.json",
            "terminology_ledger",
            json.dumps(
                {
                    "terms": [
                        {
                            "id": "t1",
                            "zh": "聚合情绪",
                            "en": "aggregate sentiment",
                            "definition": "日级汇总",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
        ),
    ]

    results = evaluate_capability_artifacts("ssci-argument-architecture", tmp_path, artifacts)

    assert {result.gate_id for result in results} == {
        "writing.architecture_complete",
        "writing.claim_evidence_coverage",
        "writing.terminology_consistent",
    }
    assert all(result.status is GateStatus.PASS for result in results)


def test_argument_architecture_rejects_claims_without_evidence(tmp_path: Path) -> None:
    artifacts = [
        artifact(tmp_path, "argument.md", "paper_argument_map", "# Map\nBounded."),
        artifact(tmp_path, "outline.md", "section_outline", "# Outline\nBounded."),
        artifact(
            tmp_path,
            "claims.json",
            "claim_evidence_plan",
            json.dumps({"claims": [{"claim_id": "c1", "evidence_ids": []}]}),
        ),
        artifact(
            tmp_path,
            "terms.json",
            "terminology_ledger",
            json.dumps({"terms": [{"id": "t1", "zh": "术语", "en": "term", "definition": "定义"}]}),
        ),
    ]

    results = evaluate_capability_artifacts("ssci-argument-architecture", tmp_path, artifacts)

    coverage = next(
        result for result in results if result.gate_id == "writing.claim_evidence_coverage"
    )
    assert coverage.status is GateStatus.FAIL


def test_section_drafting_gates_check_trace_and_protected_anchors(tmp_path: Path) -> None:
    artifacts = [
        artifact(
            tmp_path,
            "draft.md",
            "chinese_manuscript",
            "账号类别—日聚合只支持关联解释。",
        ),
        artifact(
            tmp_path,
            "trace.json",
            "draft_trace",
            json.dumps(
                {
                    "claims": [{"claim_id": "c1", "evidence_ids": ["row-1"]}],
                    "protected_anchors": ["账号类别—日聚合"],
                    "terminology_status": "pass",
                },
                ensure_ascii=False,
            ),
        ),
    ]

    results = evaluate_capability_artifacts("ssci-section-drafting", tmp_path, artifacts)

    assert {result.gate_id for result in results} == {
        "writing.claim_evidence_coverage",
        "writing.protected_anchors_preserved",
        "writing.terminology_consistent",
    }
    assert all(result.status is GateStatus.PASS for result in results)


def test_section_drafting_rejects_missing_protected_anchor(tmp_path: Path) -> None:
    artifacts = [
        artifact(
            tmp_path,
            "draft.md",
            "revised_chinese_manuscript",
            "只支持关联解释。",
        ),
        artifact(
            tmp_path,
            "trace.json",
            "draft_trace",
            json.dumps(
                {
                    "claims": [{"claim_id": "c1", "evidence_ids": ["row-1"]}],
                    "protected_anchors": ["账号类别—日聚合"],
                    "terminology_status": "pass",
                },
                ensure_ascii=False,
            ),
        ),
    ]

    results = evaluate_capability_artifacts("ssci-section-drafting", tmp_path, artifacts)

    anchors = next(
        result for result in results if result.gate_id == "writing.protected_anchors_preserved"
    )
    assert anchors.status is GateStatus.FAIL


def test_style_audit_gates_require_metrics_matrix_and_preserved_anchors(
    tmp_path: Path,
) -> None:
    artifacts = [
        artifact(
            tmp_path,
            "style.json",
            "prose_style_report",
            json.dumps(
                {
                    "findings": [],
                    "metrics": {"character_count": 2000},
                    "protected_anchors": ["关联而非因果"],
                    "missing_anchors": [],
                    "ok": True,
                },
                ensure_ascii=False,
            ),
        ),
        artifact(
            tmp_path,
            "matrix.md",
            "prose_revision_matrix",
            "# Revision matrix\nNo blocking findings.",
        ),
    ]

    results = evaluate_capability_artifacts("academic-prose-style-audit", tmp_path, artifacts)

    assert {result.gate_id for result in results} == {
        "style.coverage",
        "style.protected_anchors",
    }
    assert all(result.status is GateStatus.PASS for result in results)


def test_revision_audit_gates_use_explicit_regression_states(tmp_path: Path) -> None:
    artifacts = [
        artifact(
            tmp_path,
            "audit.md",
            "revision_audit",
            "# Audit\n## Overall diagnosis\nBounded pilot.\n## Revision order\nNone.",
        ),
        artifact(
            tmp_path,
            "blockers.json",
            "revision_blockers",
            json.dumps(
                {
                    "blockers": [],
                    "regressions": {
                        "argument": "pass",
                        "evidence": "pass",
                        "terminology": "pass",
                        "protected_anchors": "pass",
                    },
                }
            ),
        ),
    ]

    results = evaluate_capability_artifacts("ssci-revision-audit", tmp_path, artifacts)

    assert {result.gate_id for result in results} == {
        "revision.argument_regression",
        "revision.evidence_regression",
        "revision.terminology_regression",
        "revision.protected_anchor_regression",
    }
    assert all(result.status is GateStatus.PASS for result in results)


def test_peer_review_gates_require_limits_traceable_issues_and_calibration(
    tmp_path: Path,
) -> None:
    artifacts = [
        artifact(
            tmp_path,
            "review.md",
            "peer_review_report",
            "# Review\n## Material limits\nNo data results.\n## Recommendation\nMajor Revision.",
        ),
        artifact(
            tmp_path,
            "issues.json",
            "reviewer_issue_ledger",
            json.dumps(
                {
                    "review_setup": {
                        "material_received": ["theoretical note"],
                        "unassessable_items": ["empirical results"],
                    },
                    "recommendation": "Major Revision",
                    "issues": [
                        {
                            "concern_id": "M-01",
                            "severity": "P1",
                            "location": "literature boundary",
                            "evidence_pointer": "three-source pilot",
                            "concern": "Coverage is too narrow for publication.",
                            "resolution_test": "Expand verified nearest-work coverage.",
                        }
                    ],
                }
            ),
        ),
    ]

    results = evaluate_capability_artifacts("ssci-peer-review", tmp_path, artifacts)

    assert {result.gate_id for result in results} == {
        "review.material_limits",
        "review.issue_traceability",
        "review.severity_calibration",
    }
    assert all(result.status is GateStatus.PASS for result in results)
