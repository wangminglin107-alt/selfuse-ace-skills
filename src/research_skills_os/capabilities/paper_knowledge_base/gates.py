"""Offline deterministic gates for declared paper-knowledge-base artifacts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from pydantic import ValidationError

from research_skills_os.capabilities.evidence_common import AccessState, IdentityState
from research_skills_os.capabilities.paper_knowledge_base.models import CorpusStatus, DocumentIndex
from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult


def _result(
    gate_id: str,
    status: GateStatus,
    findings: list[str] | None = None,
    remediation: list[str] | None = None,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=status,
        severity=GateSeverity.BLOCKING,
        findings=findings or [],
        remediation=remediation or [],
    )


def _validation_findings(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]


def _is_project_relative(path: str) -> bool:
    windows = PureWindowsPath(path)
    posix = PurePosixPath(path.replace("\\", "/"))
    return (
        not windows.drive
        and not windows.root
        and not posix.is_absolute()
        and ".." not in posix.parts
    )


def evaluate_paper_knowledge_base(
    document_index: Mapping[str, Any], corpus_status: Mapping[str, Any]
) -> list[GateResult]:
    """Validate declared corpus integrity without extraction or network access."""

    try:
        index = DocumentIndex.model_validate(document_index)
        status = CorpusStatus.model_validate(corpus_status)
    except ValidationError as exc:
        return [
            _result(
                "corpus.required",
                GateStatus.FAIL,
                _validation_findings(exc),
                ["Complete the document index and corpus-status contract."],
            ),
            _result("corpus.identity_integrity", GateStatus.NOT_APPLICABLE),
            _result("corpus.locators", GateStatus.NOT_APPLICABLE),
            _result("corpus.privacy_declared", GateStatus.NOT_APPLICABLE),
        ]

    required = _result("corpus.required", GateStatus.PASS)

    identity_findings: list[str] = []
    counts = Counter(document.source_id for document in index.documents)
    for source_id, count in counts.items():
        if count > 1:
            identity_findings.append(f"duplicate source_id: {source_id}")
    indexed_ids = set(counts)
    for document in index.documents:
        if not _is_project_relative(document.path):
            identity_findings.append(f"source {document.source_id} path must be project-relative.")
        recorded_hash = status.artifact_hashes.get(document.source_id)
        if recorded_hash != document.artifact_sha256:
            identity_findings.append(f"source {document.source_id} artifact hash mismatch.")
        if document.metadata_verification is not IdentityState.VERIFIED:
            identity_findings.append(
                f"source {document.source_id} metadata identity is "
                f"{document.metadata_verification.value}."
            )
        if document.version_state == "superseded" and not document.superseded_by_source_id:
            identity_findings.append(
                f"superseded source {document.source_id} requires a replacement source ID."
            )
        for related in (document.supersedes_source_id, document.superseded_by_source_id):
            if related is not None and related not in indexed_ids:
                identity_findings.append(
                    f"source {document.source_id} references unknown version source {related}."
                )
    for group in status.unresolved_duplicate_groups:
        identity_findings.append(f"unresolved duplicate group: {', '.join(group)}")
    identity = _result(
        "corpus.identity_integrity",
        GateStatus.FAIL if identity_findings else GateStatus.PASS,
        identity_findings,
        ["Resolve duplicate, version, path, identity, and artifact-hash conflicts."]
        if identity_findings
        else [],
    )

    locator_findings: list[str] = []
    for document in index.documents:
        if document.content_availability is not AccessState.FULL_TEXT:
            locator_findings.append(
                f"source {document.source_id} lacks available full text for content evidence."
            )
        if not document.locators:
            locator_findings.append(f"source {document.source_id} has no stable content locator.")
    locators = _result(
        "corpus.locators",
        GateStatus.FAIL if locator_findings else GateStatus.PASS,
        locator_findings,
        ["Attach exact page or stable-section locators to available source content."]
        if locator_findings
        else [],
    )

    privacy_findings: list[str] = []
    if not status.privacy_declared:
        privacy_findings.append("corpus privacy has not been declared.")
    for document in index.documents:
        if document.privacy_label is None:
            privacy_findings.append(f"source {document.source_id} lacks a privacy label.")
    privacy = _result(
        "corpus.privacy_declared",
        GateStatus.FAIL if privacy_findings else GateStatus.PASS,
        privacy_findings,
        ["Declare corpus and per-document privacy before provider or workflow use."]
        if privacy_findings
        else [],
    )
    return [required, identity, locators, privacy]
