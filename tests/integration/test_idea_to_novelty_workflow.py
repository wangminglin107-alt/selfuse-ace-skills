from pathlib import Path

import pytest

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import (
    GateSeverity,
    GateStatus,
    RunMode,
    RunStatus,
    TargetKind,
)
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    GateResult,
    TargetRef,
)
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.orchestrator.coordinator import ResumeDecision, RunCoordinator
from research_skills_os.core.orchestrator.stop_policy import StopAction
from research_skills_os.core.registry.loader import RegistryLoader
from research_skills_os.core.registry.models import CapabilitySpec

ROOT = Path(__file__).parents[2]
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOWS = ROOT / "src" / "research_skills_os" / "workflows"
BUILTIN_GATES = {
    "contract.valid",
    "inputs.required",
    "artifacts.integrity",
    "provenance.complete",
    "uncertainty.explicit",
    "checkpoint.consistent",
    "provider.policy",
}


def catalog():
    return RegistryLoader(
        capability_roots=[CAPABILITIES],
        workflow_roots=[WORKFLOWS],
    ).load()


def workflow_request(mode: RunMode) -> ExecutionRequest:
    return ExecutionRequest(
        request_id=f"request-{mode.value}",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.WORKFLOW, id="idea-to-novelty"),
        mode=mode,
        goal="Develop an idea through a bounded novelty audit",
    )


def passing_result(
    project_root: Path,
    request: ExecutionRequest,
    run_id: str,
    spec: CapabilitySpec,
    *,
    provenance: bool = True,
) -> ExecutionResult:
    store = ArtifactStore(project_root)
    artifacts = []
    for index, artifact_type in enumerate(spec.output_types, start=1):
        relative = f"artifacts/{spec.id}/{artifact_type}.json"
        path = project_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{{"type":"{artifact_type}"}}\n', encoding="utf-8", newline="\n")
        artifacts.append(
            store.register(
                relative,
                artifact_id=f"{spec.id}-{index}",
                artifact_type=artifact_type,
                schema_version="1.0",
                producing_capability=spec.id,
                provenance_references=["user-input:idea-1"] if provenance else [],
            )
        )
    custom_gates = [
        GateResult(
            gate_id=gate_id,
            gate_version="1.0",
            status=GateStatus.PASS,
            severity=GateSeverity.BLOCKING,
        )
        for gate_id in spec.exit_gates
        if gate_id not in BUILTIN_GATES
    ]
    return ExecutionResult(
        request_id=request.request_id,
        run_id=run_id,
        target_id=spec.id,
        status=RunStatus.COMPLETED,
        artifacts=artifacts,
        gate_results=custom_gates,
    )


def start(tmp_path: Path, mode: RunMode):
    tmp_path.mkdir(parents=True, exist_ok=True)
    loaded = catalog()
    request = workflow_request(mode)
    coordinator = RunCoordinator(tmp_path, loaded)
    context = coordinator.start(request)
    return coordinator, loaded, request, context


def test_composed_nodes_use_the_same_registered_specs_as_standalone_routing(tmp_path: Path):
    coordinator, loaded, request, _ = start(tmp_path, RunMode.INTERACTIVE)
    workflow = coordinator.router.resolve(request.target)

    for node in workflow.nodes:
        standalone = TargetRef(kind=TargetKind.CAPABILITY, id=node.capability_id)
        assert coordinator.router.resolve(standalone) is loaded.capabilities[node.capability_id]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (RunMode.INTERACTIVE, [StopAction.PAUSE]),
        (RunMode.CHECKPOINTED, [StopAction.PAUSE]),
        (
            RunMode.AUTONOMOUS,
            [StopAction.CONTINUE, StopAction.CONTINUE, StopAction.COMPLETE],
        ),
    ],
)
def test_mode_specific_stops_and_per_node_checkpoints(
    tmp_path: Path, mode: RunMode, expected: list[StopAction]
):
    coordinator, loaded, request, context = start(tmp_path, mode)
    actions = []
    checkpoints = []

    for capability_id in ("research-framing", "literature-intelligence", "novelty-audit"):
        coordinator.begin_target(context.run_id, capability_id)
        outcome = coordinator.complete_target(
            context.run_id,
            passing_result(tmp_path, request, context.run_id, loaded.capabilities[capability_id]),
        )
        actions.append(outcome.action)
        checkpoints.append(outcome.checkpoint_id)
        if outcome.action is StopAction.PAUSE:
            break

    assert actions == expected
    assert all(checkpoints)


def test_autonomous_run_blocks_when_provenance_is_missing(tmp_path: Path):
    coordinator, loaded, request, context = start(tmp_path, RunMode.AUTONOMOUS)
    spec = loaded.capabilities["research-framing"]
    coordinator.begin_target(context.run_id, spec.id)

    outcome = coordinator.complete_target(
        context.run_id,
        passing_result(tmp_path, request, context.run_id, spec, provenance=False),
    )

    assert outcome.action is StopAction.BLOCK
    assert "provenance.complete" in {result.gate_id for result in outcome.gate_results}
    assert outcome.checkpoint_id is None


def test_resume_at_boundary_continues_with_next_node_without_rerunning_completed_node(
    tmp_path: Path,
):
    coordinator, loaded, request, context = start(tmp_path, RunMode.INTERACTIVE)
    framing = loaded.capabilities["research-framing"]
    coordinator.begin_target(context.run_id, framing.id)
    paused = coordinator.complete_target(
        context.run_id,
        passing_result(tmp_path, request, context.run_id, framing),
    )

    resumed = coordinator.resume(paused.checkpoint_id, ResumeDecision.CONTINUE)
    assert resumed.next_target_id == "literature-intelligence"
    coordinator.begin_target(context.run_id, resumed.next_target_id)
    assert coordinator.repository.load().completed_targets == ["research-framing"]


def test_drift_requires_explicit_rerun_and_returns_the_drifted_boundary(tmp_path: Path):
    coordinator, loaded, request, context = start(tmp_path, RunMode.INTERACTIVE)
    framing = loaded.capabilities["research-framing"]
    coordinator.begin_target(context.run_id, framing.id)
    paused = coordinator.complete_target(
        context.run_id,
        passing_result(tmp_path, request, context.run_id, framing),
    )
    checkpoint = coordinator.checkpoints.load(paused.checkpoint_id)
    drifted = tmp_path / checkpoint.artifacts_created[0].path
    drifted.write_text("changed\n", encoding="utf-8", newline="\n")

    with pytest.raises(InvalidStateTransition, match="explicit acceptance or rerun"):
        coordinator.resume(paused.checkpoint_id, ResumeDecision.CONTINUE)

    resumed = coordinator.resume(paused.checkpoint_id, ResumeDecision.RERUN)
    assert resumed.next_target_id == "research-framing"
    coordinator.begin_target(context.run_id, resumed.next_target_id)
    assert coordinator.repository.load().active_target == "research-framing"


def test_missing_capability_gate_result_blocks_instead_of_bypassing_gate(tmp_path: Path):
    coordinator, loaded, request, context = start(tmp_path, RunMode.AUTONOMOUS)
    framing = loaded.capabilities["research-framing"]
    coordinator.begin_target(context.run_id, framing.id)
    result = passing_result(tmp_path, request, context.run_id, framing).model_copy(
        update={"gate_results": []}
    )

    outcome = coordinator.complete_target(context.run_id, result)

    assert outcome.action is StopAction.BLOCK
    assert "framing.required" in {item.gate_id for item in outcome.gate_results}
