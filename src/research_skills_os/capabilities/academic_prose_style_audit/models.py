"""Typed output for the prose-style audit."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class StyleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProseStyleFinding(StyleModel):
    code: str
    severity: Literal["advisory", "warning", "blocking"]
    unit: str
    excerpt: str
    message: str


class ProseStyleMetrics(StyleModel):
    character_count: int
    paragraph_count: int
    sentence_count: int
    formulaic_filler_count: int
    connector_count: int
    connectors_per_1000_characters: float
    sentence_length_stddev: float
    repeated_opening_count: int
    repeated_ngram_count: int


class ProseStyleReport(StyleModel):
    findings: tuple[ProseStyleFinding, ...]
    metrics: ProseStyleMetrics
    protected_anchors: tuple[str, ...]
    missing_anchors: tuple[str, ...]
    ok: bool
