import json
import subprocess
import sys
from pathlib import Path

from research_skills_os.core.artifacts.store import ArtifactStore


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


def initialize_project(tmp_path: Path, *, provenance_gate: bool = False) -> tuple[Path, Path]:
    project = tmp_path / "run project 研究"
    capability = project / ".research-os" / "registry" / "capabilities" / "fixture"
    capability.mkdir(parents=True)
    gates = "exit_gates: [provenance.complete]\n" if provenance_gate else ""
    (capability / "capability.yaml").write_text(
        """spec_version: "1.0"
kind: capability
id: fixture-capability
version: "1.0"
input_types: []
output_types: [fixture_output]
"""
        + gates,
        encoding="utf-8",
        newline="\n",
    )
    initialized = run_cli(
        "project", "init", "--root", str(project), "--project-id", "project-1", cwd=tmp_path
    )
    assert initialized.returncode == 0, initialized.stderr
    request = project / "request.json"
    write_json(
        request,
        {
            "request_id": "request-1",
            "project_id": "project-1",
            "target": {"kind": "capability", "id": "fixture-capability"},
            "mode": "interactive",
            "goal": "Run fixture",
        },
    )
    return project, request


def test_run_commands_default_project_to_current_directory(tmp_path: Path):
    project, request = initialize_project(tmp_path)

    started = run_cli("run", "start", "--request", str(request), cwd=project)
    assert started.returncode == 0, started.stderr
    run_id = json.loads(started.stdout)["run_id"]

    begun = run_cli(
        "target", "begin", "--run", run_id, "--target", "fixture-capability", cwd=project
    )
    assert begun.returncode == 0, begun.stderr

    artifact = project / "artifacts" / "fixture" / "output.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project).register(
        "artifacts/fixture/output.json",
        artifact_id="fixture-1",
        artifact_type="fixture_output",
        schema_version="1.0",
        producing_capability="fixture-capability",
        provenance_references=["user-input:fixture"],
    )
    result = project / "result.json"
    write_json(
        result,
        {
            "request_id": "request-1",
            "run_id": run_id,
            "target_id": "fixture-capability",
            "status": "completed",
            "artifacts": [envelope.model_dump(mode="json")],
        },
    )

    completed = run_cli("target", "complete", "--run", run_id, "--result", str(result), cwd=project)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "paused"

    status = run_cli("run", "status", "--project", str(project), "--json", cwd=tmp_path)
    assert status.returncode == 0, status.stderr
    assert status.stderr == ""
    assert json.loads(status.stdout)["lifecycle"] == "paused"


def test_blocked_gate_returns_exit_code_three_with_json_outcome(tmp_path: Path):
    project, request = initialize_project(tmp_path, provenance_gate=True)
    started = run_cli("run", "start", "--request", str(request), cwd=project)
    run_id = json.loads(started.stdout)["run_id"]
    assert run_cli(
        "target", "begin", "--run", run_id, "--target", "fixture-capability", cwd=project
    ).returncode == 0
    artifact = project / "artifacts" / "fixture" / "unsupported.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project).register(
        "artifacts/fixture/unsupported.json",
        artifact_id="unsupported-1",
        artifact_type="fixture_output",
        schema_version="1.0",
        producing_capability="fixture-capability",
    )
    result = project / "blocked-result.json"
    write_json(
        result,
        {
            "request_id": "request-1",
            "run_id": run_id,
            "target_id": "fixture-capability",
            "status": "completed",
            "artifacts": [envelope.model_dump(mode="json")],
        },
    )

    completed = run_cli("target", "complete", "--run", run_id, "--result", str(result), cwd=project)

    assert completed.returncode == 3
    assert json.loads(completed.stdout)["action"] == "block"
    assert "blocked" in completed.stderr.casefold()


def test_invalid_run_transition_returns_execution_failure_code(tmp_path: Path):
    project, _ = initialize_project(tmp_path)

    completed = run_cli(
        "target",
        "begin",
        "--run",
        "not-active",
        "--target",
        "fixture-capability",
        cwd=project,
    )

    assert completed.returncode == 5
    assert completed.stdout == ""
    assert completed.stderr

