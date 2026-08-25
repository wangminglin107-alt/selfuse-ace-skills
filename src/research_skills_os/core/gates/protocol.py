"""Small protocol shared by deterministic gate implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from research_skills_os.core.artifacts.store import ArtifactVerification
from research_skills_os.core.checkpoint.service import (
    ResumeArtifactStatus,
    ResumeVerification,
)
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    GateResult,
)


@dataclass(frozen=True)
class ProviderUse:
    provider_id: str
    network: bool
    declared: bool


@dataclass(frozen=True)
class GateContext:
    request: ExecutionRequest | None = None
    result: ExecutionResult | None = None
    required_input_types: frozenset[str] = frozenset()
    artifact_verifications: tuple[ArtifactVerification | ResumeArtifactStatus, ...] = ()
    resume_verification: ResumeVerification | None = None
    material_uncertainty_detected: bool = False
    provider_uses: tuple[ProviderUse, ...] = ()


class Gate(Protocol):
    gate_id: str
    gate_version: str

    def evaluate(self, context: GateContext) -> GateResult: ...
