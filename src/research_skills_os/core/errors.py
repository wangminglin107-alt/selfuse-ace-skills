"""Domain errors returned by deterministic Research Skills OS services."""


class ResearchSkillsError(Exception):
    """Base class for expected runtime failures."""


class ProjectPathViolation(ResearchSkillsError):
    """A requested path is not safely contained by its research project."""


class ArtifactNotFound(ResearchSkillsError):
    """A declared artifact does not exist as a regular file."""


class EventLogCorruption(ResearchSkillsError):
    """An append-only event log contains unreadable or invalid data."""


class InvalidStateTransition(ResearchSkillsError):
    """An event cannot be applied to the current project state."""


class BlockedGateError(ResearchSkillsError):
    """A target cannot begin because one or more blocking gates failed."""

    def __init__(
        self,
        failed_gate_ids: list[str],
        *,
        findings: list[str] | None = None,
        remediation: list[str] | None = None,
    ) -> None:
        self.failed_gate_ids = tuple(failed_gate_ids)
        self.findings = tuple(findings or [])
        self.remediation = tuple(remediation or [])
        super().__init__("entry gates blocked: " + ", ".join(failed_gate_ids))


class CheckpointNotFound(ResearchSkillsError):
    """A requested checkpoint is not present in the project."""


class CheckpointIntegrityError(ResearchSkillsError):
    """A checkpoint cannot be created or trusted for resume."""


class DuplicateGate(ResearchSkillsError):
    """Two gate implementations declare the same stable identifier."""


class UnknownGate(ResearchSkillsError):
    """A requested gate identifier is not registered."""


class SpecLoadError(ResearchSkillsError):
    """A capability or workflow specification is invalid."""


class DuplicateSpec(ResearchSkillsError):
    """Two specifications declare the same identifier and kind."""


class UnknownTarget(ResearchSkillsError):
    """A request names no exactly registered capability or workflow."""
