"""Evidence-bounded construct, theory-candidate, and human decision models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Level = Literal[
    "individual",
    "account",
    "group",
    "organization",
    "platform",
    "institution",
    "society",
    "multilevel",
]
Recommendation = Literal[
    "single_theory", "bounded_integration", "mechanism_framework", "descriptive"
]


class TheoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TheoryCandidate(TheoryModel):
    candidate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    theories: list[str]
    construct_ids: list[str] = Field(min_length=1)
    mechanisms: list[str]
    level_of_analysis: Level
    evidence_row_ids: list[str]
    acknowledged_contradiction_ids: list[str]
    assumptions: list[str]
    compatibility_rationale: str | None
    limitations: list[str] = Field(min_length=1)


class TheoryCandidates(TheoryModel):
    schema_version: Literal["1.0"] = "1.0"
    candidates: list[TheoryCandidate]


class Construct(TheoryModel):
    construct_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    level_of_analysis: Level
    evidence_row_ids: list[str]


class ConstructRelation(TheoryModel):
    from_construct_id: str = Field(min_length=1)
    to_construct_id: str = Field(min_length=1)
    mechanism: str = Field(min_length=1)
    evidence_row_ids: list[str]
    cross_level_rationale: str | None


class ConstructMap(TheoryModel):
    schema_version: Literal["1.0"] = "1.0"
    known_evidence_row_ids: list[str]
    material_contradiction_ids: list[str]
    constructs: list[Construct] = Field(min_length=1)
    relations: list[ConstructRelation]


class TheoryDecisionPacket(TheoryModel):
    schema_version: Literal["1.0"] = "1.0"
    recommendation: Recommendation
    selected_candidate_id: str | None
    authorization_state: Literal["proposed", "selected"]
    user_decision_id: str | None
    rationale: str = Field(min_length=1)
    acknowledged_contradiction_ids: list[str]
