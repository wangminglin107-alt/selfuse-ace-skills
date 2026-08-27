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


def pause_fixture_run(tmp_path: Path) -> tuple[Path, str, Path]:
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
    return project, json.loads(completed.stdout)["checkpoint_id"], artifact


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
    assert (
        run_cli(
            "target", "begin", "--run", run_id, "--target", "fixture-capability", cwd=project
        ).returncode
        == 0
    )
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


def test_entry_gate_block_returns_exit_code_three_with_structured_json(tmp_path: Path):
    project, request = initialize_project(tmp_path)
    capability = project / ".research-os" / "registry" / "capabilities" / "fixture"
    (capability / "capability.yaml").write_text(
        """spec_version: "1.0"
kind: capability
id: fixture-capability
version: "1.0"
input_types: [required_input]
output_types: [fixture_output]
entry_gates: [inputs.required]
""",
        encoding="utf-8",
        newline="\n",
    )
    started = run_cli("run", "start", "--request", str(request), cwd=project)
    assert started.returncode == 0, started.stderr
    run_id = json.loads(started.stdout)["run_id"]

    begun = run_cli(
        "target", "begin", "--run", run_id, "--target", "fixture-capability", cwd=project
    )

    assert begun.returncode == 3
    payload = json.loads(begun.stdout)
    assert payload["action"] == "block"
    assert payload["status"] == "blocked"
    assert payload["failed_gates"] == ["inputs.required"]
    assert payload["findings"] == ["Missing required input types: required_input"]
    assert payload["remediation"] == ["Register the missing input artifacts before continuing."]
    assert "blocked" in begun.stderr.casefold()


def test_run_resume_reruns_verified_checkpoint_from_cli(tmp_path: Path):
    project, checkpoint_id, _ = pause_fixture_run(tmp_path)

    resumed = run_cli(
        "run",
        "resume",
        "--project",
        str(project),
        "--checkpoint",
        checkpoint_id,
        "--decision",
        "rerun",
        cwd=tmp_path,
    )

    assert resumed.returncode == 0, resumed.stderr
    payload = json.loads(resumed.stdout)
    assert payload["lifecycle"] == "running"
    assert payload["next_target_id"] == "fixture-capability"


def test_run_resume_requires_explicit_drift_decision_from_cli(tmp_path: Path):
    project, checkpoint_id, artifact = pause_fixture_run(tmp_path)
    artifact.write_text('{"edited":true}\n', encoding="utf-8", newline="\n")

    refused = run_cli(
        "run",
        "resume",
        "--project",
        str(project),
        "--checkpoint",
        checkpoint_id,
        "--decision",
        "continue",
        cwd=tmp_path,
    )

    assert refused.returncode == 4
    assert json.loads(refused.stdout)["status"] == "drifted"
    assert "drift" in refused.stderr.casefold()


def test_run_resume_accept_drift_creates_verified_rebaseline_from_cli(tmp_path: Path):
    project, checkpoint_id, artifact = pause_fixture_run(tmp_path)
    artifact.write_text('{"edited":true}\n', encoding="utf-8", newline="\n")

    accepted = run_cli(
        "run",
        "resume",
        "--project",
        str(project),
        "--checkpoint",
        checkpoint_id,
        "--decision",
        "accept_drift",
        cwd=tmp_path,
    )

    assert accepted.returncode == 0, accepted.stderr
    current = (project / ".research-os" / "current-checkpoint").read_text(encoding="utf-8").strip()
    assert current != checkpoint_id
    verified = run_cli(
        "checkpoint",
        "verify",
        "--project",
        str(project),
        "--id",
        current,
        cwd=tmp_path,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["status"] == "verified"
