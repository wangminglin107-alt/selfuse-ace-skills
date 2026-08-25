"""Typed events and the materialized project-state view."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    DecisionRecord,
    GateResult,
    UncertaintyRecord,
)


class EventType(StrEnum):
    PROJECT_INITIALIZED = "project_initialized"
    RUN_STARTED = "run_started"
    TARGET_STARTED = "target_started"
    ARTIFACT_REGISTERED = "artifact_registered"
    DECISION_RECORDED = "decision_recorded"
    UNCERTAINTY_RECORDED = "uncertainty_recorded"
    GATE_RECORDED = "gate_recorded"
    TARGET_COMPLETED = "target_completed"
    CHECKPOINT_CREATED = "checkpoint_created"
    RUN_PAUSED = "run_paused"
    RUN_BLOCKED = "run_blocked"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class ProjectLifecycle(StrEnum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class StateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ProjectEvent(StateModel):
    event_version: Literal["1.0"] = "1.0"
    event_id: str = Field(min_length=1)
    sequence: int | None = Field(default=None, ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    type: EventType
    payload: dict[str, Any]

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event timestamp must include timezone information")
        return value


class ProjectState(StateModel):
    project_id: str = Field(min_length=1)
    goal: str | None = None
    lifecycle: ProjectLifecycle = ProjectLifecycle.INITIALIZED
    active_run_id: str | None = None
    active_target: str | None = None
    completed_targets: list[str] = Field(default_factory=list)
    artifacts: dict[str, ArtifactEnvelope] = Field(default_factory=dict)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    uncertainties: list[UncertaintyRecord] = Field(default_factory=list)
    gate_results: list[GateResult] = Field(default_factory=list)
    current_checkpoint: str | None = None
    last_sequence: int = Field(ge=1)
