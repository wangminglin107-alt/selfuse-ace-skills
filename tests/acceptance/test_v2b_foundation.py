from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from research_skills_os.integrations.zotero_obsidian import SyncSource, SyncSpec, SyncState
from research_skills_os.integrations.zotero_obsidian.attachments import PreparedAttachment
from research_skills_os.integrations.zotero_obsidian.service import ZoteroObsidianBridge


@dataclass
class FakeZotero:
    items: dict[str, str] = field(default_factory=dict)
    attachments: dict[tuple[str, str], str] = field(default_factory=dict)

    def ensure_collection(self, name: str) -> str:
        return "COLL0001"

    def find_item(self, identity: str) -> str | None:
        return self.items.get(identity)

    def create_item(self, source: SyncSource, collection_key: str) -> str:
        self.items[f"doi:{source.doi}"] = "ITEM0001"
        return "ITEM0001"

    def add_to_collection(self, item_key: str, collection_key: str) -> None:
        return None

    def find_attachment(self, parent_key: str, sha256: str) -> str | None:
        return self.attachments.get((parent_key, sha256))

    def create_attachment(self, parent_key: str, prepared: PreparedAttachment) -> str:
        self.attachments[(parent_key, prepared.sha256)] = "ATT00001"
        return "ATT00001"


def test_pdf_archive_is_idempotent_across_zotero_and_obsidian(tmp_path: Path) -> None:
    project = tmp_path / "project"
    vault = tmp_path / "vault"
    note = project / "sources" / "paper.md"
    pdf = project / "sources" / "paper.pdf"
    note.parent.mkdir(parents=True)
    note.write_text("Evidence ID: E-01", encoding="utf-8")
    payload = b"%PDF-1.7\n%%EOF\n"
    pdf.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    source = SyncSource(
        source_id="paper",
        title="Verified paper",
        year=2026,
        item_type="journalArticle",
        doi="10.1000/verified",
        content_sha256="a" * 64,
        note_source="sources/paper.md",
        inspected_content=True,
        attachment={
            "status": "local_file",
            "path": "sources/paper.pdf",
            "sha256": digest,
        },
    )
    spec = SyncSpec(
        version=1,
        project_id="acceptance",
        zotero_collection="Acceptance",
        obsidian_project="Research/Acceptance",
        sources=(source,),
    )
    zotero = FakeZotero()
    bridge = ZoteroObsidianBridge(zotero=zotero, vault_root=vault)

    first = bridge.apply(spec, SyncState(), project_root=project)
    second = bridge.apply(spec, first.state, project_root=project)

    record = second.state.records["paper"]
    assert len(zotero.items) == 1
    assert len(zotero.attachments) == 1
    assert record.attachment_sha256 == digest
    assert record.zotero_attachment_key == "ATT00001"
    assert second.skipped == ("paper",)
    assert (vault / record.obsidian_note).read_text(encoding="utf-8")
