from collections.abc import Mapping
from pathlib import Path

import pytest

from research_skills_os.core.contracts.enums import RunMode, TargetKind
from research_skills_os.core.contracts.models import ArtifactEnvelope, ExecutionRequest, TargetRef
from research_skills_os.providers.protocol import (
    ProviderDeclaration,
    ProviderRequest,
    ProviderResult,
)
from research_skills_os.providers.registry import (
    DuplicateProvider,
    ProviderPolicyViolation,
    ProviderRegistry,
    UnknownProvider,
)


class FakeNetworkProvider:
    declaration = ProviderDeclaration(
        provider_id="fixture-network",
        provider_version="1.0",
        network="required",
        required_secrets=["FIXTURE_TOKEN"],
        data_sent_off_machine=["query"],
        endpoints=["https://fixture.invalid/search"],
        timeout_seconds=5,
        max_retries=0,
        cache="none",
        response_schema="provider-result/1.0",
        provenance_fields=["provider_id", "retrieved_at"],
        offline_behavior="blocked",
    )

    def __init__(self) -> None:
        self.called = False

    def collect(
        self,
        provider_request: ProviderRequest,
        registered_artifacts: Mapping[str, ArtifactEnvelope],
    ) -> ProviderResult:
        del provider_request, registered_artifacts
        self.called = True
        return ProviderResult(
            provider_id=self.declaration.provider_id,
            provider_version=self.declaration.provider_version,
            network_used=True,
            secrets_used=["FIXTURE_TOKEN"],
        )


def execution_request(*, network: str) -> ExecutionRequest:
    return ExecutionRequest(
        request_id="request-1",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="literature-intelligence"),
        mode=RunMode.INTERACTIVE,
        goal="Collect literature",
        constraints={"network": network},
    )


def test_denied_network_blocks_registered_provider_before_it_is_called(tmp_path: Path):
    provider = FakeNetworkProvider()
    registry = ProviderRegistry()
    registry.register(provider)

    with pytest.raises(ProviderPolicyViolation, match="denied network"):
        registry.collect(
            "fixture-network",
            execution_request(network="deny"),
            ProviderRequest(),
            registered_artifacts={},
        )

    assert provider.called is False


def test_explicit_network_authorization_allows_a_declared_provider():
    provider = FakeNetworkProvider()
    registry = ProviderRegistry([provider])

    result = registry.collect(
        "fixture-network",
        execution_request(network="allow_declared_providers"),
        ProviderRequest(),
        registered_artifacts={},
    )

    assert provider.called is True
    assert result.provider_id == "fixture-network"
    assert result.network_used is True


def test_duplicate_and_unknown_providers_are_rejected():
    provider = FakeNetworkProvider()
    registry = ProviderRegistry([provider])

    with pytest.raises(DuplicateProvider):
        registry.register(FakeNetworkProvider())
    with pytest.raises(UnknownProvider):
        registry.get("missing")
