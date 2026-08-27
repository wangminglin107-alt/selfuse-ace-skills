from datetime import UTC, datetime

import pytest

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import ArtifactEnvelope
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.state.models import EventType, ProjectEvent, ProjectLifecycle
from research_skills_os.core.state.reducer import reduce_events

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def event(sequence: int, event_type: EventType, payload: dict[str, object]) -> ProjectEvent:
    return ProjectEvent(
        event_id=f"event-{sequence}",
        sequence=sequence,
        timestamp=NOW,
        type=event_type,
        payload=payload,
    )


def artifact() -> ArtifactEnvelope:
    return ArtifactEnvelope(
        artifact_id="brief-1",
        type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
        created_at=NOW,
        path="artifacts/research-framing/research-brief.md",
        sha256="a" * 64,
    )


def complete_history() -> list[ProjectEvent]:
    return [
        event(1, EventType.PROJECT_INITIALIZED, {"project_id": "project-1", "goal": "Frame idea"}),
        event(2, EventType.RUN_STARTED, {"run_id": "run-1"}),
        event(3, EventType.TARGET_STARTED, {"target_id": "research-framing"}),
        event(4, EventType.ARTIFACT_REGISTERED, {"artifact": artifact().model_dump(mode="json")}),
        event(
            5,
            EventType.DECISION_RECORDED,
            {
                "decision": {
                    "decision_id": "decision-1",
                    "description": "Study university students.",
                    "made_by": "user",
                }
            },
        ),
        event(
            6,
            EventType.UNCERTAINTY_RECORDED,
            {
                "uncertainty": {
                    "uncertainty_id": "uncertainty-1",
                    "description": "Geographic scope remains open.",
                    "material": True,
                }
            },
        ),
        event(
            7,
            EventType.GATE_RECORDED,
            {
                "gate_result": {
                    "gate_id": "contract.valid",
                    "gate_version": "1.0",
                    "status": GateStatus.PASS,
                    "severity": GateSeverity.BLOCKING,
                }
            },
        ),
        event(8, EventType.TARGET_COMPLETED, {"target_id": "research-framing"}),
        event(9, EventType.CHECKPOINT_CREATED, {"checkpoint_id": "checkpoint-1"}),
        event(10, EventType.RUN_COMPLETED, {"run_id": "run-1"}),
    ]


def test_replays_complete_history_into_materialized_state():
    state = reduce_events(complete_history())

    assert state.project_id == "project-1"
    assert state.goal == "Frame idea"
    assert state.lifecycle is ProjectLifecycle.COMPLETED
    assert state.active_run_id is None
    assert state.active_target is None
    assert state.completed_targets == ["research-framing"]
    assert state.artifacts == {"brief-1": artifact()}
    assert [decision.decision_id for decision in state.decisions] == ["decision-1"]
    assert [item.uncertainty_id for item in state.uncertainties] == ["uncertainty-1"]
    assert [gate.gate_id for gate in state.gate_results] == ["contract.valid"]
    assert state.current_checkpoint == "checkpoint-1"
    assert state.last_sequence == 10


def test_replay_is_deterministic_and_does_not_mutate_events():
    history = complete_history()
    original = [item.model_dump(mode="json") for item in history]

    first = reduce_events(history)
    second = reduce_events(history)

    assert first == second
    assert [item.model_dump(mode="json") for item in history] == original


def test_rejects_duplicate_terminal_transition():
    history = complete_history()
    history.append(event(11, EventType.RUN_COMPLETED, {"run_id": "run-1"}))

    with pytest.raises(InvalidStateTransition, match="already terminal"):
        reduce_events(history)


def test_rejects_noncontiguous_event_sequence():
    history = complete_history()
    history[2] = history[2].model_copy(update={"sequence": 4})

    with pytest.raises(InvalidStateTransition, match="expected sequence 3"):
        reduce_events(history)


def test_represents_paused_run_as_active_and_resumable():
    history = complete_history()[:3]
    history.append(event(4, EventType.RUN_PAUSED, {"run_id": "run-1"}))

    state = reduce_events(history)

    assert state.lifecycle is ProjectLifecycle.PAUSED
    assert state.active_run_id == "run-1"
    assert state.active_target is None


def test_fresh_run_does_not_inherit_prior_run_gate_results():
    history = complete_history()
    history.append(event(11, EventType.RUN_STARTED, {"run_id": "run-2"}))

    state = reduce_events(history)

    assert state.lifecycle is ProjectLifecycle.RUNNING
    assert state.active_run_id == "run-2"
    assert state.gate_results == []
