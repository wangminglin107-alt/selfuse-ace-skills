"""Domain errors returned by deterministic Research Skills OS services."""


class ResearchSkillsError(Exception):
    """Base class for expected runtime failures."""


class ProjectPathViolation(ResearchSkillsError):
    """A requested path is not safely contained by its research project."""


class ArtifactNotFound(ResearchSkillsError):
    """A declared artifact does not exist as a regular file."""
