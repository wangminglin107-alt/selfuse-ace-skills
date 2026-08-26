import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
INSTALLER = ROOT / "scripts" / "install-runtime.ps1"
UNINSTALLER = ROOT / "scripts" / "uninstall-runtime.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def run_script(script: Path, runtime_root: Path, launcher_directory: Path, *arguments: str):
    assert POWERSHELL is not None
    return subprocess.run(
        [
            POWERSHELL,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
            "-RuntimeRoot",
            str(runtime_root),
            "-LauncherDirectory",
            str(launcher_directory),
            *arguments,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_runtime_dry_run_is_non_mutating_and_uses_direct_launcher_child(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    launcher_directory = tmp_path / "bin"

    result = run_script(INSTALLER, runtime_root, launcher_directory, "-WhatIf")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "what_if"
    assert Path(payload["runtime_root"]) == runtime_root.resolve()
    assert Path(payload["launcher"]) == (launcher_directory / "research-os.cmd").resolve()
    assert payload["actions"] == ["create_runtime", "create_launcher"]
    assert not runtime_root.exists()
    assert not launcher_directory.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_runtime_install_refuses_unmanaged_collisions_before_provisioning(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    launcher_directory = tmp_path / "bin"
    runtime_root.mkdir()
    personal = runtime_root / "personal.txt"
    personal.write_text("keep\n", encoding="utf-8")

    result = run_script(INSTALLER, runtime_root, launcher_directory)

    assert result.returncode != 0
    assert "collision" in result.stderr.casefold()
    assert personal.read_text(encoding="utf-8") == "keep\n"
    assert not launcher_directory.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_runtime_uninstall_refuses_modified_launcher(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    launcher_directory = tmp_path / "bin"
    launcher_directory.mkdir()
    launcher = launcher_directory / "research-os.cmd"
    launcher.write_text("@echo modified\n", encoding="utf-8")
    runtime_root.mkdir()
    record = {
        "record_version": "1.0",
        "installation_id": "test-installation",
        "runtime_root": str(runtime_root.resolve()),
        "launcher": str(launcher.resolve()),
        "launcher_sha256": "0" * 64,
        "backup_root": None,
        "runtime_backup": None,
        "launcher_backup": None,
    }
    (runtime_root / ".research-skills-os-runtime-install.json").write_text(
        json.dumps(record), encoding="utf-8"
    )

    result = run_script(UNINSTALLER, runtime_root, launcher_directory)

    assert result.returncode != 0
    assert "modified" in result.stderr.casefold()
    assert runtime_root.exists()
    assert launcher.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_runtime_uninstall_rejects_record_supplied_backup_root(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    launcher_directory = tmp_path / "bin"
    launcher_directory.mkdir()
    launcher = launcher_directory / "research-os.cmd"
    launcher.write_text("@echo managed\n", encoding="ascii")
    runtime_root.mkdir()
    unrelated_root = tmp_path / "unrelated-backups" / "forged-session"
    runtime_backup = unrelated_root / "runtime"
    runtime_backup.mkdir(parents=True)
    record = {
        "record_version": "1.0",
        "installation_id": "test-installation",
        "runtime_root": str(runtime_root.resolve()),
        "launcher": str(launcher.resolve()),
        "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
        "backup_root": str(unrelated_root.resolve()),
        "runtime_backup": str(runtime_backup.resolve()),
        "launcher_backup": None,
    }
    (runtime_root / ".research-skills-os-runtime-install.json").write_text(
        json.dumps(record), encoding="utf-8"
    )

    result = run_script(UNINSTALLER, runtime_root, launcher_directory)

    assert result.returncode != 0
    assert "backup root" in result.stderr.casefold()
    assert runtime_root.exists()
    assert launcher.exists()
    assert runtime_backup.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required")
def test_runtime_uninstall_rejects_runtime_junction(tmp_path: Path):
    runtime_target = tmp_path / "runtime-target"
    runtime_target.mkdir()
    runtime_root = tmp_path / "runtime-junction"
    launcher_directory = tmp_path / "bin"
    launcher_directory.mkdir()
    launcher = launcher_directory / "research-os.cmd"
    launcher.write_text("@echo managed\n", encoding="ascii")
    record = {
        "record_version": "1.0",
        "installation_id": "test-installation",
        "runtime_root": str(runtime_root.resolve()),
        "launcher": str(launcher.resolve()),
        "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
        "backup_root": None,
        "runtime_backup": None,
        "launcher_backup": None,
    }
    (runtime_target / ".research-skills-os-runtime-install.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    created = subprocess.run(
        [
            POWERSHELL,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "New-Item -ItemType Junction -Path $env:RSOS_TEST_LINK "
            "-Target $env:RSOS_TEST_TARGET | Out-Null",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "RSOS_TEST_LINK": str(runtime_root),
            "RSOS_TEST_TARGET": str(runtime_target),
        },
    )
    if created.returncode != 0:
        pytest.skip(f"Junction creation unavailable: {created.stderr}")
    try:
        result = run_script(UNINSTALLER, runtime_root, launcher_directory)

        assert result.returncode != 0
        assert "reparse" in result.stderr.casefold()
        assert runtime_root.exists()
        assert runtime_target.exists()
        assert launcher.exists()
    finally:
        runtime_root.rmdir()


def test_runtime_lock_contains_only_exact_hashed_runtime_dependencies():
    lock = ROOT / "requirements-runtime.lock"
    entries = [
        line.strip()
        for line in lock.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    assert len(entries) == 7
    assert all("==" in entry and " --hash=sha256:" in entry for entry in entries)
    assert {entry.split("==", maxsplit=1)[0].casefold() for entry in entries} == {
        "annotated-types",
        "filelock",
        "pydantic",
        "pydantic-core",
        "pyyaml",
        "typing-extensions",
        "typing-inspection",
    }
