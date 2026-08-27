"""Pure identity normalization and synchronization planning."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from research_skills_os.integrations.zotero_obsidian.models import (
    SyncAction,
    SyncActionKind,
    SyncPlan,
    SyncSource,
    SyncSpec,
    SyncState,
)


def _normalize_doi(value: str) -> str:
    normalized = value.strip().casefold()
    normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", normalized)
    return normalized.strip()


def _canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, "", "")).rstrip("/")


def source_identity(source: SyncSource) -> str:
    if source.doi and (doi := _normalize_doi(source.doi)):
        return f"doi:{doi}"
    if source.url:
        return f"url:{_canonical_url(source.url)}"
    title = re.sub(r"\s+", " ", source.title).strip().casefold()
    return f"title-year:{title}|{source.year}"


def build_sync_plan(spec: SyncSpec, state: SyncState) -> SyncPlan:
    actions: list[SyncAction] = []
    for source in spec.sources:
        identity = source_identity(source)
        prior = state.records.get(source.source_id)
        if prior is None:
            kind = SyncActionKind.UPSERT
            reason = "source has no completed sync state"
        elif prior.identity != identity:
            kind = SyncActionKind.UPSERT
            reason = "bibliographic identity changed"
        elif source.attachment is not None and (
            prior.attachment_status != source.attachment.status
            or prior.attachment_sha256 != source.attachment.sha256
        ):
            kind = SyncActionKind.UPSERT
            reason = "attachment declaration changed"
        elif prior.content_sha256 != source.content_sha256:
            kind = SyncActionKind.REFRESH_NOTE
            reason = "content hash changed"
        else:
            kind = SyncActionKind.SKIP
            reason = "identity and content hash unchanged"
        actions.append(
            SyncAction(source_id=source.source_id, identity=identity, kind=kind, reason=reason)
        )
    return SyncPlan(project_id=spec.project_id, actions=tuple(actions))
