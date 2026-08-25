import json
import subprocess
import sys
from pathlib import Path

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.checkpoint.service import CheckpointService
from research_skills_os.core.state.models import EventType, ProjectEvent
from research_skills_os.core.state.repository import StateRepository


def run_cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "research_skills_os.cli", *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def checkpointed_project(tmp_path: Path) -> tuple[Path, str, Path]:
    project = tmp_path / "checkpoint project 研究"
    artifact = project / "artifacts" / "fixture" / "result.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("original\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project).register(
        "artifacts/fixture/result.md",
        artifact_id="artifact-1",
        artifact_type="fixture_output",
        schema_version="1.0",
        producing_capability="fixture-capability",
        provenance_references=["user-input:fixture"],
    )
    repository = StateRepository(project)
    for event in (
        ProjectEvent(
            event_id="event-1",
            type=EventType.PROJECT_INITIALIZED,
            payload={"project_id": "project-1"},
        ),
        ProjectEvent(event_id="event-2", type=EventType.RUN_STARTED, payload={"run_id": "run-1"}),
        ProjectEvent(
            event_id="event-3",
            type=EventType.TARGET_STARTED,
            payload={"target_id": "fixture-capability"},
        ),
        ProjectEvent(
            event_id="event-4",
            type=EventType.ARTIFACT_REGISTERED,
            payload={"artifact": envelope.model_dump(mode="json")},
        ),
        ProjectEvent(
            event_id="event-5",
            type=EventType.TARGET_COMPLETED,
            payload={"target_id": "fixture-capability"},
        ),
        ProjectEvent(event_id="event-6", type=EventType.RUN_PAUSED, payload={"run_id": "run-1"}),
    ):
        repository.append(event)
    checkpoint = CheckpointService(project, repository=repository).create(
        repository.load(), "fixture-capability"
    )
    return project, checkpoint.checkpoint_id, artifact


def test_checkpoint_list_and_verify_emit_json(tmp_path: Path):
    project, checkpoint_id, _ = checkpointed_project(tmp_path)

    listed = run_cli("checkpoint", "list", "--project", str(project), cwd=tmp_path)
    verified = run_cli(
        "checkpoint", "verify", "--project", str(project), "--id", checkpoint_id, cwd=tmp_path
    )

    assert listed.returncode == 0, listed.stderr
    assert json.loads(listed.stdout)["checkpoints"][0]["checkpoint_id"] == checkpoint_id
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["status"] == "verified"


def test_drifted_checkpoint_returns_integrity_exit_code_four(tmp_path: Path):
    project, checkpoint_id, artifact = checkpointed_project(tmp_path)
    artifact.write_text("drifted\n", encoding="utf-8", newline="\n")

    verified = run_cli(
        "checkpoint", "verify", "--project", str(project), "--id", checkpoint_id, cwd=tmp_path
    )

    assert verified.returncode == 4
    assert json.loads(verified.stdout)["status"] == "drifted"
    assert "integrity" in verified.stderr.casefold()

