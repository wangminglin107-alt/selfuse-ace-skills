from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.providers.local_manual import LocalManualProvider
from research_skills_os.providers.protocol import ProviderRequest, ProviderSource
from research_skills_os.providers.registry import (
    ProviderArtifactIntegrityError,
    ProviderArtifactNotRegistered,
)


def registered_text_artifact(project_root: Path):
    source = project_root / "sources" / "manual-note.md"
    source.parent.mkdir(parents=True)
    source.write_text("A locally supplied source.\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project_root).register(
        "sources/manual-note.md",
        artifact_id="manual-source-1",
        artifact_type="manual_source",
        schema_version="1.0",
        producing_capability="user-import",
        provenance_references=["user-supplied:manual-source-1"],
        created_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
    )
    return envelope


def test_default_provider_is_fully_offline_and_secret_free(tmp_path: Path):
    project_root = tmp_path / "project 研究"
    project_root.mkdir()

    declaration = LocalManualProvider(project_root).declaration

    assert declaration.provider_id == "local-manual"
    assert declaration.network == "none"
    assert declaration.required_secrets == []
    assert declaration.endpoints == []
    assert declaration.data_sent_off_machine == []
    assert declaration.offline_behavior == "supported"


def test_reads_only_registered_project_artifacts_and_returns_hash(tmp_path: Path):
    project_root = tmp_path / "project 研究"
    project_root.mkdir()
    envelope = registered_text_artifact(project_root)

    result = LocalManualProvider(project_root).collect(
        ProviderRequest(artifact_ids=[envelope.artifact_id]),
        registered_artifacts={envelope.artifact_id: envelope},
    )

    assert result.provider_id == "local-manual"
    assert result.network_used is False
    assert result.secrets_used == []
    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.artifact_id == envelope.artifact_id
    assert source.path == envelope.path
    assert source.sha256 == envelope.sha256
    assert source.content == "A locally supplied source.\n"
    assert source.verification_state == "candidate"


def test_rejects_an_artifact_id_that_is_not_in_the_registry(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ProviderArtifactNotRegistered, match="not registered"):
        LocalManualProvider(project_root).collect(
            ProviderRequest(artifact_ids=["not-registered"]),
            registered_artifacts={},
        )


def test_rejects_registered_artifact_after_hash_drift(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    envelope = registered_text_artifact(project_root)
    (project_root / envelope.path).write_text("changed\n", encoding="utf-8")

    with pytest.raises(ProviderArtifactIntegrityError, match="hash drift"):
        LocalManualProvider(project_root).collect(
            ProviderRequest(artifact_ids=[envelope.artifact_id]),
            registered_artifacts={envelope.artifact_id: envelope},
        )


def test_provider_source_cannot_claim_automatic_verification():
    with pytest.raises(ValidationError):
        ProviderSource(
            artifact_id="source-1",
            path="sources/source.md",
            sha256="0" * 64,
            content="source",
            verification_state="verified_content",
        )
