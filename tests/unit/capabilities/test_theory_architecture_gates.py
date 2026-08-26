from research_skills_os.capabilities.theory_architecture.gates import (
    evaluate_theory_architecture,
)
from research_skills_os.core.contracts.enums import GateStatus


def candidates():
    return {
        "schema_version": "1.0",
        "candidates": [
            {
                "candidate_id": "candidate-1",
                "name": "Bounded mechanism account",
                "theories": ["Selective exposure"],
                "construct_ids": ["account-type", "engagement"],
                "mechanisms": ["Audience selection may condition engagement."],
                "level_of_analysis": "account",
                "evidence_row_ids": ["row-1"],
                "acknowledged_contradiction_ids": ["conflict-1"],
                "assumptions": ["Account classification is meaningful for this archive."],
                "compatibility_rationale": None,
                "limitations": ["The evidence is associational."],
            }
        ],
    }


def construct_map():
    return {
        "schema_version": "1.0",
        "known_evidence_row_ids": ["row-1", "row-2"],
        "material_contradiction_ids": ["conflict-1"],
        "constructs": [
            {
                "construct_id": "account-type",
                "label": "Account type",
                "definition": "A declared archive-level account classification.",
                "level_of_analysis": "account",
                "evidence_row_ids": ["row-1"],
            },
            {
                "construct_id": "engagement",
                "label": "Engagement",
                "definition": "Thirty-day public interaction counts.",
                "level_of_analysis": "account",
                "evidence_row_ids": ["row-1"],
            },
        ],
        "relations": [
            {
                "from_construct_id": "account-type",
                "to_construct_id": "engagement",
                "mechanism": "Audience selection may condition engagement.",
                "evidence_row_ids": ["row-1"],
                "cross_level_rationale": None,
            }
        ],
    }


def valid_decision(**updates):
    value = {
        "schema_version": "1.0",
        "recommendation": "single_theory",
        "selected_candidate_id": "candidate-1",
        "authorization_state": "proposed",
        "user_decision_id": None,
        "rationale": "The candidate is bounded by verified associational evidence.",
        "acknowledged_contradiction_ids": ["conflict-1"],
    }
    value.update(updates)
    return value


def by_id(candidate_value=None, constructs=None, decision=None, rationale="Bounded synthesis."):
    return {
        result.gate_id: result
        for result in evaluate_theory_architecture(
            candidate_value or candidates(),
            constructs or construct_map(),
            decision or valid_decision(),
            rationale,
        )
    }


def test_valid_theory_packet_passes_in_stable_order():
    results = evaluate_theory_architecture(
        candidates(), construct_map(), valid_decision(), "Bounded synthesis."
    )

    assert [result.gate_id for result in results] == [
        "theory.required",
        "theory.evidence_fit",
        "theory.construct_consistency",
        "theory.level_consistency",
        "theory.contradictions_acknowledged",
        "theory.no_forced_theory",
        "theory.user_decision",
    ]
    assert all(result.status is GateStatus.PASS for result in results)


def test_unknown_evidence_row_reference_fails_evidence_fit():
    value = candidates()
    value["candidates"][0]["evidence_row_ids"] = ["unknown-row"]

    assert by_id(value)["theory.evidence_fit"].status is GateStatus.FAIL


def test_incompatible_levels_require_cross_level_rationale():
    constructs = construct_map()
    constructs["constructs"][1]["level_of_analysis"] = "individual"

    assert by_id(constructs=constructs)["theory.level_consistency"].status is GateStatus.FAIL


def test_hidden_assumptions_fail_evidence_fit():
    value = candidates()
    value["candidates"][0]["assumptions"] = []

    assert by_id(value)["theory.evidence_fit"].status is GateStatus.FAIL


def test_bounded_integration_requires_compatibility_rationale():
    value = candidates()
    value["candidates"][0]["theories"] = ["Theory A", "Theory B"]
    decision = valid_decision(recommendation="bounded_integration")

    assert by_id(value, decision=decision)["theory.construct_consistency"].status is GateStatus.FAIL


def test_material_contradiction_must_be_acknowledged_by_candidate_and_decision():
    value = candidates()
    value["candidates"][0]["acknowledged_contradiction_ids"] = []

    result = by_id(value)["theory.contradictions_acknowledged"]

    assert result.status is GateStatus.FAIL


def test_descriptive_recommendation_is_valid_when_theory_support_is_insufficient():
    decision = valid_decision(
        recommendation="descriptive",
        selected_candidate_id=None,
        authorization_state="proposed",
        rationale="Verified evidence does not establish a defensible mechanism.",
    )
    results = by_id(
        candidate_value={"schema_version": "1.0", "candidates": []},
        constructs=construct_map(),
        decision=decision,
        rationale="Bounded synthesis.",
    )

    assert results["theory.no_forced_theory"].status is GateStatus.PASS


def test_non_descriptive_recommendation_requires_candidate():
    result = by_id(
        candidate_value={"schema_version": "1.0", "candidates": []},
        decision=valid_decision(selected_candidate_id=None),
    )["theory.no_forced_theory"]

    assert result.status is GateStatus.FAIL


def test_selected_theory_requires_user_decision_id():
    decision = valid_decision(authorization_state="selected", user_decision_id=None)

    assert by_id(decision=decision)["theory.user_decision"].status is GateStatus.FAIL


def test_selected_theory_with_user_decision_passes():
    decision = valid_decision(
        authorization_state="selected", user_decision_id="decision-user-1"
    )

    assert by_id(decision=decision)["theory.user_decision"].status is GateStatus.PASS
