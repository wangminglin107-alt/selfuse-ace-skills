from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
PROJECT = ROOT / "projects" / "gsma-sentiment-engagement"
ARTIFACTS = PROJECT / "artifacts"
WRITING = PROJECT / "writing"
EXPECTED_SOURCES = {"norc-gsma-method", "brady-2017", "najafizada-2022"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def chinese_character_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def test_low_token_pilot_uses_three_verified_sources_and_authorized_theory() -> None:
    documents = load_json(ARTIFACTS / "document-index.json")["documents"]
    decision = load_json(ARTIFACTS / "theory-decision-packet.json")

    assert {document["source_id"] for document in documents} == EXPECTED_SOURCES
    assert all(document["content_availability"] == "full_text" for document in documents)
    assert decision["authorization_state"] == "selected"
    assert decision["user_decision_id"] == "gsma-theory-selected-20260827"


def test_chinese_note_is_a_small_evidence_traceable_experiment() -> None:
    manuscript = (WRITING / "chinese-research-note.md").read_text(encoding="utf-8")
    trace = load_json(WRITING / "draft-trace.json")

    assert 1800 <= chinese_character_count(manuscript) <= 2600
    assert "AUTHOR_INPUT_NEEDED" not in manuscript
    assert "因果效应" not in manuscript
    assert "证明了" not in manuscript
    assert {item["source_id"] for item in trace["sources"]} >= EXPECTED_SOURCES
    assert all(item["evidence_ids"] for item in trace["claims"])


def test_all_seven_workflow_boundaries_leave_reviewable_artifacts() -> None:
    expected = {
        "argument-map.md",
        "section-outline.md",
        "claim-evidence-plan.json",
        "terminology-ledger.json",
        "chinese-research-note.md",
        "draft-trace.json",
        "citation-regression.json",
        "prose-style-report.json",
        "prose-revision-matrix.md",
        "revised-chinese-research-note.md",
        "revision-audit.md",
        "peer-review.md",
        "reviewer-issue-ledger.json",
    }

    assert expected <= {path.name for path in WRITING.iterdir() if path.is_file()}


def test_audits_preserve_claim_strength_and_expose_pilot_limits() -> None:
    citation = load_json(WRITING / "citation-regression.json")
    style = load_json(WRITING / "prose-style-report.json")
    revision = (WRITING / "revision-audit.md").read_text(encoding="utf-8")
    review = (WRITING / "peer-review.md").read_text(encoding="utf-8")

    assert citation["records"]
    assert all(record["support_state"] == "supports" for record in citation["records"])
    assert style["ok"] is True
    assert style["missing_anchors"] == []
    assert "三篇" in revision
    assert "系统实验" in review
    assert "Major Revision" in review
