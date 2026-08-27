from __future__ import annotations

from pathlib import Path

from research_skills_os.core.registry.loader import RegistryLoader

ROOT = Path(__file__).parents[2]


def load_workflow():
    catalog = RegistryLoader(
        capability_roots=[ROOT / "src" / "research_skills_os" / "capabilities"],
        workflow_roots=[ROOT / "src" / "research_skills_os" / "workflows"],
    ).load()
    return catalog, catalog.workflows["evidence-to-chinese-note"]


def test_chinese_note_workflow_is_an_acyclic_seven_node_composition() -> None:
    _, workflow = load_workflow()

    assert [node.id for node in workflow.nodes] == [
        "architecture",
        "draft",
        "citation-regression",
        "style-audit",
        "constrained-revision",
        "revision-audit",
        "peer-review",
    ]
    assert workflow.entry_node == "architecture"
    assert workflow.terminal_nodes == ["peer-review"]
    assert all(node.checkpoint for node in workflow.nodes)


def test_workflow_reuses_drafting_but_keeps_every_capability_standalone() -> None:
    catalog, workflow = load_workflow()
    capability_ids = [node.capability_id for node in workflow.nodes]

    assert capability_ids.count("ssci-section-drafting") == 2
    assert set(capability_ids) <= set(catalog.capabilities)
    assert "evidence-to-chinese-note" not in catalog.capabilities


def test_revision_and_review_receive_explicit_traceable_artifacts() -> None:
    _, workflow = load_workflow()
    mappings = {
        (mapping.from_node, mapping.to_node): set(mapping.artifact_types)
        for mapping in workflow.artifact_mappings
    }

    assert {"chinese_manuscript", "draft_trace"} <= mappings[
        ("draft", "citation-regression")
    ]
    assert {"prose_style_report", "prose_revision_matrix"} <= mappings[
        ("style-audit", "constrained-revision")
    ]
    assert "revised_chinese_manuscript" in mappings[
        ("constrained-revision", "revision-audit")
    ]
    assert "revision_audit" in mappings[("revision-audit", "peer-review")]


def test_mode_stops_keep_interactive_and_checkpointed_control() -> None:
    _, workflow = load_workflow()

    assert workflow.mode_stops.interactive_after_each is True
    assert workflow.mode_stops.checkpointed_nodes == [
        "citation-regression",
        "constrained-revision",
    ]
    assert workflow.mode_stops.autonomous_terminal_only is True
