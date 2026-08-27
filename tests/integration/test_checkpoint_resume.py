from pathlib import Path

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.checkpoint.service import CheckpointService
from research_skills_os.core.state.models import EventType, ProjectEvent
from research_skills_os.core.state.repository import StateRepository


def project_with_completed_artifact(tmp_path: Path) -> tuple[Path, StateRepository, Path]:
    project_root = tmp_path / "research project 研究"
    artifact_path = project_root / "artifacts" / "research-framing" / "brief.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("original\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project_root).register(
        "artifacts/research-framing/brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
    )
    repository = StateRepository(project_root)
    for item in [
        ProjectEvent(
            event_id="event-1",
            type=EventType.PROJECT_INITIALIZED,
            payload={"project_id": "project-1", "goal": "Frame idea"},
        ),
        ProjectEvent(event_id="event-2", type=EventType.RUN_STARTED, payload={"run_id": "run-1"}),
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
    ]:
        repository.append(item)
    return project_root, repository, artifact_path


def test_resume_verifies_unchanged_state_and_artifacts(tmp_path: Path):
    project_root, repository, _ = project_with_completed_artifact(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    checkpoint = service.create(repository.load(), "research-framing")

    verification = service.verify_resume(checkpoint.checkpoint_id)

    assert verification.status == "verified"
    assert verification.state_matches is True
    assert [item.status for item in verification.artifacts] == ["verified"]
    assert verification.reasons == []


def test_resume_reports_artifact_hash_drift(tmp_path: Path):
    project_root, repository, artifact_path = project_with_completed_artifact(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    checkpoint = service.create(repository.load(), "research-framing")
    artifact_path.write_text("edited\n", encoding="utf-8", newline="\n")

    verification = service.verify_resume(checkpoint.checkpoint_id)

    assert verification.status == "drifted"
    assert verification.state_matches is True
    assert verification.artifacts[0].status == "drifted"
    assert "brief-1" in verification.reasons[0]


def test_resume_reports_project_state_drift(tmp_path: Path):
    project_root, repository, _ = project_with_completed_artifact(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    checkpoint = service.create(repository.load(), "research-framing")
    repository.append(
        ProjectEvent(
            event_id="event-later",
            type=EventType.DECISION_RECORDED,
            payload={
                "decision": {
                    "decision_id": "decision-later",
                    "description": "Narrow the sample.",
                    "made_by": "user",
                }
            },
        )
    )

    verification = service.verify_resume(checkpoint.checkpoint_id)

    assert verification.status == "drifted"
    assert verification.state_matches is False
    assert "project state" in verification.reasons[0]


def test_resume_reports_missing_artifact_without_losing_checkpoint(tmp_path: Path):
    project_root, repository, artifact_path = project_with_completed_artifact(tmp_path)
    service = CheckpointService(project_root, repository=repository)
    checkpoint = service.create(repository.load(), "research-framing")
    artifact_path.unlink()

    verification = service.verify_resume(checkpoint.checkpoint_id)

    assert verification.status == "drifted"
    assert verification.artifacts[0].status == "missing"
    assert "brief-1" in verification.reasons[0]
    assert service.load(checkpoint.checkpoint_id) == checkpoint


def test_later_checkpoint_detects_drift_in_an_earlier_dependency(tmp_path: Path):
    project_root, repository, framing_path = project_with_completed_artifact(tmp_path)
    literature_path = project_root / "artifacts" / "literature-intelligence" / "ledger.yaml"
    literature_path.parent.mkdir(parents=True)
    literature_path.write_text("queries: []\n", encoding="utf-8", newline="\n")
    literature = ArtifactStore(project_root).register(
        "artifacts/literature-intelligence/ledger.yaml",
        artifact_id="ledger-1",
        artifact_type="search_ledger",
        schema_version="1.0",
        producing_capability="literature-intelligence",
    )
    for item in [
        ProjectEvent(
            event_id="event-6",
            type=EventType.TARGET_STARTED,
            payload={"target_id": "literature-intelligence"},
        ),
        ProjectEvent(
            event_id="event-7",
            type=EventType.ARTIFACT_REGISTERED,
            payload={"artifact": literature.model_dump(mode="json")},
        ),
        ProjectEvent(
            event_id="event-8",
            type=EventType.TARGET_COMPLETED,
            payload={"target_id": "literature-intelligence"},
        ),
    ]:
        repository.append(item)

    service = CheckpointService(project_root, repository=repository)
    checkpoint = service.create(repository.load(), "literature-intelligence")
    framing_path.write_text("edited upstream framing\n", encoding="utf-8", newline="\n")

    verification = service.verify_resume(checkpoint.checkpoint_id)

    assert checkpoint.inputs_used == ["brief-1"]
    assert verification.status == "drifted"
    assert {item.artifact_id: item.status for item in verification.artifacts} == {
        "brief-1": "drifted",
        "ledger-1": "verified",
    }
