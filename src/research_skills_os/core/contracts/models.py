"""Canonical Pydantic models for V1 execution and persistence contracts."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from research_skills_os.core.contracts.enums import (
    GateSeverity,
    GateStatus,
    RunMode,
    RunStatus,
    TargetKind,
)

CONTRACT_VERSION: Literal["1.0"] = "1.0"
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone information")
    return value


def _validate_project_relative_path(value: str, *, allow_remote_uri: bool) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("path must not be empty")

    parsed = urlsplit(candidate)
    if parsed.scheme:
        if parsed.scheme.casefold() == "file":
            raise ValueError("file URIs are not project-relative paths")
        if allow_remote_uri and parsed.netloc:
            return candidate

    windows_path = PureWindowsPath(candidate)
    posix_path = PurePosixPath(candidate.replace("\\", "/"))
    if windows_path.drive or windows_path.root or posix_path.is_absolute():
        raise ValueError("path must be relative to the project root")
    if ".." in posix_path.parts:
        raise ValueError("path traversal is not allowed")
    if posix_path.as_posix() in {"", "."}:
        raise ValueError("path must identify a project artifact")
    return posix_path.as_posix()


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TargetRef(ContractModel):
    kind: TargetKind
    id: NonEmptyStr


class InputArtifactRef(ContractModel):
    artifact_id: NonEmptyStr
    type: NonEmptyStr
    path_or_uri: NonEmptyStr

    @field_validator("path_or_uri")
    @classmethod
    def validate_path_or_uri(cls, value: str) -> str:
        return _validate_project_relative_path(value, allow_remote_uri=True)


class RequestConstraints(ContractModel):
    language: Literal["zh", "en", "bilingual"] = "bilingual"
    domain: NonEmptyStr = "other"
    stop_after: NonEmptyStr | None = None
    network: Literal["deny", "allow_declared_providers"] = "deny"


class ExecutionRequest(ContractModel):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    request_id: NonEmptyStr
    project_id: NonEmptyStr
    target: TargetRef
    mode: RunMode
    goal: NonEmptyStr
    inputs: list[InputArtifactRef] = Field(default_factory=list)
    constraints: RequestConstraints = Field(default_factory=RequestConstraints)
    prior_checkpoint: NonEmptyStr | None = None
    user_decisions: dict[str, JsonValue] = Field(default_factory=dict)


class ArtifactEnvelope(ContractModel):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    artifact_id: NonEmptyStr
    type: NonEmptyStr
    schema_version: NonEmptyStr
    producing_capability: NonEmptyStr
    created_at: datetime
    path: NonEmptyStr
    sha256: Sha256
    source_artifact_ids: list[NonEmptyStr] = Field(default_factory=list)
    provenance_references: list[NonEmptyStr] = Field(default_factory=list)
    sensitivity: Literal["public", "internal", "sensitive"] = "internal"
    human_edited: bool = False
    verification_state: Literal["unverified", "verified", "drifted"] = "unverified"

    _created_at_is_aware = field_validator("created_at")(_ensure_aware)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_project_relative_path(value, allow_remote_uri=False)


class GateResult(ContractModel):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    gate_id: NonEmptyStr
    gate_version: NonEmptyStr
    status: GateStatus
    severity: GateSeverity
    findings: list[NonEmptyStr] = Field(default_factory=list)
    evidence: list[NonEmptyStr] = Field(default_factory=list)
    remediation: list[NonEmptyStr] = Field(default_factory=list)


class EvidenceRecord(ContractModel):
    evidence_id: NonEmptyStr
    description: NonEmptyStr
    source_artifact_ids: list[NonEmptyStr] = Field(default_factory=list)
    verification_state: Literal["candidate", "verified_metadata", "verified_content"] = "candidate"


class DecisionRecord(ContractModel):
    decision_id: NonEmptyStr
    description: NonEmptyStr
    rationale: NonEmptyStr | None = None
    made_by: Literal["user", "system"]


class UncertaintyRecord(ContractModel):
    uncertainty_id: NonEmptyStr
    description: NonEmptyStr
    material: bool = True


class NextAction(ContractModel):
    target_id: NonEmptyStr | None = None
    reason: NonEmptyStr


class ExecutionResult(ContractModel):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    request_id: NonEmptyStr
    run_id: NonEmptyStr
    target_id: NonEmptyStr
    status: RunStatus
    artifacts: list[ArtifactEnvelope] = Field(default_factory=list)
    evidence_added: list[EvidenceRecord] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    uncertainties: list[UncertaintyRecord] = Field(default_factory=list)
    gate_results: list[GateResult] = Field(default_factory=list)
    failed_gates: list[NonEmptyStr] = Field(default_factory=list)
    next_action: NextAction | None = None
    resume_token: NonEmptyStr | None = None

    @model_validator(mode="after")
    def completed_has_no_blocking_failures(self) -> ExecutionResult:
        if self.status is not RunStatus.COMPLETED:
            return self
        if self.failed_gates:
            raise ValueError("completed result cannot contain failed_gates")
        if any(
            result.status is GateStatus.FAIL and result.severity is GateSeverity.BLOCKING
            for result in self.gate_results
        ):
            raise ValueError("completed result cannot contain a blocking gate failure")
        return self


class Checkpoint(ContractModel):
    checkpoint_version: Literal["1.0"] = CONTRACT_VERSION
    checkpoint_id: NonEmptyStr
    project_id: NonEmptyStr
    run_id: NonEmptyStr
    completed_target: NonEmptyStr
    inputs_used: list[NonEmptyStr] = Field(default_factory=list)
    artifacts_created: list[ArtifactEnvelope] = Field(default_factory=list)
    key_decisions: list[DecisionRecord] = Field(default_factory=list)
    evidence_added: list[EvidenceRecord] = Field(default_factory=list)
    uncertainties: list[UncertaintyRecord] = Field(default_factory=list)
    failed_gates: list[NonEmptyStr] = Field(default_factory=list)
    recommended_next: NonEmptyStr | None = None
    resume_from: NonEmptyStr
    state_hash: Sha256
    created_at: datetime

    _created_at_is_aware = field_validator("created_at")(_ensure_aware)


def is_sha256(value: str) -> bool:
    """Return whether a string is a canonical lowercase SHA-256 digest."""

    return re.fullmatch(r"[0-9a-f]{64}", value) is not None
