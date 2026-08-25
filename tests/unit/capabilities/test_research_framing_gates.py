from copy import deepcopy

import pytest

from research_skills_os.capabilities.research_framing.gates import evaluate_research_brief
from research_skills_os.core.contracts.enums import GateStatus


def bounded(value: str | None, basis: str):
    return {
        "status": "known" if value is not None else "unknown",
        "value": value,
        "basis": basis,
    }


@pytest.fixture
def valid_brief():
    return {
        "schema_version": "1.0",
        "phenomenon": "Creators disclose platform burnout in public exit videos.",
        "research_problem": "Public exit narratives may renegotiate creator-platform obligations.",
        "unit_of_analysis": "Individual creator exit video",
        "level_of_analysis": "Text and creator-platform relation",
        "population_context": bounded("English-language YouTube creators", "user_input"),
        "temporal_scope": bounded("2023-2026", "user_input"),
        "geographic_scope": bounded(None, "explicit_unknown"),
        "constructs": [
            {
                "name": "platform burnout",
                "working_definition": "Creator-described exhaustion attributed to platform work.",
                "basis": "user_input",
            }
        ],
        "research_questions": [
            "How do creator exit videos frame obligations between creators and platforms?"
        ],
        "provisional_contribution": {
            "type": "empirical",
            "statement": "Clarify how exit narratives articulate platform-work obligations.",
            "status": "provisional",
        },
        "assumptions": ["Exit videos are strategic public accounts."],
        "uncertainties": ["Geographic scope is not yet bounded."],
        "user_decisions": ["Use videos, not audience comments, as the initial unit."],
        "claims": [],
    }


def result_by_id(brief):
    return {result.gate_id: result for result in evaluate_research_brief(brief)}


def test_complete_traceable_brief_passes_all_gates(valid_brief):
    results = evaluate_research_brief(valid_brief)

    assert results
    assert all(result.status is GateStatus.PASS for result in results)


@pytest.mark.parametrize(
    "field",
    [
        "phenomenon",
        "research_problem",
        "unit_of_analysis",
        "level_of_analysis",
        "population_context",
        "temporal_scope",
        "geographic_scope",
        "constructs",
        "research_questions",
        "provisional_contribution",
        "assumptions",
        "uncertainties",
        "user_decisions",
    ],
)
def test_required_elements_cannot_be_omitted(valid_brief, field):
    brief = deepcopy(valid_brief)
    del brief[field]

    result = result_by_id(brief)["framing.required"]

    assert result.status is GateStatus.FAIL
    assert any(field in finding for finding in result.findings)


def test_explicit_unknown_scope_is_valid(valid_brief):
    result = result_by_id(valid_brief)["framing.scope_traceable"]

    assert result.status is GateStatus.PASS


@pytest.mark.parametrize("field", ["population_context", "temporal_scope", "geographic_scope"])
def test_hidden_scope_guess_is_rejected(valid_brief, field):
    brief = deepcopy(valid_brief)
    brief[field] = bounded("A scope the user never supplied", "model_inference")

    result = result_by_id(brief)["framing.scope_traceable"]

    assert result.status is GateStatus.FAIL
    assert field in result.findings[0]


@pytest.mark.parametrize(
    "claim",
    [
        {"kind": "novelty", "statement": "No study has examined this.", "evidence_refs": []},
        {
            "kind": "literature",
            "statement": "Prior literature ignores exit narratives.",
            "evidence_refs": [],
        },
    ],
)
def test_novelty_or_unsupported_literature_claims_are_rejected(valid_brief, claim):
    brief = deepcopy(valid_brief)
    brief["claims"] = [claim]

    result = result_by_id(brief)["framing.claim_boundaries"]

    assert result.status is GateStatus.FAIL
