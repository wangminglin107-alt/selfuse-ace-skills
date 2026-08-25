"""Stable provider declarations and result contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_skills_os.core.contracts.models import ArtifactEnvelope


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProviderDeclaration(ProviderModel):
    """Auditable side-effect declaration checked before an adapter is called."""

    provider_id: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)
    network: Literal["none", "required"]
    required_secrets: list[str] = Field(default_factory=list)
    data_sent_off_machine: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(ge=1)
    max_retries: int = Field(ge=0)
    cache: Literal["none", "project"]
    response_schema: str = Field(min_length=1)
    provenance_fields: list[str] = Field(min_length=1)
    offline_behavior: Literal["supported", "blocked"]

    @model_validator(mode="after")
    def offline_declaration_has_no_remote_side_effects(self) -> ProviderDeclaration:
        if self.network == "none" and (
            self.required_secrets or self.data_sent_off_machine or self.endpoints
        ):
            raise ValueError("offline providers cannot declare remote side effects")
        if self.network == "required" and not self.endpoints:
            raise ValueError("network providers must declare at least one endpoint")
        return self


class ProviderRequest(ProviderModel):
    artifact_ids: list[str] = Field(default_factory=list)
    query: str | None = None


class ProviderSource(ProviderModel):
    """Imported content remains a candidate until a downstream gate verifies it."""

    artifact_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content: str
    verification_state: Literal["candidate"] = "candidate"


class ProviderResult(ProviderModel):
    provider_id: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)
    sources: list[ProviderSource] = Field(default_factory=list)
    network_used: bool = False
    secrets_used: list[str] = Field(default_factory=list)


class ProviderAdapter(Protocol):
    declaration: ProviderDeclaration

    def collect(
        self,
        provider_request: ProviderRequest,
        registered_artifacts: Mapping[str, ArtifactEnvelope],
    ) -> ProviderResult: ...
