"""Strict claim-level evidence synthesis artifact models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_skills_os.capabilities.evidence_common import ContentLocator, EvidenceRole


class SynthesisModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceRow(SynthesisModel):
    schema_version: Literal["1.0"] = "1.0"
    row_id: str = Field(min_length=1)
    synthesis_group: str = Field(min_length=1)
    question_dimension: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_passage: str
    reviewed_translation: str | None
    passage_language: str = Field(min_length=1)
    locator: ContentLocator
    source_claim: str = Field(min_length=1)
    author_inference: str | None
    study_context: str = Field(min_length=1)
    method: str = Field(min_length=1)
    population: str = Field(min_length=1)
    boundary_conditions: list[str]
    evidence_role: EvidenceRole
    verification_status: Literal["verified_content", "manual_needed"]
    verifier_note: str = Field(min_length=1)
    downstream_claim_ids: list[str]


class SynthesisGroup(SynthesisModel):
    group_id: str = Field(min_length=1)
    row_ids: list[str] = Field(min_length=1)
    provisional_claim: str = Field(min_length=1)
    downstream_claim_ids: list[str]


class SynthesisMatrix(SynthesisModel):
    schema_version: Literal["1.0"] = "1.0"
    groups: list[SynthesisGroup]


class ContradictionEntry(SynthesisModel):
    contradiction_id: str = Field(min_length=1)
    synthesis_group: str = Field(min_length=1)
    row_ids: list[str] = Field(min_length=2)
    competing_claims: list[str] = Field(min_length=2)
    possible_scope_explanations: list[str]
    unresolved_issue: str = Field(min_length=1)
    material: bool
    resolution_state: Literal["open", "resolved", "accepted_limitation"]
    boundary_note: str | None


class ContradictionLedger(SynthesisModel):
    schema_version: Literal["1.0"] = "1.0"
    entries: list[ContradictionEntry]


class CoverageReport(SynthesisModel):
    schema_version: Literal["1.0"] = "1.0"
    source_ids: list[str]
    question_dimensions: list[str]
    downstream_claim_ids: list[str]
    uncovered_dimensions: list[str]
    coverage_limits: list[str] = Field(min_length=1)
