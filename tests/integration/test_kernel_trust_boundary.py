import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import (
    GateSeverity,
    GateStatus,
    RunMode,
    RunStatus,
    TargetKind,
)
from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    ExecutionRequest,
    ExecutionResult,
    GateResult,
    InputArtifactRef,
    TargetRef,
)
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.orchestrator.coordinator import RunCoordinator
from research_skills_os.core.orchestrator.stop_policy import StopAction
from research_skills_os.core.registry.loader import RegistryLoader

ROOT = Path(__file__).parents[2]
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
FIXTURE = ROOT / "tests" / "acceptance" / "fixtures" / "end-to-end-project" / "artifacts"


def catalog():
    return RegistryLoader(capability_roots=[CAPABILITIES]).load()


def request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id="trust-request",
        project_id="trust-project",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="research-framing"),
        mode=RunMode.INTERACTIVE,
        goal="Exercise the kernel trust boundary",
    )


def start(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog())
    execution_request = request()
    context = coordinator.start(execution_request)
    coordinator.begin_target(context.run_id, "research-framing")
    return coordinator, context


def valid_brief() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "phenomenon": "Creator exit announcements.",
        "research_problem": "How are obligations framed?",
        "unit_of_analysis": "Announcement",
        "level_of_analysis": "Message",
        "population_context": {"status": "unknown", "value": None, "basis": "explicit_unknown"},
        "temporal_scope": {"status": "unknown", "value": None, "basis": "explicit_unknown"},
        "geographic_scope": {"status": "unknown", "value": None, "basis": "explicit_unknown"},
        "constructs": [
            {"name": "obligation", "working_definition": "A stated duty.", "basis": "user_input"}
        ],
        "research_questions": ["How are obligations framed?"],
        "provisional_contribution": {
            "type": "empirical",
            "statement": "Describe the bounded corpus.",
            "status": "provisional",
        },
        "assumptions": [],
        "uncertainties": ["Scope is unknown."],
        "user_decisions": [],
        "claims": [],
    }


def registered_artifacts(
    tmp_path: Path,
    brief: dict[str, object],
    *,
    markdown_text: str = "# Brief\n",
):
    store = ArtifactStore(tmp_path)
    markdown = tmp_path / "artifacts" / "research-framing" / "brief.md"
    metadata = tmp_path / "artifacts" / "research-framing" / "brief.yaml"
    markdown.parent.mkdir(parents=True)
    markdown.write_text(markdown_text, encoding="utf-8", newline="\n")
    metadata.write_text(yaml.safe_dump(brief), encoding="utf-8", newline="\n")
    return [
        store.register(
            "artifacts/research-framing/brief.md",
            artifact_id="brief-markdown",
            artifact_type="research_brief_markdown",
            schema_version="1.0",
            producing_capability="research-framing",
            provenance_references=["user-input:idea"],
        ),
        store.register(
            "artifacts/research-framing/brief.yaml",
            artifact_id="brief-metadata",
            artifact_type="research_brief_metadata",
            schema_version="1.0",
            producing_capability="research-framing",
            provenance_references=["user-input:idea"],
        ),
    ]


def test_failed_result_cannot_complete_or_checkpoint(tmp_path: Path):
    coordinator, context = start(tmp_path)
    result = ExecutionResult(
        request_id="trust-request",
        run_id=context.run_id,
        target_id="research-framing",
        status=RunStatus.FAILED,
        artifacts=registered_artifacts(tmp_path, valid_brief()),
    )

    with pytest.raises(InvalidStateTransition, match="completed result status"):
        coordinator.complete_target(context.run_id, result)

    assert coordinator.repository.load().completed_targets == []
    assert coordinator.checkpoints.current() is None


def test_nonexistent_artifact_blocks_before_registration_or_checkpoint(tmp_path: Path):
    coordinator, context = start(tmp_path)
    missing = ArtifactEnvelope(
        artifact_id="missing-markdown",
        type="research_brief_markdown",
        schema_version="1.0",
        producing_capability="research-framing",
        created_at=datetime.now(UTC),
        path="artifacts/research-framing/missing.md",
        sha256="a" * 64,
        provenance_references=["user-input:idea"],
    )
    metadata = registered_artifacts(tmp_path, valid_brief())[1]
    result = ExecutionResult(
        request_id="trust-request",
        run_id=context.run_id,
        target_id="research-framing",
        status=RunStatus.COMPLETED,
        artifacts=[missing, metadata],
    )

    outcome = coordinator.complete_target(context.run_id, result)

    assert outcome.action is StopAction.BLOCK
    assert "artifacts.integrity" in {item.gate_id for item in outcome.gate_results}
    assert coordinator.repository.load().artifacts == {}
    assert coordinator.checkpoints.current() is None


def test_kernel_recomputes_scholarly_gates_instead_of_trusting_forged_passes(tmp_path: Path):
    coordinator, context = start(tmp_path)
    invalid = valid_brief()
    invalid["claims"] = [
        {
            "kind": "novelty",
            "statement": "This is the first study.",
            "evidence_refs": [],
        }
    ]
    forged = [
        GateResult(
            gate_id=gate_id,
            gate_version="999",
            status=GateStatus.PASS,
            severity=GateSeverity.INFO,
        )
        for gate_id in (
            "framing.required",
            "framing.scope_traceable",
            "framing.claim_boundaries",
        )
    ]
    result = ExecutionResult(
        request_id="trust-request",
        run_id=context.run_id,
        target_id="research-framing",
        status=RunStatus.COMPLETED,
        artifacts=registered_artifacts(tmp_path, invalid),
        gate_results=forged,
    )

    outcome = coordinator.complete_target(context.run_id, result)

    claim_gate = next(
        item for item in outcome.gate_results if item.gate_id == "framing.claim_boundaries"
    )
    assert outcome.action is StopAction.BLOCK
    assert claim_gate.status is GateStatus.FAIL
    assert claim_gate.gate_version == "1.0"
    assert claim_gate.severity is GateSeverity.BLOCKING
    assert coordinator.checkpoints.current() is None


def test_clean_metadata_cannot_hide_first_study_claim_in_framing_markdown(tmp_path: Path):
    coordinator, context = start(tmp_path)
    result = ExecutionResult(
        request_id="trust-request",
        run_id=context.run_id,
        target_id="research-framing",
        status=RunStatus.COMPLETED,
        artifacts=registered_artifacts(
            tmp_path,
            valid_brief(),
            markdown_text="# Brief\n\nThis is the first study of the phenomenon.\n",
        ),
    )

    outcome = coordinator.complete_target(context.run_id, result)

    claim_gate = next(
        item for item in outcome.gate_results if item.gate_id == "framing.claim_boundaries"
    )
    assert outcome.action is StopAction.BLOCK
    assert claim_gate.status is GateStatus.FAIL
    assert any("Markdown" in finding for finding in claim_gate.findings)


def test_clean_audit_yaml_cannot_hide_first_study_claim_in_novelty_matrix(tmp_path: Path):
    input_files = {
        "research_brief_metadata": "research-brief-metadata.yaml",
        "search_ledger": "search-ledger.yaml",
        "source_registry": "source-registry.yaml",
        "evidence_map": "evidence-map.yaml",
    }
    inputs = []
    for artifact_type, filename in input_files.items():
        relative = f"inputs/{filename}"
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            (FIXTURE / filename).read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        inputs.append(
            InputArtifactRef(
                artifact_id=f"input-{artifact_type}",
                type=artifact_type,
                path_or_uri=relative,
            )
        )
    execution_request = ExecutionRequest(
        request_id="novelty-request",
        project_id="trust-project",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="novelty-audit"),
        mode=RunMode.INTERACTIVE,
        goal="Exercise user-facing novelty output checks",
        inputs=inputs,
    )
    coordinator = RunCoordinator(tmp_path, catalog())
    context = coordinator.start(execution_request)
    coordinator.begin_target(context.run_id, "novelty-audit")
    matrix = tmp_path / "artifacts" / "novelty-audit" / "matrix.md"
    audit = tmp_path / "artifacts" / "novelty-audit" / "audit.yaml"
    matrix.parent.mkdir(parents=True)
    matrix.write_text(
        "# Novelty matrix\n\nThis is the first study of this phenomenon.\n",
        encoding="utf-8",
        newline="\n",
    )
    audit.write_text(
        (FIXTURE / "novelty-audit.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    store = ArtifactStore(tmp_path)
    result = ExecutionResult(
        request_id=execution_request.request_id,
        run_id=context.run_id,
        target_id="novelty-audit",
        status=RunStatus.COMPLETED,
        artifacts=[
            store.register(
                "artifacts/novelty-audit/matrix.md",
                artifact_id="novelty-matrix",
                artifact_type="novelty_matrix",
                schema_version="1.0",
                producing_capability="novelty-audit",
                provenance_references=["fixture:matrix"],
            ),
            store.register(
                "artifacts/novelty-audit/audit.yaml",
                artifact_id="novelty-audit",
                artifact_type="novelty_audit",
                schema_version="1.0",
                producing_capability="novelty-audit",
                provenance_references=["fixture:audit"],
            ),
        ],
    )

    outcome = coordinator.complete_target(context.run_id, result)

    evidence_gate = next(
        item for item in outcome.gate_results if item.gate_id == "novelty.evidence_support"
    )
    assert outcome.action is StopAction.BLOCK
    assert evidence_gate.status is GateStatus.FAIL
    assert any("matrix" in finding.casefold() for finding in evidence_gate.findings)


def test_v2a_kernel_rejects_forged_pass_for_metadata_only_corpus(tmp_path: Path):
    inputs = []
    for artifact_type in ("source_registry", "source_document"):
        relative = f"inputs/{artifact_type}.json"
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("{}", encoding="utf-8", newline="\n")
        inputs.append(
            InputArtifactRef(
                artifact_id=f"input-{artifact_type}",
                type=artifact_type,
                path_or_uri=relative,
            )
        )
    execution_request = ExecutionRequest(
        request_id="v2a-trust-request",
        project_id="v2a-trust-project",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="paper-knowledge-base"),
        mode=RunMode.INTERACTIVE,
        goal="Reject forged V2A gates",
        inputs=inputs,
    )
    coordinator = RunCoordinator(tmp_path, catalog())
    context = coordinator.start(execution_request)
    coordinator.begin_target(context.run_id, "paper-knowledge-base")

    index = {
        "schema_version": "1.0",
        "documents": [
            {
                "source_id": "source-1",
                "title": "Metadata-only source",
                "authors": ["Researcher, A."],
                "identifiers": {},
                "artifact_id": "source-artifact",
                "path": "inputs/source_document.json",
                "artifact_sha256": "a" * 64,
                "imported_at": "2026-08-26T12:00:00Z",
                "document_type": "article",
                "language": "en",
                "access_state": "metadata_only",
                "privacy_label": "public",
                "content_availability": "metadata_only",
                "locators": [],
                "extraction_method": "metadata-provider",
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
        "coverage_limits": ["Metadata only."],
    }
    output_dir = tmp_path / "artifacts" / "paper-knowledge-base"
    output_dir.mkdir(parents=True)
    (output_dir / "document_index.json").write_text(
        json.dumps(index), encoding="utf-8", newline="\n"
    )
    (output_dir / "corpus_status.json").write_text(
        json.dumps(status), encoding="utf-8", newline="\n"
    )
    store = ArtifactStore(tmp_path)
    artifacts = [
        store.register(
            "artifacts/paper-knowledge-base/document_index.json",
            artifact_id="document-index",
            artifact_type="document_index",
            schema_version="1.0",
            producing_capability="paper-knowledge-base",
        ),
        store.register(
            "artifacts/paper-knowledge-base/corpus_status.json",
            artifact_id="corpus-status",
            artifact_type="corpus_status",
            schema_version="1.0",
            producing_capability="paper-knowledge-base",
        ),
    ]
    forged = [
        GateResult(
            gate_id=gate_id,
            gate_version="999",
            status=GateStatus.PASS,
            severity=GateSeverity.INFO,
        )
        for gate_id in catalog().capabilities["paper-knowledge-base"].exit_gates
    ]
    result = ExecutionResult(
        request_id=execution_request.request_id,
        run_id=context.run_id,
        target_id="paper-knowledge-base",
        status=RunStatus.COMPLETED,
        artifacts=artifacts,
        gate_results=forged,
    )

    outcome = coordinator.complete_target(context.run_id, result)

    locator_gate = next(
        item for item in outcome.gate_results if item.gate_id == "corpus.locators"
    )
    assert outcome.action is StopAction.BLOCK
    assert locator_gate.status is GateStatus.FAIL
    assert locator_gate.gate_version == "1.0"
