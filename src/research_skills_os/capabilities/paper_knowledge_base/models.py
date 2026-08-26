"""Strict declared artifacts for the project-scoped paper knowledge base."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_skills_os.capabilities.evidence_common import (
    AccessState,
    ContentLocator,
    IdentityState,
    PrivacyLabel,
)


class KnowledgeBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def normalize_bibliographic_text(value: str | None) -> str:
    """Return stable plain text for title/author identity comparison.

    Adapted from Nature Skills' ``ris_escape`` at the commit recorded in
    ``SOURCE_MANIFEST.yaml``; provider and output-format assumptions are removed.
    """

    without_markup = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", without_markup).strip()


class DocumentRecord(KnowledgeBaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authors: list[str] = Field(min_length=1)
    identifiers: dict[str, str]
    artifact_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    imported_at: datetime
    document_type: Literal[
        "article", "book", "chapter", "thesis", "report", "dataset", "policy", "web", "other"
    ]
    language: str = Field(min_length=1)
    access_state: AccessState
    privacy_label: PrivacyLabel | None
    content_availability: AccessState
    locators: list[ContentLocator]
    extraction_method: str = Field(min_length=1)
    extraction_warnings: list[str]
    version_state: Literal["current", "superseded"]
    supersedes_source_id: str | None
    superseded_by_source_id: str | None
    metadata_verification: IdentityState

    @field_validator("imported_at")
    @classmethod
    def imported_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("imported_at must include timezone information")
        return value


class DocumentIndex(KnowledgeBaseModel):
    schema_version: Literal["1.0"] = "1.0"
    documents: list[DocumentRecord] = Field(min_length=1)


class CorpusStatus(KnowledgeBaseModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_hashes: dict[str, str]
    unresolved_duplicate_groups: list[list[str]]
    privacy_declared: bool
    coverage_limits: list[str] = Field(min_length=1)

    @field_validator("artifact_hashes")
    @classmethod
    def artifact_hashes_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        for source_id, digest in value.items():
            invalid_digest = len(digest) != 64 or any(
                char not in "0123456789abcdef" for char in digest
            )
            if not source_id or invalid_digest:
                raise ValueError("artifact_hashes must map source IDs to lowercase SHA-256 values")
        return value
