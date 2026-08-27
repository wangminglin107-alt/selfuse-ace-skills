"""Provider registration and request-level privacy policy enforcement."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from research_skills_os.core.contracts.models import ArtifactEnvelope, ExecutionRequest
from research_skills_os.core.errors import ResearchSkillsError
from research_skills_os.providers.protocol import (
    ProviderAdapter,
    ProviderRequest,
    ProviderResult,
)


class DuplicateProvider(ResearchSkillsError):
    """Two adapters declare the same provider identifier."""


class UnknownProvider(ResearchSkillsError):
    """A provider identifier is not registered."""


class ProviderPolicyViolation(ResearchSkillsError):
    """A provider call conflicts with declared or request-level policy."""


class ProviderArtifactNotRegistered(ResearchSkillsError):
    """A local provider was asked to read an unregistered artifact."""


class ProviderArtifactIntegrityError(ResearchSkillsError):
    """A registered provider input no longer matches its content hash."""


class ProviderArtifactReadError(ResearchSkillsError):
    """A registered artifact cannot be decoded by the V1 local provider."""


class ProviderRegistry:
    def __init__(self, providers: Iterable[ProviderAdapter] = ()) -> None:
        self._providers: dict[str, ProviderAdapter] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ProviderAdapter) -> None:
        provider_id = provider.declaration.provider_id
        if provider_id in self._providers:
            raise DuplicateProvider(f"provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> ProviderAdapter:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise UnknownProvider(f"unknown provider: {provider_id}") from exc

    def collect(
        self,
        provider_id: str,
        execution_request: ExecutionRequest,
        provider_request: ProviderRequest,
        *,
        registered_artifacts: Mapping[str, ArtifactEnvelope],
    ) -> ProviderResult:
        provider = self.get(provider_id)
        declaration = provider.declaration
        if declaration.network == "required" and execution_request.constraints.network == "deny":
            raise ProviderPolicyViolation(f"provider {provider_id} requires denied network access")

        result = provider.collect(provider_request, registered_artifacts)
        if result.provider_id != declaration.provider_id:
            raise ProviderPolicyViolation("provider result identifier differs from declaration")
        if result.provider_version != declaration.provider_version:
            raise ProviderPolicyViolation("provider result version differs from declaration")
        if result.network_used and declaration.network == "none":
            raise ProviderPolicyViolation("offline provider reported network use")
        undeclared_secrets = sorted(set(result.secrets_used) - set(declaration.required_secrets))
        if undeclared_secrets:
            raise ProviderPolicyViolation(
                f"provider used undeclared secrets: {', '.join(undeclared_secrets)}"
            )
        return result
