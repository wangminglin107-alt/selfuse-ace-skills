from pathlib import Path

import pytest

from research_skills_os.core.contracts.enums import GateStatus, RunMode, TargetKind
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    InputArtifactRef,
    TargetRef,
)
from research_skills_os.core.errors import ResearchSkillsError
from research_skills_os.core.orchestrator.coordinator import RunCoordinator
from research_skills_os.core.registry.loader import RegistryLoader
from research_skills_os.core.state.models import ProjectLifecycle

ROOT = Path(__file__).parents[2]


def catalog():
    return RegistryLoader(
        capability_roots=[ROOT / "src" / "research_skills_os" / "capabilities"],
        workflow_roots=[ROOT / "src" / "research_skills_os" / "workflows"],
    ).load()


def test_novelty_audit_entry_gate_blocks_missing_research_and_literature_inputs(
    tmp_path: Path,
):
    coordinator = RunCoordinator(tmp_path, catalog())
    request = ExecutionRequest(
        request_id="request-1",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="novelty-audit"),
        mode=RunMode.INTERACTIVE,
        goal="Audit novelty",
    )
    context = coordinator.start(request)

    with pytest.raises(ResearchSkillsError, match="entry gates blocked"):
        coordinator.begin_target(context.run_id, "novelty-audit")

    state = coordinator.repository.load()
    required = next(item for item in state.gate_results if item.gate_id == "inputs.required")
    assert required.status is GateStatus.FAIL
    assert state.lifecycle is ProjectLifecycle.BLOCKED
    assert state.active_target is None


def test_novelty_audit_entry_gate_rejects_claimed_but_nonexistent_inputs(tmp_path: Path):
    coordinator = RunCoordinator(tmp_path, catalog())
    required_types = (
        "research_brief_metadata",
        "search_ledger",
        "source_registry",
        "evidence_map",
    )
    request = ExecutionRequest(
        request_id="request-1",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="novelty-audit"),
        mode=RunMode.INTERACTIVE,
        goal="Audit novelty",
        inputs=[
            InputArtifactRef(
                artifact_id=f"input-{artifact_type}",
                type=artifact_type,
                path_or_uri=f"inputs/{artifact_type}.yaml",
            )
            for artifact_type in required_types
        ],
    )
    context = coordinator.start(request)

    with pytest.raises(ResearchSkillsError, match="entry gates blocked"):
        coordinator.begin_target(context.run_id, "novelty-audit")

    state = coordinator.repository.load()
    integrity = next(item for item in state.gate_results if item.gate_id == "artifacts.integrity")
    assert integrity.status is GateStatus.FAIL
    assert state.artifacts == {}


def test_new_request_can_replace_blocked_run_after_missing_inputs_are_supplied(
    tmp_path: Path,
):
    coordinator = RunCoordinator(tmp_path, catalog())
    blocked_request = ExecutionRequest(
        request_id="request-blocked",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="novelty-audit"),
        mode=RunMode.INTERACTIVE,
        goal="Audit novelty",
    )
    blocked = coordinator.start(blocked_request)
    with pytest.raises(ResearchSkillsError, match="entry gates blocked"):
        coordinator.begin_target(blocked.run_id, "novelty-audit")

    required_types = (
        "research_brief_metadata",
        "search_ledger",
        "source_registry",
        "evidence_map",
    )
    inputs = []
    for artifact_type in required_types:
        relative = f"inputs/{artifact_type}.yaml"
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8", newline="\n")
        inputs.append(
            InputArtifactRef(
                artifact_id=f"input-{artifact_type}",
                type=artifact_type,
                path_or_uri=relative,
            )
        )
    replacement_request = blocked_request.model_copy(
        update={"request_id": "request-replacement", "inputs": inputs}
    )

    replacement = coordinator.start(replacement_request)
    coordinator.begin_target(replacement.run_id, "novelty-audit")

    state = coordinator.repository.load()
    assert replacement.run_id != blocked.run_id
    assert state.active_run_id == replacement.run_id
    assert state.active_target == "novelty-audit"
