"""Read-only validation for local PDF attachments before Zotero mutation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from research_skills_os.integrations.zotero_obsidian.models import (
    AttachmentSpec,
    AttachmentStatus,
)


class AttachmentPreparationError(ValueError):
    """Raised when a declared attachment cannot be trusted for upload."""


@dataclass(frozen=True)
class PreparedAttachment:
    path: Path
    filename: str
    sha256: str
    md5: str
    size: int
    mtime_ms: int
    media_type: str
    source_url: str | None


def prepare_attachment(spec: AttachmentSpec, project_root: Path) -> PreparedAttachment:
    """Resolve and verify one declared local PDF without changing either library."""

    if spec.status is not AttachmentStatus.LOCAL_FILE or spec.path is None or spec.sha256 is None:
        raise AttachmentPreparationError("attachment is not a declared local_file")
    root = project_root.resolve()
    path = (root / spec.path).resolve()
    if not path.is_relative_to(root):
        raise AttachmentPreparationError("attachment path escapes project root")
    if not path.is_file():
        raise AttachmentPreparationError(f"attachment does not exist: {spec.path}")
    content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise AttachmentPreparationError("attachment does not have a PDF signature")
    digest = hashlib.sha256(content).hexdigest()
    if digest != spec.sha256:
        raise AttachmentPreparationError("attachment SHA-256 mismatch")
    stat = path.stat()
    return PreparedAttachment(
        path=path,
        filename=path.name,
        sha256=digest,
        md5=hashlib.md5(content, usedforsecurity=False).hexdigest(),
        size=len(content),
        mtime_ms=int(stat.st_mtime * 1000),
        media_type=spec.media_type,
        source_url=spec.source_url,
    )
