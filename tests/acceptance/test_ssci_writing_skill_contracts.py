from __future__ import annotations

from pathlib import Path

from research_skills_os.core.registry.loader import RegistryLoader

ROOT = Path(__file__).parents[2]
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOWS = ROOT / "src" / "research_skills_os" / "workflows"
SKILLS = ROOT / "skills"


def catalog():
    return RegistryLoader(
        capability_roots=[CAPABILITIES], workflow_roots=[WORKFLOWS]
    ).load()


def test_argument_architecture_consumes_upstream_theory_without_recreating_it() -> None:
    spec = catalog().capabilities["ssci-argument-architecture"]

    assert {
        "theory_decision_packet",
        "theory_rationale",
        "synthesis_matrix",
        "contradiction_ledger",
        "citation_support_audit",
        "evidence_rows",
    } <= set(spec.input_types)
    assert set(spec.output_types) == {
        "paper_argument_map",
        "section_outline",
        "claim_evidence_plan",
        "terminology_ledger",
    }
    assert "theory_candidates" not in spec.output_types


def test_section_drafting_is_the_only_registered_manuscript_writer() -> None:
    loaded = catalog()
    drafting = loaded.capabilities["ssci-section-drafting"]

    assert {
        "paper_argument_map",
        "section_outline",
        "claim_evidence_plan",
        "terminology_ledger",
        "evidence_rows",
        "citation_support_audit",
    } <= set(drafting.input_types)
    assert {"chinese_manuscript", "draft_trace", "author_input_needed"} <= set(
        drafting.output_types
    )
    owners = [
        spec.id
        for spec in loaded.capabilities.values()
        if "chinese_manuscript" in spec.output_types
    ]
    assert owners == ["ssci-section-drafting"]


def test_drafting_skill_routes_theoretical_note_and_chinese_style_on_demand() -> None:
    skill = (SKILLS / "ssci-section-drafting" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "references/theoretical-note.md" in skill
    assert "references/zh-style.md" in skill
    assert "does not select theory" in skill
