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


def test_cli_runs_interactive_target_and_verifies_checkpoint(tmp_path: Path):
    project_root = tmp_path / "CLI project 研究"
    project_root.mkdir()
    registry = project_root / ".research-os" / "registry" / "capabilities" / "research-framing"
    registry.mkdir(parents=True)
    (registry / "capability.yaml").write_text(
        """spec_version: "1.0"
kind: capability
id: research-framing
version: "1.0"
input_types: []
output_types: [research_brief]
""",
        encoding="utf-8",
        newline="\n",
    )
    initialized = run_cli(
        "project", "init", "--root", str(project_root), "--project-id", "project-1", cwd=tmp_path
    )
    assert initialized.returncode == 0, initialized.stderr

    request_path = project_root / "request.json"
    write_json(
        request_path,
        {
            "request_id": "request-1",
            "project_id": "project-1",
            "target": {"kind": "capability", "id": "research-framing"},
            "mode": "interactive",
            "goal": "Frame idea",
        },
    )
    started = run_cli(
        "run", "start", "--project", str(project_root), "--request", str(request_path), cwd=tmp_path
    )
    assert started.returncode == 0, started.stderr
    run_id = json.loads(started.stdout)["run_id"]
    begun = run_cli(
        "target",
        "begin",
        "--project",
        str(project_root),
        "--run",
        run_id,
        "--target",
        "research-framing",
        cwd=tmp_path,
    )
    assert begun.returncode == 0, begun.stderr

    artifact_path = project_root / "artifacts" / "research-framing" / "brief.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("brief\n", encoding="utf-8", newline="\n")
    envelope = ArtifactStore(project_root).register(
        "artifacts/research-framing/brief.md",
        artifact_id="brief-1",
        artifact_type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
        provenance_references=["user-input:idea-1"],
    )
    result_path = project_root / "result.json"
    write_json(
        result_path,
        {
            "request_id": "request-1",
            "run_id": run_id,
            "target_id": "research-framing",
            "status": "completed",
            "artifacts": [envelope.model_dump(mode="json")],
        },
    )
    completed = run_cli(
        "target",
        "complete",
        "--project",
        str(project_root),
        "--run",
        run_id,
        "--result",
        str(result_path),
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr
    checkpoint_id = json.loads(completed.stdout)["checkpoint_id"]

    verified = run_cli(
        "checkpoint",
        "verify",
        "--project",
        str(project_root),
        "--id",
        checkpoint_id,
        cwd=tmp_path,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["status"] == "verified"

    status = run_cli("run", "status", "--project", str(project_root), "--json", cwd=tmp_path)
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["lifecycle"] == "paused"
