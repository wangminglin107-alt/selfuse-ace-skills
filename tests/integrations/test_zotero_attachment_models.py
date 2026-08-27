from __future__ import annotations

import pytest
from pydantic import ValidationError

from research_skills_os.integrations.zotero_obsidian.models import (
    AttachmentSpec,
    SyncSource,
)


def test_local_pdf_attachment_requires_hash_and_contained_path() -> None:
    attachment = AttachmentSpec(
        status="local_file",
        path="sources/paper.pdf",
        sha256="a" * 64,
        source_url="https://example.org/paper.pdf",
    )

    assert attachment.path == "sources/paper.pdf"
    assert attachment.media_type == "application/pdf"
    assert attachment.mirror_policy == "link_only"


@pytest.mark.parametrize("path", ["C:/outside.pdf", "../outside.pdf", "/outside.pdf"])
def test_local_attachment_rejects_uncontained_path(path: str) -> None:
    with pytest.raises(ValidationError, match="contained relative path"):
        AttachmentSpec(status="local_file", path=path, sha256="a" * 64)


def test_metadata_only_attachment_cannot_claim_a_local_file() -> None:
    with pytest.raises(ValidationError, match="metadata_only"):
        AttachmentSpec(
            status="metadata_only",
            path="sources/paper.pdf",
            sha256="a" * 64,
        )


def test_attachment_free_source_remains_backward_compatible() -> None:
    source = SyncSource(
        source_id="paper",
        title="Paper",
        year=2024,
        item_type="journalArticle",
        content_sha256="b" * 64,
        note_source="sources/paper.md",
        inspected_content=True,
    )

    assert source.attachment is None
