from copy import deepcopy

import pytest

from research_skills_os.capabilities.citation_verification.gates import (
    evaluate_citation_verification,
)
from research_skills_os.core.contracts.enums import GateStatus


@pytest.fixture
def valid_identity():
    return {
        "schema_version": "1.0",
        "records": [
            {
                "citation_id": "citation-1",
                "source_id": "source-1",
                "source_type": "article",
                "claimed_title": "A Study of Platform Withdrawal",
                "claimed_authors": ["Li, Ming"],
                "claimed_container": "Journal of Communication",
                "claimed_year": 2024,
                "claimed_identifier": "10.1000/example",
                "verified_title": "A Study of Platform Withdrawal",
                "verified_authors": ["Li, Ming"],
                "verified_container": "Journal of Communication",
                "verified_year": 2024,
                "verified_identifier": "10.1000/example",
                "route": "doi",
                "official_record_locator": "https://doi.org/10.1000/example",
                "identity_state": "verified",
                "publication_status": "current",
                "status_note": "No correction or retraction was found in the declared record.",
            }
        ],
    }


def valid_support(
    state="supports", claim_strength="associational", passage_strength="associational"
):
    return {
        "schema_version": "1.0",
        "content_claims_requested": True,
        "records": [
            {
                "support_id": "support-1",
                "citation_id": "citation-1",
                "claim_id": "claim-1",
                "claim_text": "The variables are associated.",
                "evidence_row_id": "row-1",
                "evidence_content_sha256": "b" * 64,
                "locator": {
                    "page": 7,
                    "block_id": "p7-b2",
                    "content_sha256": "b" * 64,
                },
                "support_state": state,
                "claim_strength": claim_strength,
                "passage_strength": passage_strength,
                "verifier_note": "The exact passage was inspected.",
            }
        ],
    }


def empty_blockers():
    return {"schema_version": "1.0", "blockers": []}


def blockers_for(citation_id="citation-1"):
    return {
        "schema_version": "1.0",
        "blockers": [
            {
                "blocker_id": "blocker-1",
                "citation_id": citation_id,
                "kind": "identity_or_support",
                "description": "Manual verification is required.",
                "resolution_state": "open",
            }
        ],
    }


def by_id(identity, support=None, blockers=None):
    return {
        result.gate_id: result
        for result in evaluate_citation_verification(
            identity,
            support or valid_support(),
            blockers or empty_blockers(),
        )
    }


def test_valid_citation_audits_pass_in_stable_order(valid_identity):
    results = evaluate_citation_verification(valid_identity, valid_support(), empty_blockers())

    assert [result.gate_id for result in results] == [
        "citation.required",
        "citation.identity",
        "citation.content_support",
        "citation.route_trace",
        "citation.blockers_visible",
    ]
    assert all(result.status is GateStatus.PASS for result in results)


@pytest.mark.parametrize(
    ("field", "value"),
    [("verified_identifier", "10.1000/different"), ("verified_authors", ["Wang, Lin"])],
)
def test_identity_mismatches_fail_even_if_marked_verified(valid_identity, field, value):
    identity = deepcopy(valid_identity)
    identity["records"][0][field] = value

    result = by_id(identity, blockers=blockers_for())["citation.identity"]

    assert result.status is GateStatus.FAIL


@pytest.mark.parametrize("publication_status", ["retracted", "expression_of_concern"])
def test_adverse_publication_status_is_visible_and_blocking(valid_identity, publication_status):
    identity = deepcopy(valid_identity)
    identity["records"][0]["publication_status"] = publication_status

    result = by_id(identity, blockers=blockers_for())["citation.identity"]

    assert result.status is GateStatus.FAIL


def test_correction_is_visible_but_can_remain_verified(valid_identity):
    identity = deepcopy(valid_identity)
    identity["records"][0]["publication_status"] = "corrected"
    identity["records"][0]["status_note"] = "Correction inspected; cited claim is unchanged."

    result = by_id(identity)["citation.identity"]

    assert result.status is GateStatus.PASS


def test_manual_needed_identity_blocks_and_requires_visible_blocker(valid_identity):
    identity = deepcopy(valid_identity)
    identity["records"][0]["identity_state"] = "manual_needed"

    results = by_id(identity)

    assert results["citation.identity"].status is GateStatus.FAIL
    assert results["citation.blockers_visible"].status is GateStatus.FAIL


def test_missing_doi_does_not_fail_source_type_without_doi(valid_identity):
    identity = deepcopy(valid_identity)
    record = identity["records"][0]
    record["claimed_identifier"] = None
    record["verified_identifier"] = None
    record["route"] = "official_source"
    record["official_record_locator"] = "https://official.example.cn/article/123"

    results = by_id(identity)

    assert results["citation.identity"].status is GateStatus.PASS
    assert results["citation.route_trace"].status is GateStatus.PASS


def test_verified_identity_does_not_make_unavailable_content_support_pass(valid_identity):
    results = by_id(
        valid_identity,
        support=valid_support(state="unavailable"),
        blockers=blockers_for(),
    )

    assert results["citation.identity"].status is GateStatus.PASS
    assert results["citation.content_support"].status is GateStatus.FAIL


def test_partial_passage_cannot_support_stronger_causal_claim(valid_identity):
    support = valid_support(
        state="partial", claim_strength="causal", passage_strength="associational"
    )

    result = by_id(valid_identity, support=support, blockers=blockers_for())[
        "citation.content_support"
    ]

    assert result.status is GateStatus.FAIL


def test_support_record_requires_exact_evidence_locator_hash(valid_identity):
    support = valid_support()
    support["records"][0]["locator"]["content_sha256"] = "c" * 64

    result = by_id(valid_identity, support=support)["citation.content_support"]

    assert result.status is GateStatus.FAIL


def test_metadata_only_audit_has_not_applicable_content_gate(valid_identity):
    support = {"schema_version": "1.0", "content_claims_requested": False, "records": []}

    result = by_id(valid_identity, support=support)["citation.content_support"]

    assert result.status is GateStatus.NOT_APPLICABLE
