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


def _text_list(payload: dict[str, Any], field: str, event: ProjectEvent) -> list[str]:
    value = payload.get(field, [])
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise InvalidStateTransition(f"{event.type} requires {field} to contain text IDs")
    return [item.strip() for item in value]


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
        if state.lifecycle in {
            ProjectLifecycle.COMPLETED,
            ProjectLifecycle.FAILED,
        } and event.type not in {EventType.RUN_STARTED, EventType.CHECKPOINT_CREATED}:
            raise InvalidStateTransition("project is already terminal")

        updates: dict[str, Any] = {"last_sequence": event.sequence}

        if event.type is EventType.RUN_STARTED:
            if state.lifecycle not in {
                ProjectLifecycle.INITIALIZED,
                ProjectLifecycle.PAUSED,
                ProjectLifecycle.BLOCKED,
                ProjectLifecycle.COMPLETED,
                ProjectLifecycle.FAILED,
            }:
                raise InvalidStateTransition("a run is already active")
            fresh_run = (
                state.lifecycle
                in {
                    ProjectLifecycle.INITIALIZED,
                    ProjectLifecycle.COMPLETED,
                    ProjectLifecycle.FAILED,
                }
                or event.payload.get("replace_blocked") is True
            )
            updates.update(
                lifecycle=ProjectLifecycle.RUNNING,
                active_run_id=_required_text(event.payload, "run_id", event),
                active_target=None,
                active_input_artifact_ids=[],
                current_run_artifact_ids=([] if fresh_run else state.current_run_artifact_ids),
                completed_targets=[] if fresh_run else state.completed_targets,
                gate_results=[] if fresh_run else state.gate_results,
                current_checkpoint=None if fresh_run else state.current_checkpoint,
            )
            if fresh_run and isinstance(event.payload.get("goal"), str):
                updates["goal"] = event.payload["goal"]
        elif event.type is EventType.TARGET_STARTED:
            _require_running(state, event)
            if state.active_target is not None:
                raise InvalidStateTransition("a target is already active")
            updates.update(
                active_target=_required_text(event.payload, "target_id", event),
                active_input_artifact_ids=_text_list(event.payload, "input_artifact_ids", event),
            )
        elif event.type is EventType.ARTIFACT_REGISTERED:
            _require_running(state, event)
            artifact = _validated_payload(event.payload, "artifact", ArtifactEnvelope, event)
            assert isinstance(artifact, ArtifactEnvelope)
            artifacts = dict(state.artifacts)
            artifacts[artifact.artifact_id] = artifact
            updates.update(
                artifacts=artifacts,
                current_run_artifact_ids=list(
                    dict.fromkeys([*state.current_run_artifact_ids, artifact.artifact_id])
                ),
            )
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
            completion_id = event.payload.get("completion_id", target_id)
            if not isinstance(completion_id, str) or not completion_id.strip():
                raise InvalidStateTransition("target_completed requires a completion_id")
            updates.update(
                active_target=None,
                active_input_artifact_ids=[],
                completed_targets=[*state.completed_targets, completion_id.strip()],
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
            updates.update(
                lifecycle=lifecycle,
                active_target=None,
                active_input_artifact_ids=[],
            )
            if event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}:
                updates["active_run_id"] = None
        else:
            raise InvalidStateTransition(f"unsupported event type: {event.type}")

        state = state.model_copy(update=updates, deep=True)

    if state is None:
        raise InvalidStateTransition("event history is empty")
    return state
