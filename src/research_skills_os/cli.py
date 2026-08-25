"""Minimal Windows-safe command interface used by Research Skills OS skills."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_skills_os.cli_io import emit_error, emit_json
from research_skills_os.core.checkpoint.service import CheckpointService
from research_skills_os.core.contracts.models import ExecutionRequest, ExecutionResult
from research_skills_os.core.errors import ResearchSkillsError
from research_skills_os.core.orchestrator.coordinator import RunCoordinator
from research_skills_os.core.registry.loader import RegistryLoader
from research_skills_os.core.registry.models import RegistryCatalog
from research_skills_os.core.state.models import EventType, ProjectEvent
from research_skills_os.core.state.repository import StateRepository


def _catalog(project_root: Path) -> RegistryCatalog:
    registry_root = project_root / ".research-os" / "registry"
    capability_root = registry_root / "capabilities"
    workflow_root = registry_root / "workflows"
    return RegistryLoader(
        capability_roots=[capability_root] if capability_root.exists() else [],
        workflow_roots=[workflow_root] if workflow_root.exists() else [],
    ).load()


def _coordinator(project: str) -> RunCoordinator:
    root = Path(project).resolve(strict=True)
    return RunCoordinator(root, _catalog(root))


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-os")
    commands = parser.add_subparsers(dest="command", required=True)

    project = commands.add_parser("project")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_init = project_commands.add_parser("init")
    project_init.add_argument("--root", required=True)
    project_init.add_argument("--project-id", required=True)

    run = commands.add_parser("run")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    run_start = run_commands.add_parser("start")
    run_start.add_argument("--project", required=True)
    run_start.add_argument("--request", required=True)
    run_status = run_commands.add_parser("status")
    run_status.add_argument("--project", required=True)
    run_status.add_argument("--json", action="store_true")

    target = commands.add_parser("target")
    target_commands = target.add_subparsers(dest="target_command", required=True)
    target_begin = target_commands.add_parser("begin")
    target_begin.add_argument("--project", required=True)
    target_begin.add_argument("--run", required=True)
    target_begin.add_argument("--target", required=True)
    target_complete = target_commands.add_parser("complete")
    target_complete.add_argument("--project", required=True)
    target_complete.add_argument("--run", required=True)
    target_complete.add_argument("--result", required=True)

    checkpoint = commands.add_parser("checkpoint")
    checkpoint_commands = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    checkpoint_verify = checkpoint_commands.add_parser("verify")
    checkpoint_verify.add_argument("--project", required=True)
    checkpoint_verify.add_argument("--id", required=True)
    return parser


def execute(arguments: argparse.Namespace) -> None:
    if arguments.command == "project" and arguments.project_command == "init":
        root = Path(arguments.root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        repository = StateRepository(root)
        if repository.event_log.read_all():
            raise ResearchSkillsError("project is already initialized")
        stored = repository.append(
            ProjectEvent(
                event_id=f"project-init-{arguments.project_id}",
                type=EventType.PROJECT_INITIALIZED,
                payload={"project_id": arguments.project_id},
            )
        )
        emit_json({"project_id": arguments.project_id, "sequence": stored.sequence})
        return
    if arguments.command == "run" and arguments.run_command == "start":
        context = _coordinator(arguments.project).start(
            ExecutionRequest.model_validate(_load_json(arguments.request))
        )
        emit_json(context.model_dump(mode="json"))
        return
    if arguments.command == "run" and arguments.run_command == "status":
        state = StateRepository(Path(arguments.project)).load()
        emit_json(state.model_dump(mode="json"))
        return
    if arguments.command == "target" and arguments.target_command == "begin":
        context = _coordinator(arguments.project).begin_target(arguments.run, arguments.target)
        emit_json(context.model_dump(mode="json"))
        return
    if arguments.command == "target" and arguments.target_command == "complete":
        outcome = _coordinator(arguments.project).complete_target(
            arguments.run,
            ExecutionResult.model_validate(_load_json(arguments.result)),
        )
        emit_json(outcome.model_dump(mode="json"))
        return
    if arguments.command == "checkpoint" and arguments.checkpoint_command == "verify":
        verification = CheckpointService(Path(arguments.project)).verify_resume(arguments.id)
        emit_json(verification.model_dump(mode="json"))
        return
    raise ResearchSkillsError("unsupported command")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        execute(arguments)
    except (ResearchSkillsError, ValueError, OSError) as exc:
        emit_error(str(exc))
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
