"""Mode-specific stopping decisions evaluated at target boundaries."""

from dataclasses import dataclass
from enum import StrEnum

from research_skills_os.core.contracts.enums import RunMode


class StopAction(StrEnum):
    CONTINUE = "continue"
    PAUSE = "pause"
    BLOCK = "block"
    COMPLETE = "complete"


@dataclass(frozen=True)
class StopSignals:
    is_terminal: bool = False
    human_review: bool = False
    material_uncertainty: bool = False
    conflicting_evidence: bool = False
    new_external_provider: bool = False
    global_blocked: bool = False


class StopPolicy:
    def decide(self, mode: RunMode, signals: StopSignals) -> StopAction:
        if signals.global_blocked:
            return StopAction.BLOCK
        if mode is RunMode.INTERACTIVE:
            return StopAction.PAUSE
        if mode is RunMode.CHECKPOINTED and any(
            (
                signals.human_review,
                signals.material_uncertainty,
                signals.conflicting_evidence,
                signals.new_external_provider,
            )
        ):
            return StopAction.PAUSE
        if signals.is_terminal:
            return StopAction.COMPLETE
        return StopAction.CONTINUE
