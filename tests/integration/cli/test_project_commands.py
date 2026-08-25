import json
import subprocess
import sys
from pathlib import Path


def run_cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "research_skills_os.cli", *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")


def test_project_init_preserves_already_tokenized_windows_path_with_spaces_and_cjk(tmp_path: Path):
    project = tmp_path / "quoted '研究' project"

    completed = run_cli(
        "project", "init", "--root", str(project), "--project-id", "项目-1", cwd=tmp_path
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout)["project_id"] == "项目-1"
    assert (project / ".research-os" / "events.jsonl").is_file()
    assert not (tmp_path / "quoted").exists()


def test_validate_request_emits_canonical_json(tmp_path: Path):
    request = tmp_path / "请求 with spaces.json"
    write_json(
        request,
        {
            "request_id": "request-1",
            "project_id": "project-1",
            "target": {"kind": "capability", "id": "research-framing"},
            "mode": "interactive",
            "goal": "Frame an idea",
        },
    )

    completed = run_cli("validate", "request", str(request), cwd=tmp_path)

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout)["contract_version"] == "1.0"


def test_invalid_request_uses_validation_exit_code_and_stderr(tmp_path: Path):
    request = tmp_path / "invalid.json"
    write_json(request, {"request_id": "missing-required-fields"})

    completed = run_cli("validate", "request", str(request), cwd=tmp_path)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "validation" in completed.stderr.casefold()

