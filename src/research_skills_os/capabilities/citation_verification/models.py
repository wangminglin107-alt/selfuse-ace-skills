"""Separate citation identity, content-support, route, and blocker artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_skills_os.capabilities.evidence_common import (
    ContentLocator,
    IdentityState,
    SupportState,
    VerificationRoute,
)


class CitationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CitationIdentityRecord(CitationModel):
    citation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_type: Literal[
        "article", "book", "chapter", "thesis", "report", "policy", "dataset", "web", "other"
    ]
    claimed_title: str = Field(min_length=1)
    claimed_authors: list[str] = Field(min_length=1)
    claimed_container: str = Field(min_length=1)
    claimed_year: int = Field(ge=1000, le=9999)
    claimed_identifier: str | None
    verified_title: str = Field(min_length=1)
    verified_authors: list[str] = Field(min_length=1)
    verified_container: str = Field(min_length=1)
    verified_year: int = Field(ge=1000, le=9999)
    verified_identifier: str | None
    route: VerificationRoute
    official_record_locator: str | None
    identity_state: IdentityState
    publication_status: Literal[
        "current", "corrected", "retracted", "expression_of_concern", "manual_needed"
    ]
    status_note: str = Field(min_length=1)


class CitationIdentityAudit(CitationModel):
    schema_version: Literal["1.0"] = "1.0"
    records: list[CitationIdentityRecord] = Field(min_length=1)


ClaimStrength = Literal["background", "descriptive", "associational", "causal"]


class CitationSupportRecord(CitationModel):
    support_id: str = Field(min_length=1)
    citation_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    evidence_row_id: str = Field(min_length=1)
    evidence_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    locator: ContentLocator
    support_state: SupportState
    claim_strength: ClaimStrength
    passage_strength: ClaimStrength
    verifier_note: str = Field(min_length=1)


class CitationSupportAudit(CitationModel):
    schema_version: Literal["1.0"] = "1.0"
    content_claims_requested: bool
    records: list[CitationSupportRecord]


class CitationBlocker(CitationModel):
    blocker_id: str = Field(min_length=1)
    citation_id: str = Field(min_length=1)
    kind: Literal["identity_or_support", "route", "publication_status"]
    description: str = Field(min_length=1)
    resolution_state: Literal["open", "resolved"]


class CitationBlockers(CitationModel):
    schema_version: Literal["1.0"] = "1.0"
    blockers: list[CitationBlocker]
