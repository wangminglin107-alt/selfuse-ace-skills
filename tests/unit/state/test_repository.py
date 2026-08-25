from pathlib import Path

from research_skills_os.core.state.models import EventType, ProjectEvent, ProjectLifecycle
from research_skills_os.core.state.repository import StateRepository


def test_repository_replays_log_on_every_load(tmp_path: Path):
    repository = StateRepository(tmp_path)
    repository.append(
        ProjectEvent(
            event_id="event-1",
            type=EventType.PROJECT_INITIALIZED,
            payload={"project_id": "project-1", "goal": "Frame idea"},
        )
    )
    first = repository.load()
    repository.append(
        ProjectEvent(
            event_id="event-2",
            type=EventType.RUN_STARTED,
            payload={"run_id": "run-1"},
        )
    )

    second = repository.load()

    assert first.lifecycle is ProjectLifecycle.INITIALIZED
    assert first.active_run_id is None
    assert second.lifecycle is ProjectLifecycle.RUNNING
    assert second.active_run_id == "run-1"
    assert second.last_sequence == 2


def test_repository_uses_readable_project_state_directory(tmp_path: Path):
    repository = StateRepository(tmp_path)
    repository.append(
        ProjectEvent(
            event_id="event-1",
            type=EventType.PROJECT_INITIALIZED,
            payload={"project_id": "project-1", "goal": "Frame idea"},
        )
    )

    assert repository.event_log.path == tmp_path / ".research-os" / "events.jsonl"
    assert repository.event_log.path.read_text(encoding="utf-8").endswith("\n")
