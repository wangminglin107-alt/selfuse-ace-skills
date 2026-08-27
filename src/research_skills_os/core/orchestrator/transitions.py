"""Explicit legal lifecycle transitions for execution runs."""

from enum import StrEnum

from research_skills_os.core.errors import InvalidStateTransition


class RunLifecycle(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


def validate_transition(
    current: RunLifecycle,
    next_state: RunLifecycle,
    *,
    remediation_recorded: bool = False,
) -> RunLifecycle:
    if current in {RunLifecycle.COMPLETED, RunLifecycle.FAILED}:
        raise InvalidStateTransition(f"cannot transition out of terminal state {current}")
    if current is RunLifecycle.BLOCKED and next_state is RunLifecycle.RUNNING:
        if not remediation_recorded:
            raise InvalidStateTransition("blocked run requires recorded remediation")
        return next_state
    allowed = {
        RunLifecycle.CREATED: {RunLifecycle.RUNNING},
        RunLifecycle.RUNNING: {
            RunLifecycle.COMPLETED,
            RunLifecycle.PAUSED,
            RunLifecycle.BLOCKED,
            RunLifecycle.FAILED,
        },
        RunLifecycle.PAUSED: {RunLifecycle.RUNNING},
        RunLifecycle.BLOCKED: set(),
    }
    if next_state not in allowed[current]:
        raise InvalidStateTransition(f"invalid run transition: {current} -> {next_state}")
    return next_state
