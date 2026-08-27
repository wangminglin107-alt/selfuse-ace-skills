import json
from hashlib import sha256
from pathlib import Path

from research_skills_os.capabilities.gate_evaluators import evaluate_capability_artifacts
from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import GateStatus


def register_json(project: Path, artifact_type: str, value, capability: str):
    path = project / "artifacts" / capability / f"{artifact_type}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    return ArtifactStore(project).register(
        path.relative_to(project),
        artifact_id=f"artifact-{artifact_type}",
        artifact_type=artifact_type,
        schema_version="1.0",
        producing_capability=capability,
        provenance_references=["fixture:v2a"],
    )


def valid_paper_knowledge_base_artifacts(project: Path):
    index = {
        "schema_version": "1.0",
        "documents": [
            {
                "source_id": "source-1",
                "title": "Traceable paper",
                "authors": ["Researcher, A."],
                "identifiers": {},
                "artifact_id": "source-artifact",
                "path": "sources/paper.md",
                "artifact_sha256": "a" * 64,
                "imported_at": "2026-08-26T12:00:00Z",
                "document_type": "article",
                "language": "en",
                "access_state": "full_text",
                "privacy_label": "public",
                "content_availability": "full_text",
                "locators": [{"page": 1, "block_id": "p1", "content_sha256": "b" * 64}],
                "extraction_method": "manual",
                "extraction_warnings": [],
                "version_state": "current",
                "supersedes_source_id": None,
                "superseded_by_source_id": None,
                "metadata_verification": "verified",
            }
        ],
    }
    status = {
        "schema_version": "1.0",
        "artifact_hashes": {"source-1": "a" * 64},
        "unresolved_duplicate_groups": [],
        "privacy_declared": True,
        "coverage_limits": ["Fixture corpus."],
    }
    return [
        register_json(project, "document_index", index, "paper-knowledge-base"),
        register_json(project, "corpus_status", status, "paper-knowledge-base"),
    ]


def test_kernel_dispatches_paper_knowledge_base_from_registered_json(tmp_path: Path):
    results = evaluate_capability_artifacts(
        "paper-knowledge-base",
        tmp_path,
        valid_paper_knowledge_base_artifacts(tmp_path),
    )

    assert results
    assert all(result.status is GateStatus.PASS for result in results)


def test_malformed_jsonl_returns_required_failure_with_line_number(tmp_path: Path):
    rows_path = tmp_path / "artifacts" / "evidence-synthesis" / "evidence_rows.jsonl"
    rows_path.parent.mkdir(parents=True)
    rows_path.write_text('{"row_id":"row-1"}\n{broken}\n', encoding="utf-8", newline="\n")
    rows = ArtifactStore(tmp_path).register(
        rows_path.relative_to(tmp_path),
        artifact_id="artifact-evidence-rows",
        artifact_type="evidence_rows",
        schema_version="1.0",
        producing_capability="evidence-synthesis",
        provenance_references=["fixture:v2a"],
    )
    other = [
        register_json(
            tmp_path,
            "synthesis_matrix",
            {"schema_version": "1.0", "groups": []},
            "evidence-synthesis",
        ),
        register_json(
            tmp_path,
            "contradiction_ledger",
            {"schema_version": "1.0", "entries": []},
            "evidence-synthesis",
        ),
        register_json(
            tmp_path,
            "coverage_report",
            {
                "schema_version": "1.0",
                "source_ids": [],
                "question_dimensions": [],
                "downstream_claim_ids": [],
                "uncovered_dimensions": [],
                "coverage_limits": ["Fixture."],
            },
            "evidence-synthesis",
        ),
    ]

    results = evaluate_capability_artifacts("evidence-synthesis", tmp_path, [rows, *other])
    required = next(result for result in results if result.gate_id == "synthesis.required")

    assert required.status is GateStatus.FAIL
    assert any("line 2" in finding for finding in required.findings)


def test_loader_reads_registered_content_not_caller_payload(tmp_path: Path):
    artifacts = valid_paper_knowledge_base_artifacts(tmp_path)
    index = next(item for item in artifacts if item.type == "document_index")
    path = tmp_path / index.path
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["documents"][0]["content_availability"] = "metadata_only"
    path.write_text(json.dumps(raw), encoding="utf-8", newline="\n")

    results = evaluate_capability_artifacts("paper-knowledge-base", tmp_path, artifacts)

    assert sha256(path.read_bytes()).hexdigest() != index.sha256
    locator_gate = next(item for item in results if item.gate_id == "corpus.locators")
    assert locator_gate.status is GateStatus.FAIL
