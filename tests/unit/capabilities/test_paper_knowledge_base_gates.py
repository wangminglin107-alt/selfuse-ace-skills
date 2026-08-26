from copy import deepcopy
from pathlib import Path

import pytest

from research_skills_os.capabilities.paper_knowledge_base.gates import (
    evaluate_paper_knowledge_base,
)
from research_skills_os.capabilities.paper_knowledge_base.models import (
    normalize_bibliographic_text,
)
from research_skills_os.core.contracts.enums import GateStatus
from research_skills_os.core.registry.loader import RegistryLoader


@pytest.fixture
def valid_index():
    return {
        "schema_version": "1.0",
        "documents": [
            {
                "source_id": "source-1",
                "title": "A traceable paper",
                "authors": ["Researcher, A."],
                "identifiers": {"doi": "10.1000/example"},
                "artifact_id": "artifact-source-1",
                "path": "sources/source-1.md",
                "artifact_sha256": "a" * 64,
                "imported_at": "2026-08-26T12:00:00Z",
                "document_type": "article",
                "language": "en",
                "access_state": "full_text",
                "privacy_label": "public",
                "content_availability": "full_text",
                "locators": [
                    {
                        "page": 7,
                        "block_id": "p7-b2",
                        "content_sha256": "b" * 64,
                    }
                ],
                "extraction_method": "manual-markdown",
                "extraction_warnings": [],
                "version_state": "current",
                "supersedes_source_id": None,
                "superseded_by_source_id": None,
                "metadata_verification": "verified",
            }
        ],
    }


@pytest.fixture
def valid_status():
    return {
        "schema_version": "1.0",
        "artifact_hashes": {"source-1": "a" * 64},
        "unresolved_duplicate_groups": [],
        "privacy_declared": True,
        "coverage_limits": ["Only the registered project corpus is indexed."],
    }


def by_id(index, status):
    return {
        result.gate_id: result
        for result in evaluate_paper_knowledge_base(index, status)
    }


def test_valid_document_index_passes_in_stable_gate_order(valid_index, valid_status):
    results = evaluate_paper_knowledge_base(valid_index, valid_status)

    assert [result.gate_id for result in results] == [
        "corpus.required",
        "corpus.identity_integrity",
        "corpus.locators",
        "corpus.privacy_declared",
    ]
    assert all(result.status is GateStatus.PASS for result in results)


def test_duplicate_source_ids_fail_identity_gate(valid_index, valid_status):
    index = deepcopy(valid_index)
    index["documents"].append(deepcopy(index["documents"][0]))

    result = by_id(index, valid_status)["corpus.identity_integrity"]

    assert result.status is GateStatus.FAIL
    assert "duplicate source_id" in result.findings[0]


def test_full_text_document_requires_a_locator(valid_index, valid_status):
    index = deepcopy(valid_index)
    index["documents"][0]["locators"] = []

    result = by_id(index, valid_status)["corpus.locators"]

    assert result.status is GateStatus.FAIL


def test_metadata_only_document_does_not_pass_content_ready_gate(valid_index, valid_status):
    index = deepcopy(valid_index)
    index["documents"][0]["content_availability"] = "metadata_only"

    result = by_id(index, valid_status)["corpus.locators"]

    assert result.status is GateStatus.FAIL


def test_status_hash_must_match_document_artifact_hash(valid_index, valid_status):
    status = deepcopy(valid_status)
    status["artifact_hashes"]["source-1"] = "c" * 64

    result = by_id(valid_index, status)["corpus.identity_integrity"]

    assert result.status is GateStatus.FAIL
    assert "hash mismatch" in result.findings[0]


def test_privacy_state_must_be_explicit(valid_index, valid_status):
    index = deepcopy(valid_index)
    index["documents"][0]["privacy_label"] = None

    result = by_id(index, valid_status)["corpus.privacy_declared"]

    assert result.status is GateStatus.FAIL


def test_absolute_artifact_path_fails_identity_gate(valid_index, valid_status):
    index = deepcopy(valid_index)
    index["documents"][0]["path"] = "C:/private/source-1.md"

    result = by_id(index, valid_status)["corpus.identity_integrity"]

    assert result.status is GateStatus.FAIL
    assert "project-relative" in result.findings[0]


def test_superseded_document_requires_replacement_source_id(valid_index, valid_status):
    index = deepcopy(valid_index)
    index["documents"][0]["version_state"] = "superseded"

    result = by_id(index, valid_status)["corpus.identity_integrity"]

    assert result.status is GateStatus.FAIL
    assert "replacement" in result.findings[0]


def test_capability_manifest_is_offline_and_declares_outputs():
    root = Path(__file__).parents[3] / "src" / "research_skills_os" / "capabilities"
    spec = RegistryLoader(capability_roots=[root]).load().capabilities["paper-knowledge-base"]

    assert spec.network == "none"
    assert spec.providers == ["local-manual"]
    assert spec.input_types == ["source_registry", "source_document"]
    assert spec.output_types == ["document_index", "corpus_status"]


def test_bibliographic_text_normalization_is_deterministic_and_strips_markup():
    raw = "  Platform <i>Withdrawal</i>\n   and   Exit  "

    assert normalize_bibliographic_text(raw) == "Platform Withdrawal and Exit"
    assert normalize_bibliographic_text(raw) == normalize_bibliographic_text(raw)
