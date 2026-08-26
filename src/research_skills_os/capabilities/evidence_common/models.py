"""Shared, closed evidence vocabularies and content locators."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceRole(StrEnum):
    SUPPORTS = "supports"
    QUALIFIES = "qualifies"
    CONTRADICTS = "contradicts"
    NULL = "null"
    BACKGROUND = "background"


class IdentityState(StrEnum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"
    SUSPICIOUS = "suspicious"
    MANUAL_NEEDED = "manual_needed"


class SupportState(StrEnum):
    SUPPORTS = "supports"
    PARTIAL = "partial"
    MISALIGNED = "misaligned"
    CONTRADICTED = "contradicted"
    UNAVAILABLE = "unavailable"
    MANUAL_NEEDED = "manual_needed"


class AccessState(StrEnum):
    FULL_TEXT = "full_text"
    ABSTRACT_ONLY = "abstract_only"
    METADATA_ONLY = "metadata_only"
    UNAVAILABLE = "unavailable"


class PrivacyLabel(StrEnum):
    PUBLIC = "public"
    PROJECT_PRIVATE = "project_private"
    RESTRICTED = "restricted"


class VerificationRoute(StrEnum):
    DOI = "doi"
    TITLE_AUTHOR = "title_author"
    ISBN = "isbn"
    OFFICIAL_SOURCE = "official_source"
    MANUAL = "manual"


class ContentLocator(BaseModel):
    """Stable machine and human locator for an exact source passage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, min_length=1)
    block_id: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_human_locator(self) -> ContentLocator:
        if self.page is None and self.section is None:
            raise ValueError("page or section locator is required")
        return self
