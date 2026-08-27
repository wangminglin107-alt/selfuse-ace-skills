import pytest

from research_skills_os.core.contracts.enums import RunMode
from research_skills_os.core.orchestrator.stop_policy import (
    StopAction,
    StopPolicy,
    StopSignals,
)


def test_interactive_mode_pauses_after_one_completed_target():
    assert (
        StopPolicy().decide(RunMode.INTERACTIVE, StopSignals(is_terminal=True)) is StopAction.PAUSE
    )


@pytest.mark.parametrize(
    "signals",
    [
        StopSignals(human_review=True),
        StopSignals(material_uncertainty=True),
        StopSignals(conflicting_evidence=True),
        StopSignals(new_external_provider=True),
    ],
)
def test_checkpointed_mode_pauses_at_human_or_material_decision(signals: StopSignals):
    assert StopPolicy().decide(RunMode.CHECKPOINTED, signals) is StopAction.PAUSE


def test_checkpointed_mode_continues_across_low_risk_nonterminal_target():
    assert StopPolicy().decide(RunMode.CHECKPOINTED, StopSignals()) is StopAction.CONTINUE


def test_autonomous_mode_continues_until_terminal():
    policy = StopPolicy()

    assert policy.decide(RunMode.AUTONOMOUS, StopSignals()) is StopAction.CONTINUE
    assert policy.decide(RunMode.AUTONOMOUS, StopSignals(is_terminal=True)) is StopAction.COMPLETE


def test_autonomous_mode_pauses_at_explicit_autonomous_review():
    action = StopPolicy().decide(
        RunMode.AUTONOMOUS,
        StopSignals(autonomous_review=True),
    )

    assert action is StopAction.PAUSE


def test_autonomous_mode_keeps_v1_default_behavior():
    assert StopPolicy().decide(RunMode.AUTONOMOUS, StopSignals()) is StopAction.CONTINUE


@pytest.mark.parametrize("mode", list(RunMode))
def test_every_mode_blocks_on_global_integrity_or_security_failure(mode: RunMode):
    assert StopPolicy().decide(mode, StopSignals(global_blocked=True)) is StopAction.BLOCK
