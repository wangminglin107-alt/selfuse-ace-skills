import json
import os
from pathlib import Path

import pytest

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.checkpoint.service import CheckpointService
from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import Checkpoint
from research_skills_os.core.errors import CheckpointIntegrityError
from research_skills_os.core.state.models import EventType, ProjectEvent
from research_skills_os.core.state.repository import StateRepository


def prepared_project(tmp_path: Path) -> tuple[Path, StateRepository]:
    project_root = tmp_path / "研究 project with spaces"
    artifact_path = project_root / "artifacts" / "research-framing" / "brief.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("brief\n", encoding="utf-8", newline="\n")
    store = ArtifactStore(project_root)
    envelope = store.register(
        "artifacts/research-framing/brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
    )
    repository = StateRepository(project_root)
    events = [
        ProjectEvent(
            event_id="event-1",
            type=EventType.PROJECT_INITIALIZED,
            payload={"project_id": "project-1", "goal": "Frame idea"},
        ),
        ProjectEvent(
            event_id="event-2",
            type=EventType.RUN_STARTED,
            payload={"run_id": "run-1"},
        ),
        ProjectEvent(
            event_id="event-3",
            type=EventType.TARGET_STARTED,
            payload={"target_id": "research-framing"},
        ),
        ProjectEvent(
            event_id="event-4",
            type=EventType.ARTIFACT_REGISTERED,
            payload={"artifact": envelope.model_dump(mode="json")},
        ),
        ProjectEvent(
            event_id="event-5",
            type=EventType.TARGET_COMPLETED,
            payload={"target_id": "research-framing"},
        ),
    ]
    for item in events:
        repository.append(item)
    return project_root, repository


def test_creates_valid_checkpoint_and_updates_pointer_after_target(tmp_path: Path):
    project_root, repository = prepared_project(tmp_path)
    service = CheckpointService(project_root, repository=repository)

    checkpoint = service.create(repository.load(), "research-framing")

    checkpoint_path = (
        project_root / ".research-os" / "checkpoints" / f"{checkpoint.checkpoint_id}.json"
    )
    stored = Checkpoint.model_validate(json.loads(checkpoint_path.read_text(encoding="utf-8")))
    assert stored == checkpoint
    assert service.current() == checkpoint
    assert (project_root / ".research-os" / "current-checkpoint").read_text(
        encoding="utf-8"
    ).strip() == checkpoint.checkpoint_id
    assert repository.load().current_checkpoint == checkpoint.checkpoint_id


def test_retains_previous_checkpoints_when_current_pointer_advances(tmp_path: Path):
    project_root, repository = prepared_project(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    first = service.create(repository.load(), "research-framing")

    second = service.create(repository.load(), "research-framing")

    assert first.checkpoint_id != second.checkpoint_id
    assert service.load(first.checkpoint_id) == first
    assert service.current() == second
    assert len(list((project_root / ".research-os" / "checkpoints").glob("*.json"))) == 2


def test_checkpoint_lists_only_latest_unresolved_gate_failures(tmp_path: Path):
    project_root, repository = prepared_project(tmp_path)
    for index, (gate_id, status) in enumerate(
        (
            ("writing.architecture_complete", GateStatus.FAIL),
            ("writing.architecture_complete", GateStatus.PASS),
            ("writing.terminology_consistent", GateStatus.PASS),
            ("writing.terminology_consistent", GateStatus.FAIL),
        ),
        start=6,
    ):
        repository.append(
            ProjectEvent(
                event_id=f"event-{index}",
                type=EventType.GATE_RECORDED,
                payload={
                    "gate_result": {
                        "gate_id": gate_id,
                        "gate_version": "1.0",
                        "status": status,
                        "severity": GateSeverity.BLOCKING,
                    }
                },
            )
        )
    service = CheckpointService(project_root, repository=repository)

    checkpoint = service.create(repository.load(), "research-framing")

    assert checkpoint.failed_gates == ["writing.terminology_consistent"]


def test_rejects_checkpoint_for_target_not_in_completed_state(tmp_path: Path):
    project_root, repository = prepared_project(tmp_path)
    service = CheckpointService(project_root, repository=repository)

    with pytest.raises(CheckpointIntegrityError, match="not completed"):
        service.create(repository.load(), "literature-intelligence")

    assert not (project_root / ".research-os" / "current-checkpoint").exists()


def test_pointer_replace_failure_preserves_previous_current_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    project_root, repository = prepared_project(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    first = service.create(repository.load(), "research-framing")
    real_replace = os.replace
    calls = 0

    def fail_pointer_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated pointer replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(
        "research_skills_os.core.checkpoint.service.os.replace", fail_pointer_replace
    )

    with pytest.raises(OSError, match="simulated pointer"):
        service.create(repository.load(), "research-framing")

    assert service.current() == first
    assert repository.load().current_checkpoint == first.checkpoint_id


def test_event_append_failure_rolls_pointer_back_to_previous_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    project_root, repository = prepared_project(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    first = service.create(repository.load(), "research-framing")

    def fail_event_append(event: ProjectEvent) -> ProjectEvent:
        raise OSError("simulated event append failure")

    monkeypatch.setattr(repository, "append", fail_event_append)

    with pytest.raises(OSError, match="simulated event"):
        service.create(repository.load(), "research-framing")

    assert service.current() == first
    assert repository.load().current_checkpoint == first.checkpoint_id
