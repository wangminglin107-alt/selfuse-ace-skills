"""Ownership-safe, idempotent Obsidian note writes."""

from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

AUTO_START = "<!-- research-os:auto:start -->"
AUTO_END = "<!-- research-os:auto:end -->"


class ObsidianPathError(ValueError):
    """Raised when a requested note destination escapes the authorized vault."""


class ObsidianOwnershipError(ValueError):
    """Raised when an existing note has no bridge-owned generated region."""


class NoteWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_path: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    year: int = Field(ge=1000, le=9999)
    zotero_item_key: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_markdown: str = Field(min_length=1)


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    slug = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-_")
    if not slug:
        raise ObsidianPathError("source_id does not produce a safe filename")
    return slug


def _generated_block(request: NoteWriteRequest) -> str:
    markdown = request.generated_markdown.strip()
    return (
        f"{AUTO_START}\n"
        "## 文献链接\n\n"
        f"[在 Zotero 中打开](zotero://select/library/items/{request.zotero_item_key})\n\n"
        f"{markdown}\n"
        f"{AUTO_END}"
    )


def render_source_note(request: NoteWriteRequest) -> str:
    title = json.dumps(request.title, ensure_ascii=False)
    return (
        "---\n"
        f"title: {title}\n"
        f"year: {request.year}\n"
        f"zotero_key: {request.zotero_item_key}\n"
        f"source_sha256: {request.content_sha256}\n"
        "tags:\n"
        "  - research/source\n"
        "---\n\n"
        f"# {request.title}\n\n"
        f"{_generated_block(request)}\n\n"
        "## 我的想法\n\n"
    )


def merge_generated_block(existing: str, generated: str) -> str:
    start = existing.find(AUTO_START)
    end = existing.find(AUTO_END)
    if start < 0 or end < start:
        raise ObsidianOwnershipError("existing note does not contain generated markers")
    end += len(AUTO_END)
    return existing[:start] + generated + existing[end:]


class ObsidianWriter:
    def __init__(self, vault_root: Path) -> None:
        self._vault_root = vault_root.resolve()

    def _destination(self, request: NoteWriteRequest) -> Path:
        filename = f"{_slugify(request.source_id)}.md"
        candidate = (
            self._vault_root
            / request.project_path
            / "Sources"
            / "Papers"
            / filename
        ).resolve()
        if not candidate.is_relative_to(self._vault_root):
            raise ObsidianPathError("note destination is outside the vault")
        return candidate

    def write_source_note(self, request: NoteWriteRequest) -> Path:
        destination = self._destination(request)
        if destination.exists():
            existing = destination.read_text(encoding="utf-8")
            updated = merge_generated_block(existing, _generated_block(request))
        else:
            updated = render_source_note(request)
        encoded = updated.encode("utf-8")
        if destination.exists() and destination.read_bytes() == encoded:
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent,
                delete=False,
            ) as temporary:
                temporary.write(encoded)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return destination
