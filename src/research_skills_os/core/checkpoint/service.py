"""Durable checkpoint publication and state/artifact drift verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import GateStatus
from research_skills_os.core.contracts.models import Checkpoint
from research_skills_os.core.errors import (
    CheckpointIntegrityError,
    CheckpointNotFound,
)
from research_skills_os.core.state.models import EventType, ProjectEvent, ProjectState
from research_skills_os.core.state.repository import StateRepository

CHECKPOINT_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}$")


class ResumeArtifactStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    path: str
    status: Literal["verified", "drifted", "missing"]
    expected_sha256: str
    actual_sha256: str | None = None


class ResumeVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str
    status: Literal["verified", "drifted"]
    state_matches: bool
    artifacts: list[ResumeArtifactStatus] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


def _checkpoint_id(now: datetime) -> str:
    return f"{now.astimezone(UTC):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}"


def _resume_state_hash(state: ProjectState) -> str:
    payload = state.model_dump(mode="json")
    payload.pop("current_checkpoint", None)
    payload.pop("last_sequence", None)
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class CheckpointService:
    def __init__(
        self,
        project_root: str | Path,
        *,
        repository: StateRepository | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.repository = repository or StateRepository(self.project_root)
        self.artifact_store = ArtifactStore(self.project_root)
        self.checkpoint_directory = self.project_root / ".research-os" / "checkpoints"
        self.current_pointer = self.project_root / ".research-os" / "current-checkpoint"

    def create(self, state: ProjectState, completed_target: str) -> Checkpoint:
        """Validate and publish a checkpoint before recording its history event."""

        if completed_target not in state.completed_targets:
            raise CheckpointIntegrityError(f"target is not completed: {completed_target}")
        if state.active_run_id is None:
            raise CheckpointIntegrityError("checkpoint requires an active resumable run")

        now = datetime.now(UTC)
        checkpoint = Checkpoint(
            checkpoint_id=_checkpoint_id(now),
            project_id=state.project_id,
            run_id=state.active_run_id,
            completed_target=completed_target,
            artifacts_created=[
                artifact
                for artifact in state.artifacts.values()
                if artifact.producing_capability == completed_target
            ],
            key_decisions=state.decisions,
            uncertainties=state.uncertainties,
            failed_gates=[
                result.gate_id for result in state.gate_results if result.status is GateStatus.FAIL
            ],
            resume_from=completed_target,
            state_hash=_resume_state_hash(state),
            created_at=now,
        )
        validated = Checkpoint.model_validate(checkpoint.model_dump(mode="json"))
        checkpoint_path = self._checkpoint_path(validated.checkpoint_id)
        serialized = json.dumps(
            validated.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        _atomic_write_text(checkpoint_path, f"{serialized}\n")
        _atomic_write_text(self.current_pointer, f"{validated.checkpoint_id}\n")
        self.repository.append(
            ProjectEvent(
                event_id=f"checkpoint-event-{validated.checkpoint_id}",
                type=EventType.CHECKPOINT_CREATED,
                payload={"checkpoint_id": validated.checkpoint_id},
            )
        )
        return validated

    def load(self, checkpoint_id: str) -> Checkpoint:
        path = self._checkpoint_path(checkpoint_id)
        if not path.is_file():
            raise CheckpointNotFound(f"checkpoint does not exist: {checkpoint_id}")
        try:
            return Checkpoint.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CheckpointIntegrityError(f"checkpoint is invalid: {checkpoint_id}") from exc

    def current(self) -> Checkpoint | None:
        if not self.current_pointer.is_file():
            return None
        checkpoint_id = self.current_pointer.read_text(encoding="utf-8").strip()
        return self.load(checkpoint_id)

    def verify_resume(self, checkpoint_id: str) -> ResumeVerification:
        checkpoint = self.load(checkpoint_id)
        current_state = self.repository.load()
        state_matches = _resume_state_hash(current_state) == checkpoint.state_hash
        reasons: list[str] = []
        if not state_matches:
            reasons.append("project state changed after the checkpoint")

        artifacts: list[ResumeArtifactStatus] = []
        for envelope in checkpoint.artifacts_created:
            try:
                verification = self.artifact_store.verify(envelope)
            except FileNotFoundError:
                result = ResumeArtifactStatus(
                    artifact_id=envelope.artifact_id,
                    path=envelope.path,
                    status="missing",
                    expected_sha256=envelope.sha256,
                )
            else:
                result = ResumeArtifactStatus.model_validate(verification.model_dump(mode="json"))
            artifacts.append(result)
            if result.status != "verified":
                reasons.append(f"artifact {result.artifact_id} is {result.status}")

        status: Literal["verified", "drifted"] = "verified" if not reasons else "drifted"
        return ResumeVerification(
            checkpoint_id=checkpoint_id,
            status=status,
            state_matches=state_matches,
            artifacts=artifacts,
            reasons=reasons,
        )

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        if CHECKPOINT_ID_PATTERN.fullmatch(checkpoint_id) is None:
            raise CheckpointNotFound(f"invalid checkpoint id: {checkpoint_id}")
        return self.checkpoint_directory / f"{checkpoint_id}.json"
