from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from research_skills_os.integrations.zotero_obsidian import SyncSource, SyncSpec, SyncState
from research_skills_os.integrations.zotero_obsidian.service import ZoteroObsidianBridge
from research_skills_os.integrations.zotero_obsidian.zotero import ZoteroUnavailable


@dataclass
class InMemoryZotero:
    items: dict[str, str] = field(default_factory=dict)
    collections: dict[str, str] = field(default_factory=dict)
    fail_collection: bool = False
    created_items: int = 0

    def ensure_collection(self, name: str) -> str:
        if self.fail_collection:
            raise ZoteroUnavailable("offline")
        return self.collections.setdefault(name, "COLL1234")

    def find_item(self, identity: str) -> str | None:
        return self.items.get(identity)

    def create_item(self, source: SyncSource, collection_key: str) -> str:
        self.created_items += 1
        key = f"ITEM{self.created_items:04d}"
        identity = "doi:" + source.doi.casefold() if source.doi else f"title:{source.title}"
        self.items[identity] = key
        return key

    def add_to_collection(self, item_key: str, collection_key: str) -> None:
        return None


def write_note_source(project_root: Path, text: str = "Evidence ID: E-01") -> None:
    note = project_root / "notes" / "source.md"
    note.parent.mkdir(parents=True)
    note.write_text(text, encoding="utf-8")


def source_record(**overrides: object) -> SyncSource:
    values: dict[str, object] = {
        "source_id": "source-1",
        "title": "A verified source",
        "year": 2026,
        "item_type": "journalArticle",
        "authors": ("Researcher One",),
        "doi": "10.1000/test",
        "url": "https://example.org/source",
        "content_sha256": "a" * 64,
        "note_source": "notes/source.md",
        "inspected_content": True,
    }
    values.update(overrides)
    return SyncSource.model_validate(values)


def sync_spec(*sources: SyncSource) -> SyncSpec:
    return SyncSpec(
        version=1,
        project_id="pilot",
        zotero_collection="Pilot Collection",
        obsidian_project="Research/Pilot",
        sources=sources or (source_record(),),
    )


def test_preview_has_no_zotero_or_obsidian_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "project"
    vault_root = tmp_path / "vault"
    write_note_source(project_root)
    zotero = InMemoryZotero()
    bridge = ZoteroObsidianBridge(zotero=zotero, vault_root=vault_root)

    plan = bridge.preview(sync_spec(), SyncState())

    assert [action.kind.value for action in plan.actions] == ["upsert"]
    assert zotero.collections == {}
    assert zotero.items == {}
    assert not vault_root.exists()


def test_existing_zotero_item_is_reused(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    vault_root = tmp_path / "vault"
    write_note_source(project_root)
    zotero = InMemoryZotero(items={"doi:10.1000/test": "EXIST123"})
    bridge = ZoteroObsidianBridge(zotero=zotero, vault_root=vault_root)

    result = bridge.apply(sync_spec(), SyncState(), project_root=project_root)

    record = result.state.records["source-1"]
    assert record.zotero_item_key == "EXIST123"
    assert zotero.created_items == 0
    assert (vault_root / record.obsidian_note).exists()


def test_zotero_failure_prevents_obsidian_mutation(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    vault_root = tmp_path / "vault"
    write_note_source(project_root)
    bridge = ZoteroObsidianBridge(
        zotero=InMemoryZotero(fail_collection=True), vault_root=vault_root
    )

    with pytest.raises(ZoteroUnavailable, match="offline"):
        bridge.apply(sync_spec(), SyncState(), project_root=project_root)

    assert list(vault_root.rglob("*.md")) == []


def test_successful_apply_returns_complete_mapping_state(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    vault_root = tmp_path / "vault"
    write_note_source(project_root)
    source = source_record()
    result = ZoteroObsidianBridge(
        zotero=InMemoryZotero(), vault_root=vault_root
    ).apply(sync_spec(source), SyncState(), project_root=project_root)

    record = result.state.records[source.source_id]
    assert record.identity == "doi:10.1000/test"
    assert record.content_sha256 == "a" * 64
    assert record.obsidian_note == "Research/Pilot/Sources/Papers/source-1.md"
    assert result.created_or_linked == ("source-1",)
    assert result.refreshed_notes == ()
    assert result.skipped == ()


def test_second_apply_is_a_noop(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    vault_root = tmp_path / "vault"
    write_note_source(project_root)
    zotero = InMemoryZotero()
    bridge = ZoteroObsidianBridge(zotero=zotero, vault_root=vault_root)
    first = bridge.apply(sync_spec(), SyncState(), project_root=project_root)
    note = vault_root / first.state.records["source-1"].obsidian_note
    before = note.read_bytes()

    second = bridge.apply(sync_spec(), first.state, project_root=project_root)

    assert second.created_or_linked == ()
    assert second.refreshed_notes == ()
    assert second.skipped == ("source-1",)
    assert note.read_bytes() == before
    assert zotero.created_items == 1


def test_uninspected_source_cannot_be_promoted_to_obsidian(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    vault_root = tmp_path / "vault"
    write_note_source(project_root)
    source = source_record(inspected_content=False)

    with pytest.raises(ValueError, match="inspected content"):
        ZoteroObsidianBridge(zotero=InMemoryZotero(), vault_root=vault_root).apply(
            sync_spec(source), SyncState(), project_root=project_root
        )

    assert list(vault_root.rglob("*.md")) == []
