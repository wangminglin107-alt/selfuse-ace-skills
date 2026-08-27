from __future__ import annotations

from pathlib import Path

from research_skills_os.core.registry.loader import RegistryLoader

ROOT = Path(__file__).parents[2]
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOWS = ROOT / "src" / "research_skills_os" / "workflows"
SKILLS = ROOT / "skills"


def catalog():
    return RegistryLoader(capability_roots=[CAPABILITIES], workflow_roots=[WORKFLOWS]).load()


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
    skill = (SKILLS / "ssci-section-drafting" / "SKILL.md").read_text(encoding="utf-8")
    assert "references/theoretical-note.md" in skill
    assert "references/zh-style.md" in skill
    assert "does not select theory" in skill


def test_bilingual_writing_aligns_meaning_without_owning_drafting() -> None:
    spec = catalog().capabilities["ssci-bilingual-writing"]

    assert {"chinese_manuscript", "terminology_ledger"} <= set(spec.input_types)
    assert set(spec.output_types) == {
        "english_manuscript",
        "translated_abstract",
        "bilingual_alignment_report",
    }
    assert "chinese_manuscript" not in spec.output_types


def test_revision_audit_reports_internal_regressions_without_rewriting() -> None:
    spec = catalog().capabilities["ssci-revision-audit"]

    assert {"revised_chinese_manuscript", "prose_style_report"} <= set(spec.input_types)
    assert set(spec.output_types) == {"revision_audit", "revision_blockers"}
    assert not ({"chinese_manuscript", "revised_chinese_manuscript"} & set(spec.output_types))


def test_peer_review_is_external_and_has_no_rewrite_output() -> None:
    spec = catalog().capabilities["ssci-peer-review"]

    assert {"revised_chinese_manuscript", "revision_audit"} <= set(spec.input_types)
    assert set(spec.output_types) == {"peer_review_report", "reviewer_issue_ledger"}
    assert not ({"chinese_manuscript", "revised_chinese_manuscript"} & set(spec.output_types))
