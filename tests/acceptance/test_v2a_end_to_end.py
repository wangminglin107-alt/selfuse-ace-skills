from pathlib import Path

import pytest

from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import RunMode, RunStatus, TargetKind
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    InputArtifactRef,
    TargetRef,
)
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.orchestrator.coordinator import ResumeDecision, RunCoordinator
from research_skills_os.core.orchestrator.stop_policy import StopAction
from research_skills_os.core.registry.loader import RegistryLoader

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests" / "acceptance" / "fixtures" / "v2a-project"
CAPABILITIES = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOWS = ROOT / "src" / "research_skills_os" / "workflows"
OUTPUT_FILES = {
    "document_index": "document-index.json",
    "corpus_status": "corpus-status.json",
    "evidence_rows": "evidence-rows.jsonl",
    "synthesis_matrix": "synthesis-matrix.json",
    "contradiction_ledger": "contradiction-ledger.json",
    "coverage_report": "coverage-report.json",
    "citation_identity_audit": "citation-identity-audit.json",
    "citation_support_audit": "citation-support-audit.json",
    "citation_blockers": "citation-blockers.json",
    "theory_candidates": "theory-candidates.json",
    "construct_map": "construct-map.json",
    "theory_rationale": "theory-rationale.md",
    "theory_decision_packet": "theory-decision-packet.json",
}


def catalog():
    return RegistryLoader(capability_roots=[CAPABILITIES], workflow_roots=[WORKFLOWS]).load()


def copy_input(project: Path, relative: str, artifact_type: str, artifact_id: str):
    source = FIXTURE / relative
    destination = project / "inputs" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    return InputArtifactRef(
        artifact_id=artifact_id,
        type=artifact_type,
        path_or_uri=destination.relative_to(project).as_posix(),
    )


def workflow_request(project: Path) -> ExecutionRequest:
    inputs = [
        copy_input(project, "artifacts/source-registry.yaml", "source_registry", "registry"),
        copy_input(project, "sources/source-a.md", "source_document", "source-a"),
        copy_input(project, "sources/source-b.md", "source_document", "source-b"),
        copy_input(
            project,
            "artifacts/research-brief-metadata.json",
            "research_brief_metadata",
            "research-brief",
        ),
        copy_input(
            project,
            "artifacts/novelty-audit.json",
            "novelty_audit",
            "novelty-audit",
        ),
    ]
    return ExecutionRequest(
        request_id="v2a-acceptance-request",
        project_id="v2a-acceptance-project",
        target=TargetRef(kind=TargetKind.WORKFLOW, id="literature-to-theory"),
        mode=RunMode.AUTONOMOUS,
        goal="Run a fully local evidence spine",
        inputs=inputs,
    )


def result_for(project: Path, request: ExecutionRequest, run_id: str, capability_id: str):
    loaded = catalog()
    spec = loaded.capabilities[capability_id]
    store = ArtifactStore(project)
    artifacts = []
    for artifact_type in spec.output_types:
        source = FIXTURE / "artifacts" / OUTPUT_FILES[artifact_type]
        relative = f"artifacts/{capability_id}/{OUTPUT_FILES[artifact_type]}"
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        artifacts.append(
            store.register(
                relative,
                artifact_id=f"{capability_id}-{artifact_type}",
                artifact_type=artifact_type,
                schema_version="1.0",
                producing_capability=capability_id,
                provenance_references=["fixture:v2a-project"],
            )
        )
    return ExecutionResult(
        request_id=request.request_id,
        run_id=run_id,
        target_id=capability_id,
        status=RunStatus.COMPLETED,
        artifacts=artifacts,
    )


def run_workflow(project: Path):
    loaded = catalog()
    request = workflow_request(project)
    coordinator = RunCoordinator(project, loaded)
    context = coordinator.start(request)
    actions = []
    checkpoints = []
    checkpoint_statuses = []
    for capability_id in (
        "paper-knowledge-base",
        "evidence-synthesis",
        "citation-verification",
        "theory-architecture",
    ):
        coordinator.begin_target(context.run_id, capability_id)
        outcome = coordinator.complete_target(
            context.run_id,
            result_for(project, request, context.run_id, capability_id),
        )
        actions.append(outcome.action)
        checkpoints.append(outcome.checkpoint_id)
        checkpoint_statuses.append(
            coordinator.checkpoints.verify_resume(outcome.checkpoint_id).status
        )
    return coordinator, actions, checkpoints, checkpoint_statuses


def test_autonomous_fixture_reaches_proposed_theory_review_with_verified_checkpoints(
    tmp_path: Path,
):
    coordinator, actions, checkpoints, checkpoint_statuses = run_workflow(tmp_path)

    assert actions == [
        StopAction.CONTINUE,
        StopAction.CONTINUE,
        StopAction.CONTINUE,
        StopAction.PAUSE,
    ]
    assert all(checkpoints)
    assert checkpoint_statuses == ["verified"] * 4
    assert coordinator.checkpoints.verify_resume(checkpoints[-1]).status == "verified"
    decision = (
        tmp_path / "artifacts" / "theory-architecture" / "theory-decision-packet.json"
    ).read_text(encoding="utf-8")
    assert '"authorization_state": "proposed"' in decision
    assert '"recommendation": "descriptive"' in decision


def test_source_mutation_invalidates_theory_checkpoint(tmp_path: Path):
    coordinator, _, checkpoints, _ = run_workflow(tmp_path)
    source_b = tmp_path / "inputs" / "sources" / "source-b.md"
    source_b.write_text(source_b.read_text(encoding="utf-8") + "\nChanged.\n", encoding="utf-8")

    verification = coordinator.checkpoints.verify_resume(checkpoints[-1])

    assert verification.status == "drifted"
    with pytest.raises(InvalidStateTransition, match="acceptance or rerun"):
        coordinator.resume(checkpoints[-1], ResumeDecision.CONTINUE)
