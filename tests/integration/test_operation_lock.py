from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from threading import Barrier, BrokenBarrierError

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import RunMode, RunStatus, TargetKind
from research_skills_os.core.contracts.models import ExecutionRequest, ExecutionResult, TargetRef
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.orchestrator.coordinator import RunCoordinator
from research_skills_os.core.registry.models import CapabilitySpec, RegistryCatalog


def catalog() -> RegistryCatalog:
    capability = CapabilitySpec(
        id="fixture-capability",
        version="1.0",
        output_types=["fixture_output"],
    )
    return RegistryCatalog(capabilities={capability.id: capability})


def test_concurrent_completion_is_one_atomic_project_operation(tmp_path: Path, monkeypatch):
    coordinator = RunCoordinator(tmp_path, catalog())
    request = ExecutionRequest(
        request_id="request-1",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="fixture-capability"),
        mode=RunMode.AUTONOMOUS,
        goal="Exercise the operation lock",
    )
    context = coordinator.start(request)
    coordinator.begin_target(context.run_id, "fixture-capability")
    artifact_path = tmp_path / "artifacts" / "fixture" / "output.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{}\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(tmp_path).register(
        "artifacts/fixture/output.json",
        artifact_id="fixture-1",
        artifact_type="fixture_output",
        schema_version="1.0",
        producing_capability="fixture-capability",
        provenance_references=["user-input:fixture"],
    )
    result = ExecutionResult(
        request_id=request.request_id,
        run_id=context.run_id,
        target_id="fixture-capability",
        status=RunStatus.COMPLETED,
        artifacts=[envelope],
    )
    rendezvous = Barrier(2)

    def synchronized_evaluator(*_args, **_kwargs):
        with suppress(BrokenBarrierError):
            rendezvous.wait(timeout=0.5)
        return []

    monkeypatch.setattr(
        "research_skills_os.core.orchestrator.coordinator.evaluate_capability_artifacts",
        synchronized_evaluator,
    )

    def complete():
        instance = RunCoordinator(tmp_path, catalog())
        try:
            return instance.complete_target(context.run_id, result)
        except InvalidStateTransition as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: complete(), range(2)))

    assert sum(not isinstance(item, Exception) for item in outcomes) == 1
    assert sum(isinstance(item, InvalidStateTransition) for item in outcomes) == 1
    state = RunCoordinator(tmp_path, catalog()).repository.load()
    assert state.completed_targets == ["fixture-capability"]
    assert len(list((tmp_path / ".research-os" / "checkpoints").glob("*.json"))) == 1
