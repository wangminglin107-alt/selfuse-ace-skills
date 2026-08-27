from __future__ import annotations

import pytest
from pydantic import ValidationError

from research_skills_os.integrations.zotero_obsidian import (
    SyncActionKind,
    SyncSource,
    SyncSpec,
    SyncState,
    SyncStateRecord,
    build_sync_plan,
    source_identity,
)


def source_record(**overrides: object) -> SyncSource:
    values: dict[str, object] = {
        "source_id": "brady-2017",
        "title": "Emotion shapes the diffusion of moralized content",
        "year": 2017,
        "item_type": "journalArticle",
        "authors": ("William J. Brady", "Ana P. Gantman"),
        "doi": "HTTPS://DOI.ORG/10.1073/PNAS.1618923114 ",
        "url": "https://www.pnas.org/doi/10.1073/pnas.1618923114",
        "content_sha256": "a" * 64,
        "note_source": "notes/brady-2017.md",
        "inspected_content": True,
    }
    values.update(overrides)
    return SyncSource.model_validate(values)


def sync_spec(*sources: SyncSource) -> SyncSpec:
    return SyncSpec(
        version=1,
        project_id="gsma-sentiment-engagement",
        zotero_collection="Pilot｜GSMA情绪与互动",  # noqa: RUF001
        obsidian_project="Research/GSMA情绪与互动",
        sources=sources or (source_record(),),
    )


def state_record(source: SyncSource) -> SyncStateRecord:
    return SyncStateRecord(
        identity="doi:10.1073/pnas.1618923114",
        content_sha256=source.content_sha256,
        zotero_item_key="ABCD1234",
        obsidian_note="Research/GSMA情绪与互动/Sources/Papers/brady-2017.md",
    )


def test_doi_identity_is_normalized_before_url() -> None:
    assert source_identity(source_record()) == "doi:10.1073/pnas.1618923114"


def test_canonical_url_is_used_when_doi_is_absent() -> None:
    source = source_record(
        source_id="norc-methodology",
        doi=None,
        url="HTTPS://GSS.NORC.ORG/gsma.html?utm_source=test#methods",
    )
    assert source_identity(source) == "url:https://gss.norc.org/gsma.html"


def test_title_and_year_are_last_identity_fallback() -> None:
    source = source_record(doi=None, url=None, title="  A   Small STUDY ")
    assert source_identity(source) == "title-year:a small study|2017"


def test_duplicate_bibliographic_identity_is_rejected() -> None:
    first = source_record(source_id="first")
    second = source_record(source_id="second")
    with pytest.raises(ValueError, match="bibliographic identity collision"):
        sync_spec(first, second)


def test_empty_source_set_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SyncSpec(
            version=1,
            project_id="gsma-sentiment-engagement",
            zotero_collection="Pilot",
            obsidian_project="Research/GSMA",
            sources=(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content_sha256", "not-a-hash"),
        ("note_source", "../private.md"),
    ],
)
def test_unsafe_source_values_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        source_record(**{field: value})


def test_new_source_is_planned_for_upsert() -> None:
    plan = build_sync_plan(sync_spec(), SyncState())
    assert [(action.kind, action.reason) for action in plan.actions] == [
        (SyncActionKind.UPSERT, "source has no completed sync state")
    ]


def test_unchanged_source_is_skipped() -> None:
    source = source_record()
    state = SyncState(records={source.source_id: state_record(source)})
    plan = build_sync_plan(sync_spec(source), state)
    assert [(action.kind, action.reason) for action in plan.actions] == [
        (SyncActionKind.SKIP, "identity and content hash unchanged")
    ]


def test_changed_content_refreshes_note_without_new_identity() -> None:
    old_source = source_record()
    changed_source = source_record(content_sha256="b" * 64)
    state = SyncState(records={old_source.source_id: state_record(old_source)})
    plan = build_sync_plan(sync_spec(changed_source), state)
    assert [(action.kind, action.reason) for action in plan.actions] == [
        (SyncActionKind.REFRESH_NOTE, "content hash changed")
    ]


def test_changed_identity_requires_upsert() -> None:
    source = source_record(doi="10.9999/replacement")
    state = SyncState(records={source.source_id: state_record(source)})
    plan = build_sync_plan(sync_spec(source), state)
    assert [(action.kind, action.reason) for action in plan.actions] == [
        (SyncActionKind.UPSERT, "bibliographic identity changed")
    ]
