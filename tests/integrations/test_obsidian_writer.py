from __future__ import annotations

import os
from pathlib import Path

import pytest

from research_skills_os.integrations.zotero_obsidian.obsidian import (
    NoteWriteRequest,
    ObsidianOwnershipError,
    ObsidianPathError,
    ObsidianWriter,
)


def note_request(**overrides: object) -> NoteWriteRequest:
    values: dict[str, object] = {
        "project_path": "Research/GSMA情绪与互动",
        "source_id": "brady-2017",
        "title": "Emotion shapes the diffusion of moralized content",
        "year": 2017,
        "zotero_item_key": "ABCD1234",
        "content_sha256": "a" * 64,
        "generated_markdown": "## Evidence Record\n\nEvidence ID: E-BRADY-01\n",
    }
    values.update(overrides)
    return NoteWriteRequest.model_validate(values)


def test_new_note_contains_zotero_link_and_human_section(tmp_path: Path) -> None:
    path = ObsidianWriter(tmp_path).write_source_note(note_request())
    assert path.relative_to(tmp_path).as_posix() == (
        "Research/GSMA情绪与互动/Sources/Papers/brady-2017.md"
    )
    text = path.read_text(encoding="utf-8")
    assert "zotero://select/library/items/ABCD1234" in text
    assert "<!-- research-os:auto:start -->" in text
    assert "Evidence ID: E-BRADY-01" in text
    assert "<!-- research-os:auto:end -->" in text
    assert "## 我的想法" in text


def test_rerun_replaces_only_generated_block(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    path = writer.write_source_note(note_request(generated_markdown="first generated text"))
    path.write_text(
        path.read_text(encoding="utf-8") + "\n我在自动区外写的内容。\n",
        encoding="utf-8",
    )

    writer.write_source_note(note_request(generated_markdown="second generated text"))

    text = path.read_text(encoding="utf-8")
    assert "second generated text" in text
    assert "first generated text" not in text
    assert text.endswith("\n我在自动区外写的内容。\n")


def test_unchanged_note_is_not_rewritten(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    request = note_request()
    path = writer.write_source_note(request)
    old_ns = path.stat().st_mtime_ns
    os.utime(path, ns=(old_ns - 1_000_000_000, old_ns - 1_000_000_000))
    expected_ns = path.stat().st_mtime_ns

    returned = writer.write_source_note(request)

    assert returned == path
    assert path.stat().st_mtime_ns == expected_ns


def test_project_path_cannot_escape_vault(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    with pytest.raises(ObsidianPathError, match="outside the vault"):
        writer.write_source_note(note_request(project_path="../private"))
    assert not (tmp_path.parent / "private").exists()


def test_existing_unmanaged_note_is_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "Research" / "GSMA情绪与互动" / "Sources" / "Papers"
    path.mkdir(parents=True)
    note = path / "brady-2017.md"
    note.write_text("我的既有笔记", encoding="utf-8")

    with pytest.raises(ObsidianOwnershipError, match="generated markers"):
        ObsidianWriter(tmp_path).write_source_note(note_request())

    assert note.read_text(encoding="utf-8") == "我的既有笔记"


def test_source_id_is_sanitized_to_one_filename(tmp_path: Path) -> None:
    path = ObsidianWriter(tmp_path).write_source_note(note_request(source_id="Brady: 2017 / PNAS"))
    assert path.name == "brady-2017-pnas.md"
    assert path.parent.relative_to(tmp_path).as_posix() == (
        "Research/GSMA情绪与互动/Sources/Papers"
    )
