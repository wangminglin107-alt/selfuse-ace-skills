import os
import subprocess
from pathlib import Path

import pytest

from research_skills_os.core.artifacts.paths import resolve_project_path
from research_skills_os.core.errors import ProjectPathViolation


def test_resolves_nested_path_with_spaces_and_cjk(tmp_path: Path):
    project_root = tmp_path / "研究 project"
    project_root.mkdir()

    resolved = resolve_project_path(project_root, "artifacts/研究 brief.md")

    assert resolved == project_root / "artifacts" / "研究 brief.md"


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.md",
        "artifacts/../../outside.md",
        "/absolute/artifact.md",
        "C:\\research\\artifact.md",
        "C:drive-relative.md",
        "\\\\server\\share\\artifact.md",
    ],
)
def test_rejects_paths_that_are_not_project_relative(tmp_path: Path, unsafe_path: str):
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ProjectPathViolation):
        resolve_project_path(project_root, unsafe_path)


def test_rejects_symlink_that_escapes_project(tmp_path: Path):
    project_root = tmp_path / "project"
    outside = tmp_path / "outside"
    project_root.mkdir()
    outside.mkdir()
    link = project_root / "external"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Creating a Windows symlink is unavailable: {exc}")

    with pytest.raises(ProjectPathViolation, match="outside the project root"):
        resolve_project_path(project_root, "external/source.md")


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_rejects_junction_that_escapes_project(tmp_path: Path):
    project_root = tmp_path / "project"
    outside = tmp_path / "outside"
    project_root.mkdir()
    outside.mkdir()
    junction = project_root / "external-junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not os.path.isjunction(junction):
        pytest.skip("Creating a Windows junction is unavailable in this environment")

    with pytest.raises(ProjectPathViolation, match="outside the project root"):
        resolve_project_path(project_root, "external-junction/source.md")
