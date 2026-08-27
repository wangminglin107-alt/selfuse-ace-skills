"""Cross-platform project-root path containment."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from research_skills_os.core.errors import ProjectPathViolation


def _normalize_relative_path(relative_path: str | Path) -> PurePosixPath:
    raw = str(relative_path).strip()
    if not raw:
        raise ProjectPathViolation("artifact path must not be empty")

    windows_path = PureWindowsPath(raw)
    posix_path = PurePosixPath(raw.replace("\\", "/"))
    if windows_path.drive or windows_path.root or posix_path.is_absolute():
        raise ProjectPathViolation("artifact path must be relative to the project root")
    if ".." in posix_path.parts:
        raise ProjectPathViolation("artifact path traversal is not allowed")
    if posix_path.as_posix() in {"", "."}:
        raise ProjectPathViolation("artifact path must identify a file")
    return posix_path


def resolve_project_path(project_root: str | Path, relative_path: str | Path) -> Path:
    """Resolve a project-relative path and reject every escape from the project root."""

    root = Path(project_root).resolve(strict=True)
    if not root.is_dir():
        raise ProjectPathViolation("project root must be an existing directory")

    normalized = _normalize_relative_path(relative_path)
    candidate = root.joinpath(*normalized.parts)
    try:
        resolved = candidate.resolve(strict=False)
        common = Path(os.path.commonpath((str(root), str(resolved))))
    except (OSError, RuntimeError, ValueError) as exc:
        raise ProjectPathViolation("artifact path cannot be resolved safely") from exc

    if os.path.normcase(str(common)) != os.path.normcase(str(root)):
        raise ProjectPathViolation("artifact path resolves outside the project root")
    return resolved
