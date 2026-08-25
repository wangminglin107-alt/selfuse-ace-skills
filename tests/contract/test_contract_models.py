from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from research_skills_os.core.contracts.enums import (
    GateSeverity,
    GateStatus,
    RunMode,
    RunStatus,
    TargetKind,
)
from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    Checkpoint,
    ExecutionRequest,
    ExecutionResult,
    GateResult,
    InputArtifactRef,
    RequestConstraints,
    TargetRef,
)

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
SHA256 = "a" * 64


def make_artifact(**overrides: object) -> ArtifactEnvelope:
    values: dict[str, object] = {
        "artifact_id": "brief-1",
        "type": "research_brief",
        "schema_version": "1.0",
        "producing_capability": "research-framing",
        "created_at": NOW,
        "path": "artifacts/research-framing/research-brief.md",
        "sha256": SHA256,
    }
    values.update(overrides)
    return ArtifactEnvelope.model_validate(values)


def test_accepts_standalone_capability_request_with_relative_input():
    request = ExecutionRequest.model_validate(
        {
            "request_id": "req-1",
            "project_id": "project-1",
            "target": {"kind": "capability", "id": "research-framing"},
            "mode": "interactive",
            "goal": "Frame an early research idea.",
            "inputs": [
                {
                    "artifact_id": "idea-1",
                    "type": "idea_memo",
                    "path_or_uri": "inputs/idea.md",
                }
            ],
            "constraints": {
                "language": "zh",
                "domain": "communication",
                "network": "deny",
            },
        }
    )

    assert request.target == TargetRef(kind=TargetKind.CAPABILITY, id="research-framing")
    assert request.mode is RunMode.INTERACTIVE
    assert request.inputs == [
        InputArtifactRef(artifact_id="idea-1", type="idea_memo", path_or_uri="inputs/idea.md")
    ]
    assert request.constraints == RequestConstraints(
        language="zh", domain="communication", network="deny"
    )


def test_accepts_workflow_request():
    request = ExecutionRequest.model_validate(
        {
            "request_id": "req-2",
            "project_id": "project-1",
            "target": {"kind": "workflow", "id": "idea-to-novelty"},
            "mode": "autonomous",
            "goal": "Assess whether the idea has defensible novelty.",
        }
    )

    assert request.target.kind is TargetKind.WORKFLOW
    assert request.mode is RunMode.AUTONOMOUS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_version", "2.0"),
        ("mode", "batch"),
        ("target", {"kind": "agent", "id": "research-framing"}),
    ],
)
def test_rejects_unsupported_contract_mode_or_target(field: str, value: object):
    data: dict[str, object] = {
        "request_id": "req-1",
        "project_id": "project-1",
        "target": {"kind": "capability", "id": "research-framing"},
        "mode": "interactive",
        "goal": "Frame an idea.",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        ExecutionRequest.model_validate(data)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.md",
        "inputs/../../outside.md",
        "/absolute/input.md",
        "C:\\research\\input.md",
        "\\\\server\\share\\input.md",
        "file:///C:/research/input.md",
    ],
)
def test_rejects_non_project_relative_input_paths(unsafe_path: str):
    with pytest.raises(ValidationError):
        InputArtifactRef(artifact_id="idea-1", type="idea_memo", path_or_uri=unsafe_path)


@pytest.mark.parametrize("status", list(RunStatus))
def test_accepts_each_run_status(status: RunStatus):
    result = ExecutionResult(
        request_id="req-1",
        run_id="run-1",
        target_id="research-framing",
        status=status,
    )

    assert result.status is status


def test_rejects_completed_result_with_blocking_gate_failure():
    blocking_failure = GateResult(
        gate_id="artifacts.integrity",
        gate_version="1.0",
        status=GateStatus.FAIL,
        severity=GateSeverity.BLOCKING,
        findings=["Artifact hash does not match."],
    )

    with pytest.raises(ValidationError, match="blocking gate"):
        ExecutionResult(
            request_id="req-1",
            run_id="run-1",
            target_id="research-framing",
            status=RunStatus.COMPLETED,
            gate_results=[blocking_failure],
        )


def test_rejects_completed_result_with_failed_gate_ids():
    with pytest.raises(ValidationError, match="failed_gates"):
        ExecutionResult(
            request_id="req-1",
            run_id="run-1",
            target_id="research-framing",
            status=RunStatus.COMPLETED,
            failed_gates=["inputs.required"],
        )


@pytest.mark.parametrize("invalid_hash", ["A" * 64, "a" * 63, "g" * 64, ""])
def test_rejects_noncanonical_artifact_hash(invalid_hash: str):
    with pytest.raises(ValidationError):
        make_artifact(sha256=invalid_hash)


def test_rejects_unknown_fields_in_contract_models():
    with pytest.raises(ValidationError):
        TargetRef.model_validate(
            {"kind": "capability", "id": "research-framing", "prompt": "hidden"}
        )


def test_checkpoint_requires_canonical_state_hash_and_utc_timestamp():
    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        project_id="project-1",
        run_id="run-1",
        completed_target="research-framing",
        artifacts_created=[make_artifact()],
        resume_from="literature-intelligence",
        state_hash="b" * 64,
        created_at=NOW,
    )

    assert checkpoint.created_at.tzinfo is UTC
    assert checkpoint.state_hash == "b" * 64


def test_rejects_naive_contract_timestamp():
    with pytest.raises(ValidationError, match="timezone"):
        make_artifact(created_at=datetime(2026, 8, 25, 12, 0))
