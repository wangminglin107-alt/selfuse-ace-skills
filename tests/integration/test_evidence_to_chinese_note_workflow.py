from __future__ import annotations

from pathlib import Path

from research_skills_os.core.contracts.enums import RunMode, TargetKind
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    InputArtifactRef,
    TargetRef,
)
from research_skills_os.core.orchestrator.coordinator import RunCoordinator
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

    assert {"chinese_manuscript", "draft_trace"} <= mappings[("draft", "citation-regression")]
    assert {"chinese_manuscript", "draft_trace"} <= mappings[("draft", "style-audit")]
    assert {"prose_style_report", "prose_revision_matrix"} <= mappings[
        ("style-audit", "constrained-revision")
    ]
    assert "revised_chinese_manuscript" in mappings[("constrained-revision", "revision-audit")]
    assert "revision_audit" in mappings[("revision-audit", "peer-review")]


def test_mode_stops_keep_interactive_and_checkpointed_control() -> None:
    _, workflow = load_workflow()

    assert workflow.mode_stops.interactive_after_each is True
    assert workflow.mode_stops.checkpointed_nodes == [
        "citation-regression",
        "constrained-revision",
    ]
    assert workflow.mode_stops.autonomous_terminal_only is True


def writing_request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id="writing-repeat-test",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.WORKFLOW, id="evidence-to-chinese-note"),
        mode=RunMode.AUTONOMOUS,
        goal="Exercise both drafting nodes",
        inputs=[
            InputArtifactRef(
                artifact_id="rows",
                type="evidence_rows",
                path_or_uri="artifacts/evidence.jsonl",
            ),
            InputArtifactRef(
                artifact_id="support",
                type="citation_support_audit",
                path_or_uri="artifacts/support.json",
            ),
        ],
    )


def test_repeated_capability_resolves_each_workflow_node_in_order(tmp_path: Path) -> None:
    catalog, _ = load_workflow()
    coordinator = RunCoordinator(tmp_path, catalog)
    request = writing_request()

    first = coordinator._select_workflow_node(
        request,
        "ssci-section-drafting",
        ["ssci-argument-architecture"],
    )
    second = coordinator._select_workflow_node(
        request,
        "ssci-section-drafting",
        [
            "ssci-argument-architecture",
            "draft",
            "citation-verification",
            "academic-prose-style-audit",
        ],
    )

    assert first.id == "draft"
    assert second.id == "constrained-revision"


def test_workflow_node_requires_only_initial_and_mapped_inputs(tmp_path: Path) -> None:
    catalog, _ = load_workflow()
    coordinator = RunCoordinator(tmp_path, catalog)
    request = writing_request()
    spec = catalog.capabilities["ssci-section-drafting"]
    node = coordinator._select_workflow_node(
        request,
        "ssci-section-drafting",
        ["ssci-argument-architecture"],
    )

    required = coordinator._required_input_types(request, spec, node)

    assert required == {
        "paper_argument_map",
        "section_outline",
        "claim_evidence_plan",
        "terminology_ledger",
        "evidence_rows",
        "citation_support_audit",
    }


def test_repeated_capability_requires_outputs_for_the_active_node_only(tmp_path: Path) -> None:
    catalog, _ = load_workflow()
    coordinator = RunCoordinator(tmp_path, catalog)
    request = writing_request()
    spec = catalog.capabilities["ssci-section-drafting"]
    first = coordinator._select_workflow_node(
        request,
        "ssci-section-drafting",
        ["ssci-argument-architecture"],
    )
    second = coordinator._select_workflow_node(
        request,
        "ssci-section-drafting",
        [
            "ssci-argument-architecture",
            "draft",
            "citation-verification",
            "academic-prose-style-audit",
        ],
    )

    assert coordinator._required_output_types(request, spec, first) == {
        "chinese_manuscript",
        "draft_trace",
    }
    assert coordinator._required_output_types(request, spec, second) == {
        "revised_chinese_manuscript",
        "draft_trace",
    }
