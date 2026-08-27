"""Strict contracts for idempotent Zotero and Obsidian synchronization."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _validate_relative_path(value: str) -> str:
    path = PurePath(value.replace("\\", "/"))
    if path.is_absolute() or path.root or not path.parts or ".." in path.parts:
        raise ValueError("path must be a contained relative path")
    return path.as_posix()


class SyncModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AttachmentStatus(StrEnum):
    LOCAL_FILE = "local_file"
    METADATA_ONLY = "metadata_only"


class MirrorPolicy(StrEnum):
    LINK_ONLY = "link_only"
    COPY_CORE = "copy_core"


class AttachmentSpec(SyncModel):
    status: AttachmentStatus
    path: str | None = None
    sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    source_url: str | None = None
    media_type: Literal["application/pdf"] = "application/pdf"
    mirror_policy: MirrorPolicy = MirrorPolicy.LINK_ONLY

    @field_validator("path")
    @classmethod
    def attachment_path_is_relative(cls, value: str | None) -> str | None:
        return _validate_relative_path(value) if value is not None else None

    @model_validator(mode="after")
    def status_matches_file_fields(self) -> AttachmentSpec:
        if self.status is AttachmentStatus.LOCAL_FILE:
            if self.path is None or self.sha256 is None:
                raise ValueError("local_file attachment requires path and sha256")
        elif self.path is not None or self.sha256 is not None:
            raise ValueError("metadata_only attachment cannot declare path or sha256")
        if (
            self.mirror_policy is MirrorPolicy.COPY_CORE
            and self.status is not AttachmentStatus.LOCAL_FILE
        ):
            raise ValueError("copy_core requires a local_file attachment")
        return self


class SyncSource(SyncModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    year: int = Field(ge=1000, le=9999)
    item_type: str = Field(min_length=1)
    authors: tuple[str, ...] = ()
    doi: str | None = None
    url: str | None = None
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    note_source: str = Field(min_length=1)
    inspected_content: bool
    attachment: AttachmentSpec | None = None

    @field_validator("note_source")
    @classmethod
    def note_source_is_relative(cls, value: str) -> str:
        return _validate_relative_path(value)


class SyncSpec(SyncModel):
    version: Literal[1]
    project_id: str = Field(min_length=1)
    zotero_collection: str = Field(min_length=1)
    obsidian_project: str = Field(min_length=1)
    sources: tuple[SyncSource, ...] = Field(min_length=1)

    @field_validator("obsidian_project")
    @classmethod
    def obsidian_project_is_relative(cls, value: str) -> str:
        return _validate_relative_path(value)

    @model_validator(mode="after")
    def identities_are_unique(self) -> SyncSpec:
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_id collision")
        identities = [source_identity(source) for source in self.sources]
        if len(identities) != len(set(identities)):
            raise ValueError("bibliographic identity collision")
        return self


class SyncStateRecord(SyncModel):
    identity: str = Field(min_length=1)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    zotero_item_key: str = Field(min_length=1)
    obsidian_note: str = Field(min_length=1)
    attachment_status: AttachmentStatus | None = None
    attachment_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    zotero_attachment_key: str | None = None

    @field_validator("obsidian_note")
    @classmethod
    def obsidian_note_is_relative(cls, value: str) -> str:
        return _validate_relative_path(value)


class SyncState(SyncModel):
    version: Literal[1] = 1
    records: dict[str, SyncStateRecord] = Field(default_factory=dict)


class SyncActionKind(StrEnum):
    UPSERT = "upsert"
    REFRESH_NOTE = "refresh_note"
    SKIP = "skip"


class SyncAction(SyncModel):
    source_id: str
    identity: str
    kind: SyncActionKind
    reason: str


class SyncPlan(SyncModel):
    project_id: str
    actions: tuple[SyncAction, ...]


def source_identity(source: SyncSource) -> str:
    """Return the stable bibliographic identity in declared priority order."""

    from research_skills_os.integrations.zotero_obsidian.planner import source_identity as identity

    return identity(source)
