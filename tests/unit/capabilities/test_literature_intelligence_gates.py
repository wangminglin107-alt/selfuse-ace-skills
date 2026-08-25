from copy import deepcopy

import pytest

from research_skills_os.capabilities.literature_intelligence.gates import (
    evaluate_literature_artifacts,
)
from research_skills_os.core.contracts.enums import GateStatus


@pytest.fixture
def valid_artifacts():
    ledger = {
        "schema_version": "1.0",
        "search_question": "How are creator exit narratives studied?",
        "searches": [
            {
                "search_id": "search-1",
                "query": "creator exit narratives platform burnout",
                "searched_at": "2026-08-25T12:00:00Z",
                "provider": "local-manual",
                "status": "executed",
                "result_count": 1,
            }
        ],
        "inclusion_criteria": ["Directly examines creator exit or withdrawal narratives."],
        "exclusion_criteria": ["Commentary without a traceable source artifact."],
        "coverage_limits": ["Only the user-supplied local corpus was inspected."],
        "blockers": [],
    }
    registry = {
        "schema_version": "1.0",
        "sources": [
            {
                "source_id": "source-1",
                "title": "Fixture study of creator withdrawal",
                "status": "verified_content",
                "decision": "include",
                "decision_reason": "Directly addresses the search question.",
                "provenance": {
                    "provider": "local-manual",
                    "locator": "fixtures/source-1.md",
                    "retrieved_at": "2026-08-25T12:00:00Z",
                    "content_sha256": "a" * 64,
                },
                "metadata_verification": "verified",
                "content_verification": "verified",
            }
        ],
    }
    evidence_map = {
        "schema_version": "1.0",
        "claims": [
            {
                "claim_id": "claim-1",
                "statement": "The fixture describes withdrawal as negotiated platform work.",
                "links": [
                    {
                        "source_id": "source-1",
                        "relation": "supports",
                        "evidence_note": "The source's findings section states this directly.",
                    }
                ],
            }
        ],
        "coverage_limits": ["No external database search was performed."],
        "unsupported_claims": [],
    }
    return ledger, registry, evidence_map


def results_by_id(artifacts):
    return {result.gate_id: result for result in evaluate_literature_artifacts(*artifacts)}


def test_complete_traceable_literature_artifacts_pass(valid_artifacts):
    results = evaluate_literature_artifacts(*valid_artifacts)

    assert results
    assert all(result.status is GateStatus.PASS for result in results)


@pytest.mark.parametrize("field", ["query", "searched_at", "provider"])
def test_search_ledger_requires_query_date_and_source(valid_artifacts, field):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    del ledger["searches"][0][field]

    result = results_by_id((ledger, registry, evidence_map))["literature.search_trace"]

    assert result.status is GateStatus.FAIL
    assert field in result.findings[0]


@pytest.mark.parametrize("field", ["inclusion_criteria", "exclusion_criteria", "coverage_limits"])
def test_search_boundaries_must_be_explicit(valid_artifacts, field):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    del ledger[field]

    result = results_by_id((ledger, registry, evidence_map))["literature.search_trace"]

    assert result.status is GateStatus.FAIL
    assert field in result.findings[0]


def test_every_screening_decision_requires_a_reason(valid_artifacts):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    registry["sources"][0]["decision_reason"] = ""

    result = results_by_id((ledger, registry, evidence_map))["literature.source_trace"]

    assert result.status is GateStatus.FAIL
    assert "decision_reason" in result.findings[0]


def test_source_provenance_and_content_hash_are_required(valid_artifacts):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    del registry["sources"][0]["provenance"]["content_sha256"]

    result = results_by_id((ledger, registry, evidence_map))["literature.source_trace"]

    assert result.status is GateStatus.FAIL
    assert "content_sha256" in result.findings[0]


def test_claim_links_must_resolve_to_registered_sources(valid_artifacts):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    evidence_map["claims"][0]["links"][0]["source_id"] = "missing-source"

    result = results_by_id((ledger, registry, evidence_map))["literature.claim_links"]

    assert result.status is GateStatus.FAIL
    assert "missing-source" in result.findings[0]


@pytest.mark.parametrize(
    ("status", "metadata", "content"),
    [
        ("verified_metadata", "verified", "verified"),
        ("verified_content", "unverified", "verified"),
        ("retrieved", "verified", "verified"),
    ],
)
def test_metadata_and_content_verification_cannot_be_collapsed(
    valid_artifacts, status, metadata, content
):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    source = registry["sources"][0]
    source["status"] = status
    source["metadata_verification"] = metadata
    source["content_verification"] = content

    result = results_by_id((ledger, registry, evidence_map))["literature.status_consistency"]

    assert result.status is GateStatus.FAIL


def test_closed_evidence_status_vocabulary_rejects_invented_status(valid_artifacts):
    ledger, registry, evidence_map = deepcopy(valid_artifacts)
    registry["sources"][0]["status"] = "probably_verified"

    result = results_by_id((ledger, registry, evidence_map))["literature.source_trace"]

    assert result.status is GateStatus.FAIL
