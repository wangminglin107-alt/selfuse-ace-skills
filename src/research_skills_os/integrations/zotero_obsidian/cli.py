"""Dry-run-first command line entry for Zotero and Obsidian synchronization."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from research_skills_os.integrations.zotero_obsidian.models import SyncSpec, SyncState
from research_skills_os.integrations.zotero_obsidian.service import ZoteroObsidianBridge
from research_skills_os.integrations.zotero_obsidian.zotero import (
    LocalZoteroClient,
    ZoteroClient,
    ZoteroError,
    ZoteroUnavailable,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or apply Zotero-Obsidian project sync")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _load_spec(path: Path) -> SyncSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SyncSpec.model_validate(raw)


def _load_state(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    return SyncState.model_validate_json(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: SyncState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (state.model_dump_json(indent=2) + "\n").encode()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as temporary:
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def run(
    argv: Sequence[str] | None = None,
    *,
    zotero_factory: Callable[[], ZoteroClient] = LocalZoteroClient,
) -> int:
    args = _parser().parse_args(argv)
    spec_path: Path = args.spec.resolve()
    state_path: Path = (
        args.state.resolve()
        if args.state is not None
        else spec_path.parent / "artifacts" / "library-sync-state.json"
    )
    try:
        spec = _load_spec(spec_path)
        state = _load_state(state_path)
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ValidationError, TypeError) as error:
        _print({"status": "invalid", "message": str(error)})
        return 2

    bridge = ZoteroObsidianBridge(zotero=zotero_factory(), vault_root=args.vault)
    if not args.apply:
        plan = bridge.preview(spec, state)
        _print(
            {
                "mode": "preview",
                "project_id": plan.project_id,
                "actions": [action.model_dump(mode="json") for action in plan.actions],
            }
        )
        return 0

    try:
        result = bridge.apply(spec, state, project_root=spec_path.parent)
    except ZoteroUnavailable as error:
        _print({"status": "zotero_unavailable", "message": str(error)})
        return 3
    except (OSError, ValueError, ZoteroError) as error:
        _print({"status": "blocked", "message": str(error)})
        return 4
    _save_state(state_path, result.state)
    _print(
        {
            "mode": "apply",
            "project_id": spec.project_id,
            "created_or_linked": list(result.created_or_linked),
            "refreshed_notes": list(result.refreshed_notes),
            "skipped": list(result.skipped),
        }
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
