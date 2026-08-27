from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from research_skills_os.integrations.zotero_obsidian.cli import run
from research_skills_os.integrations.zotero_obsidian.models import SyncSource
from research_skills_os.integrations.zotero_obsidian.zotero import (
    ZoteroAuthorizationDenied,
    ZoteroUnavailable,
)


@dataclass
class InMemoryZotero:
    items: dict[str, str] = field(default_factory=dict)
    collections: dict[str, str] = field(default_factory=dict)

    def ensure_collection(self, name: str) -> str:
        return self.collections.setdefault(name, "COLL1234")

    def find_item(self, identity: str) -> str | None:
        return self.items.get(identity)

    def create_item(self, source: SyncSource, collection_key: str) -> str:
        self.items["doi:10.1000/test"] = "ITEM1234"
        return "ITEM1234"

    def add_to_collection(self, item_key: str, collection_key: str) -> None:
        return None


class OfflineZotero(InMemoryZotero):
    def ensure_collection(self, name: str) -> str:
        raise ZoteroUnavailable("offline")


class DeniedZotero(InMemoryZotero):
    def ensure_collection(self, name: str) -> str:
        raise ZoteroAuthorizationDenied("authorization denied")


def write_project(tmp_path: Path, *, obsidian_project: str = "Research/Pilot") -> Path:
    project = tmp_path / "project"
    (project / "notes").mkdir(parents=True)
    (project / "notes" / "source.md").write_text("Evidence ID: E-01", encoding="utf-8")
    spec = {
        "version": 1,
        "project_id": "pilot",
        "zotero_collection": "Pilot Collection",
        "obsidian_project": obsidian_project,
        "sources": [
            {
                "source_id": "source-1",
                "title": "A verified source",
                "year": 2026,
                "item_type": "journalArticle",
                "authors": ["Researcher One"],
                "doi": "10.1000/test",
                "url": "https://example.org/source",
                "content_sha256": "a" * 64,
                "note_source": "notes/source.md",
                "inspected_content": True,
            }
        ],
    }
    spec_path = project / "library-sync.yaml"
    spec_path.write_text(
        yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return spec_path


def factory(client: InMemoryZotero) -> Callable[[], InMemoryZotero]:
    return lambda: client


def test_preview_reports_actions_without_writing(tmp_path: Path, capsys: object) -> None:
    spec = write_project(tmp_path)
    vault = tmp_path / "vault"
    client = InMemoryZotero()

    exit_code = run(["--spec", str(spec), "--vault", str(vault)], zotero_factory=factory(client))

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output == {
        "mode": "preview",
        "project_id": "pilot",
        "actions": [
            {
                "source_id": "source-1",
                "identity": "doi:10.1000/test",
                "kind": "upsert",
                "reason": "source has no completed sync state",
            }
        ],
    }
    assert client.collections == {}
    assert not vault.exists()
    assert not (spec.parent / "artifacts" / "library-sync-state.json").exists()
    assert str(tmp_path) not in json.dumps(output)


def test_invalid_spec_returns_exit_code_two(tmp_path: Path, capsys: object) -> None:
    spec = write_project(tmp_path, obsidian_project="../escape")

    exit_code = run(
        ["--spec", str(spec), "--vault", str(tmp_path / "vault")],
        zotero_factory=factory(InMemoryZotero()),
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output["status"] == "invalid"


def test_apply_writes_state_and_obsidian_note(tmp_path: Path, capsys: object) -> None:
    spec = write_project(tmp_path)
    vault = tmp_path / "vault"
    state = spec.parent / "artifacts" / "library-sync-state.json"

    exit_code = run(
        ["--spec", str(spec), "--vault", str(vault), "--apply"],
        zotero_factory=factory(InMemoryZotero()),
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output["mode"] == "apply"
    assert output["created_or_linked"] == ["source-1"]
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["records"]["source-1"]["zotero_item_key"] == "ITEM1234"
    note = vault / saved["records"]["source-1"]["obsidian_note"]
    assert note.exists()


def test_unavailable_zotero_returns_exit_code_three_without_state(
    tmp_path: Path, capsys: object
) -> None:
    spec = write_project(tmp_path)
    state = spec.parent / "artifacts" / "library-sync-state.json"

    exit_code = run(
        ["--spec", str(spec), "--vault", str(tmp_path / "vault"), "--apply"],
        zotero_factory=factory(OfflineZotero()),
    )

    assert exit_code == 3
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output == {"status": "zotero_unavailable", "message": "offline"}
    assert not state.exists()


def test_denied_zotero_is_reported_as_blocked_without_traceback_or_state(
    tmp_path: Path, capsys: object
) -> None:
    spec = write_project(tmp_path)
    state = spec.parent / "artifacts" / "library-sync-state.json"

    exit_code = run(
        ["--spec", str(spec), "--vault", str(tmp_path / "vault"), "--apply"],
        zotero_factory=factory(DeniedZotero()),
    )

    assert exit_code == 4
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output == {"status": "blocked", "message": "authorization denied"}
    assert not state.exists()
