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
