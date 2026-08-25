from pathlib import Path

import pytest

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import RunMode, RunStatus, TargetKind
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    TargetRef,
)
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.orchestrator.coordinator import ResumeDecision, RunCoordinator
from research_skills_os.core.orchestrator.stop_policy import StopAction
from research_skills_os.core.registry.models import CapabilitySpec, RegistryCatalog
from research_skills_os.core.state.models import ProjectLifecycle


def catalog(*, exit_gates: list[str] | None = None) -> RegistryCatalog:
    capability = CapabilitySpec(
        id="research-framing",
        version="1.0",
        input_types=[],
        output_types=["research_brief"],
        exit_gates=exit_gates or [],
    )
    return RegistryCatalog(capabilities={capability.id: capability})


def request(mode: RunMode) -> ExecutionRequest:
    return ExecutionRequest(
        request_id=f"request-{mode.value}",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="research-framing"),
        mode=mode,
        goal="Frame idea",
    )


def result_with_artifact(
    project_root: Path, run_id: str, *, provenance: bool = True
) -> ExecutionResult:
    path = project_root / "artifacts" / "research-framing" / "brief.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("brief\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project_root).register(
        "artifacts/research-framing/brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
        provenance_references=["user-input:idea-1"] if provenance else [],
    )
    return ExecutionResult(
        request_id="request-interactive",
        run_id=run_id,
        target_id="research-framing",
        status=RunStatus.COMPLETED,
        artifacts=[envelope],
    )


def test_interactive_completion_pauses_and_checkpoints(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog())
    context = coordinator.start(request(RunMode.INTERACTIVE))
    coordinator.begin_target(context.run_id, "research-framing")

    outcome = coordinator.complete_target(
        context.run_id, result_with_artifact(tmp_path, context.run_id)
    )

    state = coordinator.repository.load()
    assert outcome.action is StopAction.PAUSE
    assert outcome.checkpoint_id is not None
    assert state.lifecycle is ProjectLifecycle.PAUSED
    assert state.completed_targets == ["research-framing"]
    assert state.current_checkpoint == outcome.checkpoint_id
    assert coordinator.checkpoints.verify_resume(outcome.checkpoint_id).status == "verified"

    resumed = coordinator.resume(outcome.checkpoint_id, ResumeDecision.CONTINUE)
    assert resumed.lifecycle.value == "running"
    assert coordinator.repository.load().lifecycle is ProjectLifecycle.RUNNING


def test_autonomous_standalone_capability_completes_after_checkpoint(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog())
    execution_request = request(RunMode.AUTONOMOUS).model_copy(
        update={"request_id": "request-interactive"}
    )
    context = coordinator.start(execution_request)
    coordinator.begin_target(context.run_id, "research-framing")

    outcome = coordinator.complete_target(
        context.run_id, result_with_artifact(tmp_path, context.run_id)
    )

    assert outcome.action is StopAction.COMPLETE
    assert outcome.checkpoint_id is not None
    assert coordinator.repository.load().lifecycle is ProjectLifecycle.COMPLETED


def test_rejects_target_completion_when_declared_output_is_missing(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog())
    context = coordinator.start(request(RunMode.INTERACTIVE))
    coordinator.begin_target(context.run_id, "research-framing")
    empty = ExecutionResult(
        request_id="request-interactive",
        run_id=context.run_id,
        target_id="research-framing",
        status=RunStatus.COMPLETED,
    )

    with pytest.raises(InvalidStateTransition, match="research_brief"):
        coordinator.complete_target(context.run_id, empty)

    assert coordinator.repository.load().active_target == "research-framing"


def test_blocking_gate_preserves_artifact_but_rejects_target_completion(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog(exit_gates=["provenance.complete"]))
    context = coordinator.start(request(RunMode.INTERACTIVE))
    coordinator.begin_target(context.run_id, "research-framing")
    unsupported = result_with_artifact(tmp_path, context.run_id, provenance=False)

    outcome = coordinator.complete_target(context.run_id, unsupported)

    state = coordinator.repository.load()
    assert outcome.action is StopAction.BLOCK
    assert outcome.checkpoint_id is None
    assert state.lifecycle is ProjectLifecycle.BLOCKED
    assert state.completed_targets == []
    assert "brief-1" in state.artifacts


def test_failed_run_event_materializes_failed_terminal_state(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog())
    context = coordinator.start(request(RunMode.INTERACTIVE))

    coordinator.fail(context.run_id, "sanitized execution failure")

    state = coordinator.repository.load()
    assert state.lifecycle is ProjectLifecycle.FAILED
    assert state.active_run_id is None
