"""Pure replay of project events into the current materialized state."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    DecisionRecord,
    GateResult,
    UncertaintyRecord,
)
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.state.models import (
    EventType,
    ProjectEvent,
    ProjectLifecycle,
    ProjectState,
)


def _required_text(payload: dict[str, Any], field: str, event: ProjectEvent) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidStateTransition(f"{event.type} requires non-empty {field}")
    return value.strip()


def _validated_payload(
    payload: dict[str, Any],
    field: str,
    model: type[ArtifactEnvelope | DecisionRecord | GateResult | UncertaintyRecord],
    event: ProjectEvent,
) -> ArtifactEnvelope | DecisionRecord | GateResult | UncertaintyRecord:
    try:
        return model.model_validate(payload.get(field))
    except ValidationError as exc:
        raise InvalidStateTransition(f"{event.type} contains invalid {field}") from exc


def _require_running(state: ProjectState, event: ProjectEvent) -> None:
    if state.lifecycle is not ProjectLifecycle.RUNNING:
        raise InvalidStateTransition(f"{event.type} requires a running project")


def reduce_events(events: Iterable[ProjectEvent]) -> ProjectState:
    """Build state from history without mutating either history or prior state."""

    state: ProjectState | None = None
    expected_sequence = 1

    for event in events:
        if event.sequence != expected_sequence:
            raise InvalidStateTransition(
                f"expected sequence {expected_sequence}, got {event.sequence}"
            )
        expected_sequence += 1

        if event.type is EventType.PROJECT_INITIALIZED:
            if state is not None:
                raise InvalidStateTransition("project is already initialized")
            state = ProjectState(
                project_id=_required_text(event.payload, "project_id", event),
                goal=event.payload.get("goal"),
                last_sequence=event.sequence,
            )
            continue

        if state is None:
            raise InvalidStateTransition("project_initialized must be the first event")
        if state.lifecycle in {ProjectLifecycle.COMPLETED, ProjectLifecycle.FAILED}:
            raise InvalidStateTransition("project is already terminal")

        updates: dict[str, Any] = {"last_sequence": event.sequence}

        if event.type is EventType.RUN_STARTED:
            if state.lifecycle not in {
                ProjectLifecycle.INITIALIZED,
                ProjectLifecycle.PAUSED,
                ProjectLifecycle.BLOCKED,
            }:
                raise InvalidStateTransition("a run is already active")
            updates.update(
                lifecycle=ProjectLifecycle.RUNNING,
                active_run_id=_required_text(event.payload, "run_id", event),
                active_target=None,
            )
        elif event.type is EventType.TARGET_STARTED:
            _require_running(state, event)
            if state.active_target is not None:
                raise InvalidStateTransition("a target is already active")
            updates["active_target"] = _required_text(event.payload, "target_id", event)
        elif event.type is EventType.ARTIFACT_REGISTERED:
            _require_running(state, event)
            artifact = _validated_payload(event.payload, "artifact", ArtifactEnvelope, event)
            assert isinstance(artifact, ArtifactEnvelope)
            artifacts = dict(state.artifacts)
            artifacts[artifact.artifact_id] = artifact
            updates["artifacts"] = artifacts
        elif event.type is EventType.DECISION_RECORDED:
            decision = _validated_payload(event.payload, "decision", DecisionRecord, event)
            assert isinstance(decision, DecisionRecord)
            updates["decisions"] = [*state.decisions, decision]
        elif event.type is EventType.UNCERTAINTY_RECORDED:
            uncertainty = _validated_payload(event.payload, "uncertainty", UncertaintyRecord, event)
            assert isinstance(uncertainty, UncertaintyRecord)
            updates["uncertainties"] = [*state.uncertainties, uncertainty]
        elif event.type is EventType.GATE_RECORDED:
            gate_result = _validated_payload(event.payload, "gate_result", GateResult, event)
            assert isinstance(gate_result, GateResult)
            updates["gate_results"] = [*state.gate_results, gate_result]
        elif event.type is EventType.TARGET_COMPLETED:
            _require_running(state, event)
            target_id = _required_text(event.payload, "target_id", event)
            if state.active_target != target_id:
                raise InvalidStateTransition("completed target is not the active target")
            updates.update(
                active_target=None,
                completed_targets=[*state.completed_targets, target_id],
            )
        elif event.type is EventType.CHECKPOINT_CREATED:
            updates["current_checkpoint"] = _required_text(event.payload, "checkpoint_id", event)
        elif event.type in {
            EventType.RUN_PAUSED,
            EventType.RUN_BLOCKED,
            EventType.RUN_COMPLETED,
            EventType.RUN_FAILED,
        }:
            _require_running(state, event)
            run_id = _required_text(event.payload, "run_id", event)
            if state.active_run_id != run_id:
                raise InvalidStateTransition("terminal event does not match the active run")
            lifecycle = {
                EventType.RUN_PAUSED: ProjectLifecycle.PAUSED,
                EventType.RUN_BLOCKED: ProjectLifecycle.BLOCKED,
                EventType.RUN_COMPLETED: ProjectLifecycle.COMPLETED,
                EventType.RUN_FAILED: ProjectLifecycle.FAILED,
            }[event.type]
            updates.update(lifecycle=lifecycle, active_target=None)
            if event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}:
                updates["active_run_id"] = None
        else:
            raise InvalidStateTransition(f"unsupported event type: {event.type}")

        state = state.model_copy(update=updates, deep=True)

    if state is None:
        raise InvalidStateTransition("event history is empty")
    return state
