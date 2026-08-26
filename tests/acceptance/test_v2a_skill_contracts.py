import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SKILLS = ROOT / "skills"
CAPABILITY_CONTRACTS = {
    "paper-knowledge-base": (
        ["source_registry", "source_document"],
        ["document_index", "corpus_status"],
    ),
    "evidence-synthesis": (
        ["research_brief_metadata", "novelty_audit", "document_index"],
        ["evidence_rows", "synthesis_matrix", "contradiction_ledger", "coverage_report"],
    ),
    "citation-verification": (
        ["source_registry", "document_index", "evidence_rows"],
        ["citation_identity_audit", "citation_support_audit", "citation_blockers"],
    ),
    "theory-architecture": (
        [
            "research_brief_metadata",
            "novelty_audit",
            "synthesis_matrix",
            "contradiction_ledger",
            "citation_support_audit",
        ],
        ["theory_candidates", "construct_map", "theory_rationale", "theory_decision_packet"],
    ),
}
STATUS_FIELDS = [
    "Current goal:",
    "Current state:",
    "Smallest meaningful action:",
    "Result / blocker:",
    "One recommended next action:",
]


@pytest.mark.parametrize("skill_name", [*CAPABILITY_CONTRACTS, "literature-to-theory"])
def test_v2a_skill_exists_with_discoverable_frontmatter(skill_name: str):
    text = (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")

    assert text.startswith("---\n")
    assert f"name: {skill_name}" in text
    assert "description: Use when" in text


@pytest.mark.parametrize("skill_name", CAPABILITY_CONTRACTS)
def test_capability_skill_names_exact_inputs_outputs_and_status(skill_name: str):
    text = (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")
    inputs, outputs = CAPABILITY_CONTRACTS[skill_name]

    assert f"`{skill_name}`" in text
    for artifact_type in [*inputs, *outputs]:
        assert f"`{artifact_type}`" in text
    for field in STATUS_FIELDS:
        assert field in text


def test_evidence_skill_preserves_original_passage_and_locator():
    text = (SKILLS / "evidence-synthesis" / "SKILL.md").read_text(encoding="utf-8")

    assert "exact original-language passage" in text
    assert "page or stable section" in text
    assert "translation never replaces" in text


def test_theory_skill_keeps_selection_human_owned():
    text = (SKILLS / "theory-architecture" / "SKILL.md").read_text(encoding="utf-8")

    assert "authorization_state=proposed" in text
    assert "authorization_state=selected" in text
    assert "user decision ID" in text


def test_workflow_skill_routes_without_embedding_scholarly_rubrics():
    text = (SKILLS / "literature-to-theory" / "SKILL.md").read_text(encoding="utf-8")

    for capability_id in CAPABILITY_CONTRACTS:
        assert f"`{capability_id}`" in text
    for forbidden in (
        "synthesis.source_inference_boundary",
        "citation.content_support",
        "theory.construct_consistency",
        "evidence role rubric",
    ):
        assert forbidden not in text


def test_research_os_routes_v2a_and_preserves_autonomous_review_stop():
    text = (SKILLS / "research-os" / "SKILL.md").read_text(encoding="utf-8")

    assert "`literature-to-theory`" in text
    assert "explicit autonomous-review node" in text


def test_templates_are_valid_json_and_keep_exact_contract_fields():
    templates = [
        SKILLS / "paper-knowledge-base" / "assets" / "document-index.template.json",
        SKILLS / "evidence-synthesis" / "assets" / "evidence-row.template.json",
        SKILLS / "evidence-synthesis" / "assets" / "contradiction-ledger.template.json",
        SKILLS / "citation-verification" / "assets" / "citation-audit.template.json",
        SKILLS / "theory-architecture" / "assets" / "theory-decision.template.json",
    ]

    for template in templates:
        assert json.loads(template.read_text(encoding="utf-8"))


def test_skills_contain_no_insecure_or_fabrication_shortcuts():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SKILLS.rglob("SKILL.md")
        if path.parent.name in {*CAPABILITY_CONTRACTS, "literature-to-theory"}
    ).casefold()

    for forbidden in (
        "verify=false",
        "--insecure",
        "api_key=",
        "fabricate sources",
        "invent citations",
    ):
        assert forbidden not in combined
    fixed_quota = re.search(
        r"\b(?:exactly|at least)\s+\d+\s+(?:papers|sources|citations)\b", combined
    )
    assert fixed_quota is None
