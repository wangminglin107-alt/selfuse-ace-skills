"""Default provider for content explicitly placed inside a research project."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from research_skills_os.core.artifacts.paths import resolve_project_path
from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.models import ArtifactEnvelope
from research_skills_os.providers.protocol import (
    ProviderDeclaration,
    ProviderRequest,
    ProviderResult,
    ProviderSource,
)
from research_skills_os.providers.registry import (
    ProviderArtifactIntegrityError,
    ProviderArtifactNotRegistered,
    ProviderArtifactReadError,
)


class LocalManualProvider:
    """Read hash-verified, registered UTF-8 artifacts without network or secrets."""

    declaration = ProviderDeclaration(
        provider_id="local-manual",
        provider_version="1.0",
        network="none",
        required_secrets=[],
        data_sent_off_machine=[],
        endpoints=[],
        timeout_seconds=30,
        max_retries=0,
        cache="none",
        response_schema="provider-result/1.0",
        provenance_fields=["artifact_id", "path", "sha256"],
        offline_behavior="supported",
    )

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.store = ArtifactStore(self.project_root)

    def collect(
        self,
        provider_request: ProviderRequest,
        registered_artifacts: Mapping[str, ArtifactEnvelope],
    ) -> ProviderResult:
        sources: list[ProviderSource] = []
        for artifact_id in provider_request.artifact_ids:
            envelope = registered_artifacts.get(artifact_id)
            if envelope is None or envelope.artifact_id != artifact_id:
                raise ProviderArtifactNotRegistered(f"artifact {artifact_id} is not registered")

            verification = self.store.verify(envelope)
            if verification.status != "verified":
                raise ProviderArtifactIntegrityError(
                    f"artifact {artifact_id} has hash drift and cannot be imported"
                )

            artifact_path = resolve_project_path(self.project_root, envelope.path)
            try:
                content = artifact_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ProviderArtifactReadError(
                    f"artifact {artifact_id} is not valid UTF-8 text"
                ) from exc
            sources.append(
                ProviderSource(
                    artifact_id=artifact_id,
                    path=envelope.path,
                    sha256=envelope.sha256,
                    content=content,
                )
            )

        return ProviderResult(
            provider_id=self.declaration.provider_id,
            provider_version=self.declaration.provider_version,
            sources=sources,
            network_used=False,
            secrets_used=[],
        )
