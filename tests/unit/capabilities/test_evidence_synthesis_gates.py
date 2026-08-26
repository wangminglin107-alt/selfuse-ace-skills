from copy import deepcopy
from hashlib import sha256

import pytest

from research_skills_os.capabilities.evidence_synthesis.gates import (
    evaluate_evidence_synthesis,
)
from research_skills_os.core.contracts.enums import GateStatus


def passage_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def valid_row():
    passage = "The study reports a bounded association between the two measures."
    return {
        "schema_version": "1.0",
        "row_id": "row-1",
        "synthesis_group": "engagement-association",
        "question_dimension": "association",
        "source_id": "source-1",
        "artifact_sha256": "a" * 64,
        "exact_passage": passage,
        "reviewed_translation": None,
        "passage_language": "en",
        "locator": {
            "page": 7,
            "block_id": "p7-b2",
            "content_sha256": passage_hash(passage),
        },
        "source_claim": "The measures are associated in this sample.",
        "author_inference": "This may reflect differential audience response.",
        "study_context": "A public social-media archive.",
        "method": "Observational comparison",
        "population": "Public account-day records",
        "boundary_conditions": ["Association is not causation."],
        "evidence_role": "supports",
        "verification_status": "verified_content",
        "verifier_note": "Checked against the exact passage.",
        "downstream_claim_ids": ["claim-1"],
    }


def matrix(row_ids=None):
    return {
        "schema_version": "1.0",
        "groups": [
            {
                "group_id": "engagement-association",
                "row_ids": row_ids or ["row-1"],
                "provisional_claim": "A bounded association is reported.",
                "downstream_claim_ids": ["claim-1"],
            }
        ],
    }


def ledger(entries=None):
    return {"schema_version": "1.0", "entries": entries or []}


def coverage():
    return {
        "schema_version": "1.0",
        "source_ids": ["source-1", "source-2"],
        "question_dimensions": ["association"],
        "downstream_claim_ids": ["claim-1"],
        "uncovered_dimensions": [],
        "coverage_limits": ["The corpus is bounded to registered sources."],
    }


def by_id(rows, matrix_value=None, ledger_value=None, coverage_value=None):
    results = evaluate_evidence_synthesis(
        rows,
        matrix_value or matrix(),
        ledger_value or ledger(),
        coverage_value or coverage(),
    )
    return {result.gate_id: result for result in results}


def test_valid_synthesis_passes_in_stable_order(valid_row):
    results = evaluate_evidence_synthesis([valid_row], matrix(), ledger(), coverage())

    assert [result.gate_id for result in results] == [
        "synthesis.required",
        "synthesis.content_trace",
        "synthesis.source_inference_boundary",
        "synthesis.contradiction_preserved",
        "synthesis.material_contradictions",
        "synthesis.coverage",
    ]
    assert all(result.status is GateStatus.PASS for result in results)


def test_evidence_row_separates_source_claim_from_author_inference(valid_row):
    row = deepcopy(valid_row)
    row["source_claim"] = row["author_inference"]

    result = by_id([row])["synthesis.source_inference_boundary"]

    assert result.status is GateStatus.FAIL


def test_exact_passage_and_locator_are_required(valid_row):
    row = deepcopy(valid_row)
    row["exact_passage"] = ""

    result = by_id([row])["synthesis.content_trace"]

    assert result.status is GateStatus.FAIL


def test_exact_passage_hash_must_match_locator(valid_row):
    row = deepcopy(valid_row)
    row["locator"]["content_sha256"] = "c" * 64

    result = by_id([row])["synthesis.content_trace"]

    assert result.status is GateStatus.FAIL
    assert "hash" in result.findings[0]


def test_unknown_source_id_fails_content_trace(valid_row):
    row = deepcopy(valid_row)
    row["source_id"] = "missing-source"

    result = by_id([row])["synthesis.content_trace"]

    assert result.status is GateStatus.FAIL


def test_duplicate_row_ids_fail_coverage(valid_row):
    duplicate = deepcopy(valid_row)

    result = by_id([valid_row, duplicate])["synthesis.coverage"]

    assert result.status is GateStatus.FAIL


def test_unknown_downstream_claim_reference_fails_coverage(valid_row):
    row = deepcopy(valid_row)
    row["downstream_claim_ids"] = ["unknown-claim"]

    result = by_id([row])["synthesis.coverage"]

    assert result.status is GateStatus.FAIL


def test_translation_cannot_replace_original_passage(valid_row):
    row = deepcopy(valid_row)
    row["exact_passage"] = ""
    row["reviewed_translation"] = "译文不能替代原文。"

    result = by_id([row])["synthesis.content_trace"]

    assert result.status is GateStatus.FAIL


def test_opposing_roles_require_contradiction_ledger_entry(valid_row):
    opposing = deepcopy(valid_row)
    opposing["row_id"] = "row-2"
    opposing["source_id"] = "source-2"
    opposing["evidence_role"] = "contradicts"

    result = by_id(
        [valid_row, opposing], matrix(["row-1", "row-2"])
    )["synthesis.contradiction_preserved"]

    assert result.status is GateStatus.FAIL


def test_material_unresolved_contradiction_blocks_progress(valid_row):
    entry = {
        "contradiction_id": "conflict-1",
        "synthesis_group": "engagement-association",
        "row_ids": ["row-1", "row-2"],
        "competing_claims": ["Association is positive.", "Association is absent."],
        "possible_scope_explanations": ["Different samples."],
        "unresolved_issue": "The scope difference is not yet established.",
        "material": True,
        "resolution_state": "open",
        "boundary_note": None,
    }

    result = by_id([valid_row], ledger_value=ledger([entry]))[
        "synthesis.material_contradictions"
    ]

    assert result.status is GateStatus.FAIL


def test_nonmaterial_open_contradiction_requires_boundary_note(valid_row):
    entry = {
        "contradiction_id": "conflict-1",
        "synthesis_group": "engagement-association",
        "row_ids": ["row-1", "row-2"],
        "competing_claims": ["Association is positive.", "Association is absent."],
        "possible_scope_explanations": [],
        "unresolved_issue": "Minor scope disagreement.",
        "material": False,
        "resolution_state": "open",
        "boundary_note": None,
    }

    result = by_id([valid_row], ledger_value=ledger([entry]))[
        "synthesis.material_contradictions"
    ]

    assert result.status is GateStatus.FAIL


def test_null_result_remains_in_synthesis(valid_row):
    row = deepcopy(valid_row)
    row["evidence_role"] = "null"

    results = by_id([row])

    assert results["synthesis.required"].status is GateStatus.PASS
    assert results["synthesis.contradiction_preserved"].status is GateStatus.PASS
