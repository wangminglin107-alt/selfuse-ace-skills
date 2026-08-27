"""Offline citation gates that never confuse metadata identity with content support."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from research_skills_os.capabilities.citation_verification.models import (
    CitationBlockers,
    CitationIdentityAudit,
    CitationSupportAudit,
)
from research_skills_os.capabilities.evidence_common import (
    IdentityState,
    SupportState,
    VerificationRoute,
)
from research_skills_os.capabilities.paper_knowledge_base.models import (
    normalize_bibliographic_text,
)
from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult


def _result(
    gate_id: str, findings: list[str] | None = None, *, status: GateStatus | None = None
) -> GateResult:
    issues = findings or []
    return GateResult(
        gate_id=gate_id,
        gate_version="1.0",
        status=status or (GateStatus.FAIL if issues else GateStatus.PASS),
        severity=GateSeverity.BLOCKING,
        findings=issues,
        remediation=["Resolve or explicitly block the citation audit discrepancy."]
        if issues
        else [],
    )


def _validation_findings(exc: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]


def _normal_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized


def evaluate_citation_verification(
    identity: Mapping[str, Any],
    support: Mapping[str, Any],
    blockers: Mapping[str, Any],
) -> list[GateResult]:
    """Evaluate identity and support as independent, traceable states."""

    try:
        identity_audit = CitationIdentityAudit.model_validate(identity)
        support_audit = CitationSupportAudit.model_validate(support)
        blocker_audit = CitationBlockers.model_validate(blockers)
    except ValidationError as exc:
        return [
            _result("citation.required", _validation_findings(exc)),
            _result("citation.identity", status=GateStatus.NOT_APPLICABLE),
            _result("citation.content_support", status=GateStatus.NOT_APPLICABLE),
            _result("citation.route_trace", status=GateStatus.NOT_APPLICABLE),
            _result("citation.blockers_visible", status=GateStatus.NOT_APPLICABLE),
        ]

    required = _result("citation.required")
    identity_findings: list[str] = []
    invalid_citation_ids: set[str] = set()
    for identity_record in identity_audit.records:
        title_matches = normalize_bibliographic_text(identity_record.claimed_title).casefold() == (
            normalize_bibliographic_text(identity_record.verified_title).casefold()
        )
        authors_match = {
            normalize_bibliographic_text(author).casefold()
            for author in identity_record.claimed_authors
        } == {
            normalize_bibliographic_text(author).casefold()
            for author in identity_record.verified_authors
        }
        identifier_matches = _normal_identifier(
            identity_record.claimed_identifier
        ) == _normal_identifier(identity_record.verified_identifier)
        core_matches = (
            title_matches
            and authors_match
            and identifier_matches
            and identity_record.claimed_year == identity_record.verified_year
        )
        if identity_record.identity_state is not IdentityState.VERIFIED or not core_matches:
            identity_findings.append(
                f"citation {identity_record.citation_id} identity is not verified."
            )
            invalid_citation_ids.add(identity_record.citation_id)
        if identity_record.publication_status in {
            "retracted",
            "expression_of_concern",
            "manual_needed",
        }:
            identity_findings.append(
                f"citation {identity_record.citation_id} publication status is "
                f"{identity_record.publication_status}."
            )
            invalid_citation_ids.add(identity_record.citation_id)
    identity_result = _result("citation.identity", identity_findings)

    support_findings: list[str] = []
    if support_audit.content_claims_requested:
        if not support_audit.records:
            support_findings.append("content claims were requested but no support audit exists.")
        strength = {"background": 0, "descriptive": 1, "associational": 2, "causal": 3}
        for support_record in support_audit.records:
            if support_record.support_state is not SupportState.SUPPORTS:
                support_findings.append(
                    f"citation {support_record.citation_id} content state is "
                    f"{support_record.support_state.value}."
                )
                invalid_citation_ids.add(support_record.citation_id)
            if strength[support_record.claim_strength] > strength[support_record.passage_strength]:
                support_findings.append(
                    f"citation {support_record.citation_id} passage is weaker than the "
                    "downstream claim."
                )
                invalid_citation_ids.add(support_record.citation_id)
            if support_record.locator.content_sha256 != support_record.evidence_content_sha256:
                support_findings.append(
                    f"citation {support_record.citation_id} evidence locator hash mismatch."
                )
                invalid_citation_ids.add(support_record.citation_id)
        support_result = _result("citation.content_support", support_findings)
    else:
        support_result = _result("citation.content_support", status=GateStatus.NOT_APPLICABLE)

    route_findings: list[str] = []
    for route_record in identity_audit.records:
        if not route_record.official_record_locator:
            route_findings.append(
                f"citation {route_record.citation_id} lacks an official record locator."
            )
        if route_record.route is VerificationRoute.DOI and not route_record.verified_identifier:
            route_findings.append(f"citation {route_record.citation_id} DOI route lacks a DOI.")
        non_doi_route = route_record.route in {
            VerificationRoute.OFFICIAL_SOURCE,
            VerificationRoute.TITLE_AUTHOR,
        }
        missing_fields = not (
            route_record.verified_title
            and route_record.verified_authors
            and route_record.verified_container
            and route_record.verified_year
        )
        if non_doi_route and missing_fields:
            route_findings.append(
                f"citation {route_record.citation_id} non-DOI route lacks identity fields."
            )
    route_result = _result("citation.route_trace", route_findings)

    open_blocker_ids = {
        blocker.citation_id
        for blocker in blocker_audit.blockers
        if blocker.resolution_state == "open"
    }
    missing_blockers = sorted(invalid_citation_ids - open_blocker_ids)
    blocker_findings = [
        f"citation {citation_id} has an unresolved audit state without a visible blocker."
        for citation_id in missing_blockers
    ]
    blocker_result = _result("citation.blockers_visible", blocker_findings)
    return [required, identity_result, support_result, route_result, blocker_result]
