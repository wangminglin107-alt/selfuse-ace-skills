from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.errors import ArtifactNotFound, ProjectPathViolation

FIXED_TIME = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
BRIEF_SHA256 = "13d68660d0fd520791f490f93d9449d34d51a061e70b0205f66c37ba8318f3ed"


def make_project(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "project with spaces 研究"
    artifact_path = project_root / "artifacts" / "research-framing" / "research-brief.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("brief\n", encoding="utf-8", newline="\n")
    return project_root, artifact_path


def test_registers_existing_artifact_without_copying_it(tmp_path: Path):
    project_root, artifact_path = make_project(tmp_path)
    store = ArtifactStore(project_root)

    envelope = store.register(
        "artifacts/research-framing/research-brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
        source_artifact_ids=["idea-1"],
        provenance_references=["user-input:idea-1"],
        human_edited=True,
        created_at=FIXED_TIME,
    )

    assert artifact_path.read_text(encoding="utf-8") == "brief\n"
    assert envelope.path == "artifacts/research-framing/research-brief.md"
    assert envelope.sha256 == BRIEF_SHA256
    assert envelope.source_artifact_ids == ["idea-1"]
    assert envelope.provenance_references == ["user-input:idea-1"]
    assert envelope.human_edited is True
    assert envelope.verification_state == "unverified"


def test_verifies_unchanged_artifact(tmp_path: Path):
    project_root, _ = make_project(tmp_path)
    store = ArtifactStore(project_root)
    envelope = store.register(
        "artifacts/research-framing/research-brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
    )

    verification = store.verify(envelope)

    assert verification.status == "verified"
    assert verification.expected_sha256 == BRIEF_SHA256
    assert verification.actual_sha256 == BRIEF_SHA256


def test_reports_hash_drift_after_artifact_edit(tmp_path: Path):
    project_root, artifact_path = make_project(tmp_path)
    store = ArtifactStore(project_root)
    envelope = store.register(
        "artifacts/research-framing/research-brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
    )
    artifact_path.write_text("changed\n", encoding="utf-8", newline="\n")

    verification = store.verify(envelope)

    assert verification.status == "drifted"
    assert verification.expected_sha256 == BRIEF_SHA256
    assert verification.actual_sha256 != BRIEF_SHA256


def test_refuses_to_register_missing_artifact(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    store = ArtifactStore(project_root)

    with pytest.raises(ArtifactNotFound):
        store.register(
            "artifacts/missing.md",
            artifact_id="missing-1",
            artifact_type="research_brief",
            schema_version="1.0",
            producing_capability="research-framing",
        )


def test_refuses_to_register_directory(tmp_path: Path):
    project_root = tmp_path / "project"
    directory = project_root / "artifacts" / "directory"
    directory.mkdir(parents=True)
    store = ArtifactStore(project_root)

    with pytest.raises(ArtifactNotFound, match="regular file"):
        store.register(
            "artifacts/directory",
            artifact_id="directory-1",
            artifact_type="research_brief",
            schema_version="1.0",
            producing_capability="research-framing",
        )


def test_refuses_to_register_escaping_artifact(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    store = ArtifactStore(project_root)

    with pytest.raises(ProjectPathViolation):
        store.register(
            "../outside.md",
            artifact_id="outside-1",
            artifact_type="research_brief",
            schema_version="1.0",
            producing_capability="research-framing",
        )
