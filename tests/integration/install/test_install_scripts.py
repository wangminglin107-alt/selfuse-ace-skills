import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
INSTALLER = ROOT / "scripts" / "install-skills.ps1"
UNINSTALLER = ROOT / "scripts" / "uninstall-skills.ps1"
SKILL_NAMES = {
    "research-os",
    "research-framing",
    "literature-intelligence",
    "novelty-audit",
    "idea-to-novelty",
}
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def directory_digest(path: Path) -> str:
    entries = []
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = item.relative_to(path).as_posix()
        entries.append(f"{relative}:{hashlib.sha256(item.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(entries).encode()).hexdigest()


def run_script(script: Path, skill_home: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    return subprocess.run(
        [
            POWERSHELL,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
            "-SkillHome",
            str(skill_home),
            *arguments,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_dry_run_names_only_five_targets_and_preserves_skill_home(tmp_path: Path):
    skill_home = tmp_path / "skills home"
    unrelated = skill_home / "ssci-existing" / "KEEP.txt"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("keep\n", encoding="utf-8")

    result = run_script(INSTALLER, skill_home, "-WhatIf")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "what_if"
    assert {item["name"] for item in payload["skills"]} == SKILL_NAMES
    assert all(
        Path(item["destination"]).parent == skill_home.resolve() for item in payload["skills"]
    )
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert not (skill_home / ".research-skills-os-install.json").exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_install_is_idempotent_and_source_hashes_match(tmp_path: Path):
    skill_home = tmp_path / "skills"
    unrelated = skill_home / "unrelated-skill" / "SKILL.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("unrelated\n", encoding="utf-8")

    first = run_script(INSTALLER, skill_home)
    second = run_script(INSTALLER, skill_home)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["status"] == "unchanged"
    record = json.loads((skill_home / ".research-skills-os-install.json").read_text("utf-8"))
    assert {item["name"] for item in record["skills"]} == SKILL_NAMES
    for item in record["skills"]:
        source = ROOT / "skills" / item["name"]
        installed = skill_home / item["name"]
        assert directory_digest(source) == directory_digest(installed)
        assert item["source_sha256"] == item["installed_sha256"]
        assert item["installed_sha256"] == directory_digest(installed)
    assert unrelated.read_text(encoding="utf-8") == "unrelated\n"


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_collision_fails_before_copy_without_explicit_replace(tmp_path: Path):
    skill_home = tmp_path / "skills"
    collision = skill_home / "research-os" / "personal.txt"
    collision.parent.mkdir(parents=True)
    collision.write_text("personal\n", encoding="utf-8")

    result = run_script(INSTALLER, skill_home)

    assert result.returncode != 0
    assert "collision" in result.stderr.casefold()
    assert collision.read_text(encoding="utf-8") == "personal\n"
    assert not (skill_home / "literature-intelligence").exists()
    assert not (skill_home / ".research-skills-os-install.json").exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_replace_backup_is_recoverable_by_record_scoped_uninstall(tmp_path: Path):
    skill_home = tmp_path / "skills"
    collision = skill_home / "research-os" / "personal.txt"
    collision.parent.mkdir(parents=True)
    collision.write_text("personal\n", encoding="utf-8")
    unrelated = skill_home / "ssci-existing" / "KEEP.txt"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("keep\n", encoding="utf-8")

    installed = run_script(INSTALLER, skill_home, "-Replace")
    record = json.loads((skill_home / ".research-skills-os-install.json").read_text("utf-8"))
    backup = next(item["backup_path"] for item in record["skills"] if item["name"] == "research-os")
    removed = run_script(UNINSTALLER, skill_home)

    assert installed.returncode == 0, installed.stderr
    assert backup is not None
    assert removed.returncode == 0, removed.stderr
    assert collision.read_text(encoding="utf-8") == "personal\n"
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert not (skill_home / "literature-intelligence").exists()
    assert not (skill_home / ".research-skills-os-install.json").exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_uninstall_refuses_to_remove_modified_installed_skill(tmp_path: Path):
    skill_home = tmp_path / "skills"
    installed = run_script(INSTALLER, skill_home)
    assert installed.returncode == 0, installed.stderr
    changed = skill_home / "research-os" / "SKILL.md"
    changed.write_text(changed.read_text("utf-8") + "\nlocal edit\n", encoding="utf-8")

    removed = run_script(UNINSTALLER, skill_home)

    assert removed.returncode != 0
    assert "modified" in removed.stderr.casefold()
    assert changed.exists()
    assert (skill_home / "literature-intelligence").exists()
    assert (skill_home / ".research-skills-os-install.json").exists()
