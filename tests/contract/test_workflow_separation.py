from pathlib import Path

import yaml

from research_skills_os.core.contracts.enums import RunMode, TargetKind
from research_skills_os.core.contracts.models import ExecutionRequest, TargetRef
from research_skills_os.core.registry.loader import RegistryLoader
from research_skills_os.core.router import Router

ROOT = Path(__file__).parents[2]
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOW = ROOT / "src" / "research_skills_os" / "workflows" / "idea_to_novelty" / "workflow.yaml"


def load_catalog():
    return RegistryLoader(
        capability_roots=[CAPABILITIES],
        workflow_roots=[WORKFLOW],
    ).load()


def test_workflow_is_only_composition_metadata():
    raw = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    serialized = yaml.safe_dump(raw).casefold()

    assert set(raw) == {
        "spec_version",
        "kind",
        "id",
        "version",
        "entry_node",
        "terminal_nodes",
        "nodes",
        "edges",
        "artifact_mappings",
        "global_gates",
        "mode_stops",
    }
    for forbidden in ("prompt", "rubric", "template", "scholarly_rules", "instructions"):
        assert forbidden not in serialized


def test_workflow_references_registered_capabilities_and_keeps_them_directly_routable():
    catalog = load_catalog()
    workflow = catalog.workflows["idea-to-novelty"]
    router = Router(catalog)

    assert [node.capability_id for node in workflow.nodes] == [
        "research-framing",
        "literature-intelligence",
        "novelty-audit",
    ]
    for capability_id in catalog.capabilities:
        request = ExecutionRequest(
            request_id=f"request-{capability_id}",
            project_id="project-1",
            target=TargetRef(kind=TargetKind.CAPABILITY, id=capability_id),
            mode=RunMode.INTERACTIVE,
            goal="Direct capability invocation",
        )
        assert router.resolve(request.target) == catalog.capabilities[capability_id]


def test_artifact_mappings_connect_nodes_without_copying_capability_contracts():
    catalog = load_catalog()
    workflow = catalog.workflows["idea-to-novelty"]

    assert [mapping.model_dump(mode="json") for mapping in workflow.artifact_mappings] == [
        {
            "from_node": "frame",
            "artifact_types": ["research_brief_markdown", "research_brief_metadata"],
            "to_node": "literature",
        },
        {
            "from_node": "literature",
            "artifact_types": ["search_ledger", "source_registry", "evidence_map"],
            "to_node": "novelty",
        },
    ]
