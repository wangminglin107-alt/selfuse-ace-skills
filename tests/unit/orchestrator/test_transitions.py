import pytest

from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.orchestrator.transitions import RunLifecycle, validate_transition


@pytest.mark.parametrize(
    ("current", "next_state"),
    [
        (RunLifecycle.CREATED, RunLifecycle.RUNNING),
        (RunLifecycle.RUNNING, RunLifecycle.COMPLETED),
        (RunLifecycle.RUNNING, RunLifecycle.PAUSED),
        (RunLifecycle.RUNNING, RunLifecycle.BLOCKED),
        (RunLifecycle.RUNNING, RunLifecycle.FAILED),
        (RunLifecycle.PAUSED, RunLifecycle.RUNNING),
    ],
)
def test_accepts_declared_run_transition(current: RunLifecycle, next_state: RunLifecycle):
    assert validate_transition(current, next_state) is next_state


def test_blocked_run_requires_recorded_remediation_before_resume():
    with pytest.raises(InvalidStateTransition, match="remediation"):
        validate_transition(RunLifecycle.BLOCKED, RunLifecycle.RUNNING)

    assert (
        validate_transition(
            RunLifecycle.BLOCKED,
            RunLifecycle.RUNNING,
            remediation_recorded=True,
        )
        is RunLifecycle.RUNNING
    )


@pytest.mark.parametrize("terminal", [RunLifecycle.COMPLETED, RunLifecycle.FAILED])
def test_rejects_transition_out_of_terminal_state(terminal: RunLifecycle):
    with pytest.raises(InvalidStateTransition, match="terminal"):
        validate_transition(terminal, RunLifecycle.RUNNING)
