from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from research_skills_os.integrations.zotero_obsidian.attachments import (
    AttachmentPreparationError,
    prepare_attachment,
)
from research_skills_os.integrations.zotero_obsidian.models import AttachmentSpec


def _pdf(path: Path) -> bytes:
    content = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def test_prepare_attachment_verifies_content_and_upload_metadata(tmp_path: Path) -> None:
    content = _pdf(tmp_path / "sources" / "paper.pdf")
    sha256 = hashlib.sha256(content).hexdigest()

    prepared = prepare_attachment(
        AttachmentSpec(status="local_file", path="sources/paper.pdf", sha256=sha256),
        tmp_path,
    )

    assert prepared.path == (tmp_path / "sources" / "paper.pdf").resolve()
    assert prepared.sha256 == sha256
    assert prepared.md5 == hashlib.md5(content, usedforsecurity=False).hexdigest()
    assert prepared.size == len(content)
    assert prepared.filename == "paper.pdf"


def test_prepare_attachment_rejects_hash_drift(tmp_path: Path) -> None:
    _pdf(tmp_path / "paper.pdf")
    with pytest.raises(AttachmentPreparationError, match="SHA-256 mismatch"):
        prepare_attachment(
            AttachmentSpec(status="local_file", path="paper.pdf", sha256="0" * 64),
            tmp_path,
        )


def test_prepare_attachment_rejects_non_pdf_content(tmp_path: Path) -> None:
    content = b"not a pdf"
    (tmp_path / "paper.pdf").write_bytes(content)
    with pytest.raises(AttachmentPreparationError, match="PDF signature"):
        prepare_attachment(
            AttachmentSpec(
                status="local_file",
                path="paper.pdf",
                sha256=hashlib.sha256(content).hexdigest(),
            ),
            tmp_path,
        )


def test_prepare_attachment_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AttachmentPreparationError, match="does not exist"):
        prepare_attachment(
            AttachmentSpec(status="local_file", path="missing.pdf", sha256="0" * 64),
            tmp_path,
        )

