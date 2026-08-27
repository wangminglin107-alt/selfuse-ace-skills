from pathlib import Path

from research_skills_os.core.contracts.enums import RunMode, TargetKind
from research_skills_os.core.contracts.models import ExecutionRequest, TargetRef
from research_skills_os.core.orchestrator.stop_policy import StopAction, StopPolicy, StopSignals
from research_skills_os.core.registry.loader import RegistryLoader
from research_skills_os.core.router import Router

ROOT = Path(__file__).parents[2]
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOWS = ROOT / "src" / "research_skills_os" / "workflows"


def catalog():
    return RegistryLoader(capability_roots=[CAPABILITIES], workflow_roots=[WORKFLOWS]).load()


def test_literature_to_theory_has_only_composition_nodes_in_order():
    workflow = catalog().workflows["literature-to-theory"]

    assert [node.capability_id for node in workflow.nodes] == [
        "paper-knowledge-base",
        "evidence-synthesis",
        "citation-verification",
        "theory-architecture",
    ]
    assert workflow.entry_node == "knowledge-base"
    assert workflow.terminal_nodes == ["theory"]


def test_every_mapped_artifact_is_declared_by_its_producer():
    loaded = catalog()
    workflow = loaded.workflows["literature-to-theory"]
    by_node = {node.id: loaded.capabilities[node.capability_id] for node in workflow.nodes}

    for mapping in workflow.artifact_mappings:
        assert set(mapping.artifact_types) <= set(by_node[mapping.from_node].output_types)


def test_composed_capabilities_remain_directly_routable():
    loaded = catalog()
    router = Router(loaded)
    workflow = loaded.workflows["literature-to-theory"]

    for node in workflow.nodes:
        request = ExecutionRequest(
            request_id=f"standalone-{node.capability_id}",
            project_id="project-v2a",
            target=TargetRef(kind=TargetKind.CAPABILITY, id=node.capability_id),
            mode=RunMode.INTERACTIVE,
            goal="Direct V2A invocation",
        )
        assert router.resolve(request.target) is loaded.capabilities[node.capability_id]


def test_mode_stops_preserve_interactive_and_checkpointed_review():
    workflow = catalog().workflows["literature-to-theory"]
    theory = next(node for node in workflow.nodes if node.id == "theory")
    policy = StopPolicy()

    assert policy.decide(RunMode.INTERACTIVE, StopSignals()) is StopAction.PAUSE
    assert theory.human_review is True
    assert (
        policy.decide(RunMode.CHECKPOINTED, StopSignals(human_review=theory.human_review))
        is StopAction.PAUSE
    )
    assert (
        policy.decide(RunMode.CHECKPOINTED, StopSignals(conflicting_evidence=True))
        is StopAction.PAUSE
    )


def test_autonomous_mode_stops_at_theory_decision_packet():
    workflow = catalog().workflows["literature-to-theory"]
    theory = next(node for node in workflow.nodes if node.id == "theory")

    action = StopPolicy().decide(
        RunMode.AUTONOMOUS,
        StopSignals(is_terminal=True, autonomous_review=theory.autonomous_review),
    )

    assert theory.autonomous_review is True
    assert action is StopAction.PAUSE
