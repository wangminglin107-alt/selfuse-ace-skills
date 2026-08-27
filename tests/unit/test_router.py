import pytest

from research_skills_os.core.contracts.enums import TargetKind
from research_skills_os.core.contracts.models import TargetRef
from research_skills_os.core.errors import UnknownTarget
from research_skills_os.core.registry.models import CapabilitySpec, RegistryCatalog, WorkflowSpec
from research_skills_os.core.router import Router


def catalog() -> RegistryCatalog:
    capability = CapabilitySpec(
        id="research-framing",
        version="1.0",
        input_types=["idea_memo"],
        output_types=["research_brief"],
    )
    workflow = WorkflowSpec(
        id="idea-to-novelty",
        version="1.0",
        entry_node="framing",
        terminal_nodes=["framing"],
        nodes=[{"id": "framing", "capability_id": "research-framing"}],
        edges=[],
    )
    return RegistryCatalog(
        capabilities={capability.id: capability}, workflows={workflow.id: workflow}
    )


@pytest.mark.parametrize(
    ("kind", "target_id", "expected_type"),
    [
        (TargetKind.CAPABILITY, "research-framing", CapabilitySpec),
        (TargetKind.WORKFLOW, "idea-to-novelty", WorkflowSpec),
    ],
)
def test_resolves_exact_target_kind_and_id(kind, target_id, expected_type):
    resolved = Router(catalog()).resolve(TargetRef(kind=kind, id=target_id))

    assert isinstance(resolved, expected_type)


def test_unknown_target_lists_registered_ids_without_fuzzy_match():
    with pytest.raises(UnknownTarget) as caught:
        Router(catalog()).resolve(TargetRef(kind=TargetKind.CAPABILITY, id="research-frame"))

    message = str(caught.value)
    assert "research-frame" in message
    assert "research-framing" in message
    assert "idea-to-novelty" not in message
