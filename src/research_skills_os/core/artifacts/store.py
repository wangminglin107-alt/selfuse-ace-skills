"""Register readable project artifacts and verify their content integrity."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from research_skills_os.core.artifacts.paths import resolve_project_path
from research_skills_os.core.contracts.models import ArtifactEnvelope
from research_skills_os.core.errors import ArtifactNotFound


class ArtifactVerification(BaseModel):
    """Integrity comparison without mutating the registered envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    path: str
    status: Literal["verified", "drifted"]
    expected_sha256: str
    actual_sha256: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArtifactStore:
    """Project-scoped registry facade; artifact content stays in normal files."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        if not self.project_root.is_dir():
            raise ArtifactNotFound("project root must be an existing directory")

    def register(
        self,
        relative_path: str | Path,
        *,
        artifact_id: str,
        artifact_type: str,
        schema_version: str,
        producing_capability: str,
        source_artifact_ids: Sequence[str] = (),
        provenance_references: Sequence[str] = (),
        sensitivity: Literal["public", "internal", "sensitive"] = "internal",
        human_edited: bool = False,
        verification_state: Literal["unverified", "verified", "drifted"] = "unverified",
        created_at: datetime | None = None,
    ) -> ArtifactEnvelope:
        """Describe an existing file without copying or rewriting its content."""

        artifact_path = resolve_project_path(self.project_root, relative_path)
        if not artifact_path.is_file():
            raise ArtifactNotFound(f"artifact must exist as a regular file: {relative_path}")

        stored_path = artifact_path.relative_to(self.project_root).as_posix()
        return ArtifactEnvelope(
            artifact_id=artifact_id,
            type=artifact_type,
            schema_version=schema_version,
            producing_capability=producing_capability,
            created_at=created_at or datetime.now(UTC),
            path=stored_path,
            sha256=_sha256(artifact_path),
            source_artifact_ids=list(source_artifact_ids),
            provenance_references=list(provenance_references),
            sensitivity=sensitivity,
            human_edited=human_edited,
            verification_state=verification_state,
        )

    def verify(self, envelope: ArtifactEnvelope) -> ArtifactVerification:
        """Compare the current file with its registered hash."""

        artifact_path = resolve_project_path(self.project_root, envelope.path)
        actual_sha256 = _sha256(artifact_path)
        status: Literal["verified", "drifted"] = (
            "verified" if actual_sha256 == envelope.sha256 else "drifted"
        )
        return ArtifactVerification(
            artifact_id=envelope.artifact_id,
            path=envelope.path,
            status=status,
            expected_sha256=envelope.sha256,
            actual_sha256=actual_sha256,
        )
