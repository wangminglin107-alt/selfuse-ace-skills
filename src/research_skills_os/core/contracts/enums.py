"""Closed vocabularies shared by all V1 contracts."""

from enum import StrEnum


class RunMode(StrEnum):
    INTERACTIVE = "interactive"
    CHECKPOINTED = "checkpointed"
    AUTONOMOUS = "autonomous"


class TargetKind(StrEnum):
    CAPABILITY = "capability"
    WORKFLOW = "workflow"


class RunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_UNCERTAINTY = "completed_with_uncertainty"
    PAUSED = "paused"
    BLOCKED = "blocked"
    FAILED = "failed"


class GateStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class GateSeverity(StrEnum):
    INFO = "info"
    ADVISORY = "advisory"
    BLOCKING = "blocking"
