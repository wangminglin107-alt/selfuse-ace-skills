"""Strict SOURCE_MANIFEST validation with license and security acceptance gates."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ManifestValidationError(ValueError):
    """The source manifest is structurally invalid or fails an acceptance rule."""


class ManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LicenseDeclaration(ManifestModel):
    spdx: str = Field(min_length=1)
    source: str = Field(min_length=1)
    status: Literal["confirmed", "uncertain"]
    notice_required: bool


class SecurityDeclaration(ManifestModel):
    network: Literal["none", "optional", "required"]
    endpoints: list[str] = Field(default_factory=list)
    network_notes: str = Field(min_length=1)
    secrets: list[str] = Field(default_factory=list)
    subprocess: bool
    filesystem_scope: str = Field(min_length=1)
    review_status: Literal["approved", "pending", "blocked"]

    @model_validator(mode="after")
    def require_network_declarations(self) -> SecurityDeclaration:
        if self.network != "none" and not self.endpoints:
            raise ValueError("networked source requires endpoints and security notes")
        return self


class TestDeclaration(ManifestModel):
    upstream: list[str] = Field(default_factory=list)
    local: list[str] = Field(default_factory=list)


class SourceDeclaration(ManifestModel):
    capability: str = Field(min_length=1)
    source_kind: Literal["git", "local"]
    upstream_repo: str = Field(min_length=1)
    upstream_commit: str | None
    source_file: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reuse_mode: Literal["conceptual", "reference_only", "verbatim", "extracted", "adapted"]
    local_target: str | None = None
    modifications: list[str] = Field(default_factory=list)
    license: LicenseDeclaration
    security: SecurityDeclaration
    tests: TestDeclaration
    notes: str | None = None

    @model_validator(mode="after")
    def enforce_acceptance_rules(self) -> SourceDeclaration:
        if self.source_kind == "git":
            if self.upstream_commit is None or len(self.upstream_commit) != 40:
                raise ValueError("git source requires a full 40-character upstream commit")
            if any(character not in "0123456789abcdef" for character in self.upstream_commit):
                raise ValueError("git source commit must be lowercase hexadecimal")
        elif self.upstream_commit is not None:
            raise ValueError("local source must use a content hash instead of an upstream commit")
        if self.license.status != "confirmed":
            raise ValueError("license is uncertain; source acceptance is blocked")
        if self.security.review_status != "approved":
            raise ValueError("security review is not approved; source acceptance is blocked")
        if self.reuse_mode in {"verbatim", "extracted", "adapted"} and not self.local_target:
            raise ValueError(f"{self.reuse_mode} source requires a local target")
        if self.reuse_mode == "adapted":
            if not self.modifications:
                raise ValueError("adapted source requires a modification record")
            if not self.tests.local:
                raise ValueError("adapted source requires at least one local test")
        return self


class SourceManifest(ManifestModel):
    manifest_version: Literal["1.0"]
    sources: list[SourceDeclaration] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_records(self) -> SourceManifest:
        identities = [
            (source.upstream_repo, source.upstream_commit, source.source_file, source.local_target)
            for source in self.sources
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("source manifest contains duplicate records")
        return self


def load_manifest(path: str | Path) -> SourceManifest:
    manifest_path = Path(path)
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        return SourceManifest.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ManifestValidationError(str(exc)) from exc
