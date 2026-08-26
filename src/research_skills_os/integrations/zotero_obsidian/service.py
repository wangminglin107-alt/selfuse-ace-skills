"""Transactional coordination between Zotero identity and Obsidian notes."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from research_skills_os.integrations.zotero_obsidian.models import (
    SyncActionKind,
    SyncPlan,
    SyncSpec,
    SyncState,
    SyncStateRecord,
)
from research_skills_os.integrations.zotero_obsidian.obsidian import (
    NoteWriteRequest,
    ObsidianPathError,
    ObsidianWriter,
)
from research_skills_os.integrations.zotero_obsidian.planner import (
    build_sync_plan,
    source_identity,
)
from research_skills_os.integrations.zotero_obsidian.zotero import ZoteroClient


class SyncResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: SyncState
    created_or_linked: tuple[str, ...]
    refreshed_notes: tuple[str, ...]
    skipped: tuple[str, ...]


def _load_note_sources(spec: SyncSpec, project_root: Path) -> dict[str, str]:
    resolved_root = project_root.resolve()
    notes: dict[str, str] = {}
    for source in spec.sources:
        if not source.inspected_content:
            raise ValueError(f"{source.source_id} does not have inspected content")
        path = (resolved_root / source.note_source).resolve()
        if not path.is_relative_to(resolved_root):
            raise ObsidianPathError("note source is outside the project root")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"{source.source_id} note source is empty")
        notes[source.source_id] = text
    return notes


class ZoteroObsidianBridge:
    def __init__(self, *, zotero: ZoteroClient, vault_root: Path) -> None:
        self._zotero = zotero
        self._vault_root = vault_root.resolve()
        self._obsidian = ObsidianWriter(self._vault_root)

    def preview(self, spec: SyncSpec, state: SyncState) -> SyncPlan:
        return build_sync_plan(spec, state)

    def apply(self, spec: SyncSpec, state: SyncState, *, project_root: Path) -> SyncResult:
        notes = _load_note_sources(spec, project_root)
        plan = build_sync_plan(spec, state)
        sources = {source.source_id: source for source in spec.sources}
        records = dict(state.records)
        item_keys: dict[str, str] = {}
        upserts = [action for action in plan.actions if action.kind is SyncActionKind.UPSERT]
        collection_key = self._zotero.ensure_collection(spec.zotero_collection) if upserts else None

        for action in plan.actions:
            source = sources[action.source_id]
            if action.kind is SyncActionKind.SKIP:
                continue
            if action.kind is SyncActionKind.REFRESH_NOTE:
                item_keys[action.source_id] = records[action.source_id].zotero_item_key
                continue
            assert collection_key is not None
            item_key = self._zotero.find_item(action.identity)
            if item_key is None:
                item_key = self._zotero.create_item(source, collection_key)
            else:
                self._zotero.add_to_collection(item_key, collection_key)
            item_keys[action.source_id] = item_key

        created_or_linked: list[str] = []
        refreshed_notes: list[str] = []
        skipped: list[str] = []
        for action in plan.actions:
            source = sources[action.source_id]
            if action.kind is SyncActionKind.SKIP:
                skipped.append(source.source_id)
                continue
            item_key = item_keys[source.source_id]
            note_path = self._obsidian.write_source_note(
                NoteWriteRequest(
                    project_path=spec.obsidian_project,
                    source_id=source.source_id,
                    title=source.title,
                    year=source.year,
                    zotero_item_key=item_key,
                    content_sha256=source.content_sha256,
                    generated_markdown=notes[source.source_id],
                )
            )
            records[source.source_id] = SyncStateRecord(
                identity=source_identity(source),
                content_sha256=source.content_sha256,
                zotero_item_key=item_key,
                obsidian_note=note_path.relative_to(self._vault_root).as_posix(),
            )
            if action.kind is SyncActionKind.UPSERT:
                created_or_linked.append(source.source_id)
            else:
                refreshed_notes.append(source.source_id)

        return SyncResult(
            state=SyncState(records=records),
            created_or_linked=tuple(created_or_linked),
            refreshed_notes=tuple(refreshed_notes),
            skipped=tuple(skipped),
        )
