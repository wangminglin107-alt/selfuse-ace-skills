from copy import deepcopy

import pytest

from research_skills_os.capabilities.novelty_audit.gates import evaluate_novelty_audit
from research_skills_os.core.contracts.enums import GateStatus


@pytest.fixture
def defensible_audit():
    return {
        "schema_version": "1.0",
        "research_question": "How do creator exit videos renegotiate platform obligations?",
        "candidate_contribution": {
            "classification": "empirical",
            "statement": "Compare exit-event narratives as public obligation renegotiation.",
        },
        "nearest_work": [
            {
                "source_id": "source-1",
                "title": "Verified fixture on creator exit narratives",
                "verification_status": "verified_content",
                "comparisons": [
                    {
                        "dimension": "phenomenon",
                        "candidate_position": "Exit-event obligation renegotiation",
                        "nearest_work_position": "General creator withdrawal narratives",
                        "evidence_refs": ["source-1#findings"],
                    }
                ],
            }
        ],
        "novelty_claims": [
            {
                "claim_id": "novelty-1",
                "statement": "The candidate distinguishes event-specific obligation renegotiation.",
                "dimension": "phenomenon",
                "evidence_refs": ["source-1#findings"],
                "certainty": "moderate",
            }
        ],
        "verdict": "defensible",
        "verdict_rationale": "The verified nearest work supports the bounded distinction.",
        "revision_recommendation": None,
        "search_absence_as_evidence": False,
        "coverage_limits": ["Verdict is bounded to the verified fixture corpus."],
    }


def results_by_id(audit):
    return {result.gate_id: result for result in evaluate_novelty_audit(audit)}


def test_bounded_defensible_audit_passes(defensible_audit):
    results = evaluate_novelty_audit(defensible_audit)

    assert results
    assert all(result.status is GateStatus.PASS for result in results)


@pytest.mark.parametrize(
    "field",
    [
        "research_question",
        "candidate_contribution",
        "nearest_work",
        "novelty_claims",
        "verdict",
        "verdict_rationale",
        "coverage_limits",
    ],
)
def test_required_audit_elements_cannot_be_omitted(defensible_audit, field):
    audit = deepcopy(defensible_audit)
    del audit[field]

    result = results_by_id(audit)["novelty.required"]

    assert result.status is GateStatus.FAIL
    assert field in result.findings[0]


def test_every_material_novelty_claim_requires_evidence(defensible_audit):
    audit = deepcopy(defensible_audit)
    audit["novelty_claims"][0]["evidence_refs"] = []

    result = results_by_id(audit)["novelty.evidence_support"]

    assert result.status is GateStatus.FAIL


@pytest.mark.parametrize("status", ["candidate", "retrieved", "screened"])
def test_defensible_verdict_cannot_rely_on_unverified_sources(defensible_audit, status):
    audit = deepcopy(defensible_audit)
    audit["nearest_work"][0]["verification_status"] = status

    result = results_by_id(audit)["novelty.verdict_consistency"]

    assert result.status is GateStatus.FAIL


def test_absence_of_search_results_is_not_novelty_evidence(defensible_audit):
    audit = deepcopy(defensible_audit)
    audit["search_absence_as_evidence"] = True

    result = results_by_id(audit)["novelty.evidence_support"]

    assert result.status is GateStatus.FAIL


def test_high_certainty_requires_verified_content(defensible_audit):
    audit = deepcopy(defensible_audit)
    audit["nearest_work"][0]["verification_status"] = "verified_metadata"
    audit["novelty_claims"][0]["certainty"] = "high"

    result = results_by_id(audit)["novelty.certainty_consistency"]

    assert result.status is GateStatus.FAIL


@pytest.mark.parametrize("verdict", ["conditional", "insufficient_evidence", "contradicted"])
def test_nondefensible_verdict_requires_revision_recommendation(defensible_audit, verdict):
    audit = deepcopy(defensible_audit)
    audit["verdict"] = verdict
    audit["revision_recommendation"] = None

    result = results_by_id(audit)["novelty.verdict_consistency"]

    assert result.status is GateStatus.FAIL


def test_negative_novelty_conclusion_is_a_successful_audit(defensible_audit):
    audit = deepcopy(defensible_audit)
    audit["verdict"] = "contradicted"
    audit["verdict_rationale"] = "Verified nearest work already makes the candidate claim."
    audit["revision_recommendation"] = "Narrow the claim or change the research question."

    results = evaluate_novelty_audit(audit)

    assert all(result.status is GateStatus.PASS for result in results)
