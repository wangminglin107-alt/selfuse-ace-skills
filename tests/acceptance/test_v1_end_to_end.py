from pathlib import Path
from typing import Any

import yaml

from research_skills_os.capabilities.literature_intelligence.gates import (
    evaluate_literature_artifacts,
)
from research_skills_os.capabilities.novelty_audit.gates import evaluate_novelty_audit
from research_skills_os.capabilities.research_framing.gates import evaluate_research_brief
from research_skills_os.core.artifacts.store import ArtifactStore
from research_skills_os.core.contracts.enums import GateStatus, RunMode, RunStatus, TargetKind
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    InputArtifactRef,
    TargetRef,
)
from research_skills_os.core.orchestrator.coordinator import ResumeDecision, RunCoordinator
from research_skills_os.core.orchestrator.stop_policy import StopAction
from research_skills_os.core.registry.loader import RegistryLoader
from research_skills_os.core.registry.models import CapabilitySpec, RegistryCatalog

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests" / "acceptance" / "fixtures" / "end-to-end-project" / "artifacts"
CAPABILITY_ROOT = ROOT / "src" / "research_skills_os" / "capabilities"
WORKFLOW_ROOT = ROOT / "src" / "research_skills_os" / "workflows"


def load_yaml(name: str) -> dict[str, Any]:
    return yaml.safe_load((FIXTURE / name).read_text(encoding="utf-8"))


def catalog() -> RegistryCatalog:
    return RegistryLoader(capability_roots=[CAPABILITY_ROOT], workflow_roots=[WORKFLOW_ROOT]).load()


def gates_for(capability_id: str):
    if capability_id == "research-framing":
        return evaluate_research_brief(load_yaml("research-brief-metadata.yaml"))
    if capability_id == "literature-intelligence":
        return evaluate_literature_artifacts(
            load_yaml("search-ledger.yaml"),
            load_yaml("source-registry.yaml"),
            load_yaml("evidence-map.yaml"),
        )
    return evaluate_novelty_audit(load_yaml("novelty-audit.yaml"))


def payload_for(artifact_type: str) -> str:
    files = {
        "research_brief_markdown": "research-brief.md",
        "research_brief_metadata": "research-brief-metadata.yaml",
        "search_ledger": "search-ledger.yaml",
        "source_registry": "source-registry.yaml",
        "evidence_map": "evidence-map.yaml",
        "novelty_matrix": "novelty-matrix.md",
        "novelty_audit": "novelty-audit.yaml",
    }
    return (FIXTURE / files[artifact_type]).read_text(encoding="utf-8")


def result_for(
    project: Path,
    request: ExecutionRequest,
    run_id: str,
    spec: CapabilitySpec,
) -> ExecutionResult:
    store = ArtifactStore(project)
    artifacts = []
    for index, artifact_type in enumerate(spec.output_types, start=1):
        relative = f"artifacts/{spec.id}/{artifact_type}.txt"
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload_for(artifact_type), encoding="utf-8", newline="\n")
        artifacts.append(
            store.register(
                relative,
                artifact_id=f"{spec.id}-{index}",
                artifact_type=artifact_type,
                schema_version="1.0",
                producing_capability=spec.id,
                provenance_references=["fixture:end-to-end-project"],
            )
        )
    return ExecutionResult(
        request_id=request.request_id,
        run_id=run_id,
        target_id=spec.id,
        status=RunStatus.COMPLETED,
        artifacts=artifacts,
        gate_results=gates_for(spec.id),
    )


def request(kind: TargetKind, target_id: str, mode: RunMode, request_id: str):
    return ExecutionRequest(
        request_id=request_id,
        project_id="acceptance-project",
        target=TargetRef(kind=kind, id=target_id),
        mode=mode,
        goal="Run the offline acceptance fixture",
    )


def novelty_inputs(project: Path) -> list[InputArtifactRef]:
    fixtures = {
        "research_brief_metadata": "research-brief-metadata.yaml",
        "search_ledger": "search-ledger.yaml",
        "source_registry": "source-registry.yaml",
        "evidence_map": "evidence-map.yaml",
    }
    inputs = []
    for artifact_type, fixture_name in fixtures.items():
        relative = f"inputs/{fixture_name}"
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            (FIXTURE / fixture_name).read_text(encoding="utf-8"),
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
    return inputs


def test_fixture_gates_pass_without_network_or_secret_material():
    for capability_id in ("research-framing", "literature-intelligence", "novelty-audit"):
        results = gates_for(capability_id)
        assert all(result.status is not GateStatus.FAIL for result in results)
    serialized = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(FIXTURE.iterdir())
    ).casefold()
    assert "api_key" not in serialized
    assert "https://" not in serialized


def test_standalone_and_composed_runs_emit_identical_artifact_contracts(tmp_path: Path):
    loaded = catalog()
    standalone_contracts: dict[str, set[tuple[str, str]]] = {}
    for capability_id in ("research-framing", "literature-intelligence", "novelty-audit"):
        project = tmp_path / f"standalone {capability_id}"
        project.mkdir()
        execution_request = request(
            TargetKind.CAPABILITY,
            capability_id,
            RunMode.INTERACTIVE,
            f"standalone-{capability_id}",
        )
        if capability_id == "novelty-audit":
            execution_request = execution_request.model_copy(
                update={"inputs": novelty_inputs(project)}
            )
        coordinator = RunCoordinator(project, loaded)
        context = coordinator.start(execution_request)
        coordinator.begin_target(context.run_id, capability_id)
        result = result_for(
            project, execution_request, context.run_id, loaded.capabilities[capability_id]
        )
        outcome = coordinator.complete_target(context.run_id, result)
        assert outcome.action is StopAction.PAUSE
        standalone_contracts[capability_id] = {
            (artifact.type, artifact.schema_version) for artifact in result.artifacts
        }

    project = tmp_path / "composed workflow 研究"
    project.mkdir()
    workflow_request = request(
        TargetKind.WORKFLOW,
        "idea-to-novelty",
        RunMode.AUTONOMOUS,
        "workflow-autonomous",
    )
    coordinator = RunCoordinator(project, loaded)
    context = coordinator.start(workflow_request)
    for capability_id in ("research-framing", "literature-intelligence", "novelty-audit"):
        coordinator.begin_target(context.run_id, capability_id)
        result = result_for(
            project, workflow_request, context.run_id, loaded.capabilities[capability_id]
        )
        outcome = coordinator.complete_target(context.run_id, result)
        assert {
            (item.type, item.schema_version) for item in result.artifacts
        } == standalone_contracts[capability_id]
    assert outcome.action is StopAction.COMPLETE
    assert len(list((project / ".research-os" / "checkpoints").glob("*.json"))) == 3


def test_checkpointed_fixture_stops_and_resumes_at_the_next_node(tmp_path: Path):
    project = tmp_path / "checkpointed workflow 研究"
    project.mkdir()
    loaded = catalog()
    execution_request = request(
        TargetKind.WORKFLOW,
        "idea-to-novelty",
        RunMode.CHECKPOINTED,
        "workflow-checkpointed",
    )
    coordinator = RunCoordinator(project, loaded)
    context = coordinator.start(execution_request)
    framing = loaded.capabilities["research-framing"]
    coordinator.begin_target(context.run_id, framing.id)
    paused = coordinator.complete_target(
        context.run_id,
        result_for(project, execution_request, context.run_id, framing),
    )

    assert paused.action is StopAction.PAUSE
    resumed = coordinator.resume(paused.checkpoint_id, ResumeDecision.CONTINUE)
    assert resumed.next_target_id == "literature-intelligence"
