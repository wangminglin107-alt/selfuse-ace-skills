from datetime import UTC, datetime

import pytest

from research_skills_os.core.artifacts.store import ArtifactVerification
from research_skills_os.core.checkpoint.service import ResumeVerification
from research_skills_os.core.contracts.enums import GateStatus, RunMode, RunStatus, TargetKind
from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    ExecutionRequest,
    ExecutionResult,
    InputArtifactRef,
    RequestConstraints,
    TargetRef,
    UncertaintyRecord,
)
from research_skills_os.core.gates.builtin import builtin_gates
from research_skills_os.core.gates.protocol import GateContext, ProviderUse

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def request(
    *, network: str = "deny", inputs: list[InputArtifactRef] | None = None
) -> ExecutionRequest:
    return ExecutionRequest(
        request_id="req-1",
        project_id="project-1",
        target=TargetRef(kind=TargetKind.CAPABILITY, id="research-framing"),
        mode=RunMode.INTERACTIVE,
        goal="Frame idea",
        inputs=inputs or [],
        constraints=RequestConstraints(network=network),
    )


def artifact(*, provenance: list[str] | None = None) -> ArtifactEnvelope:
    return ArtifactEnvelope(
        artifact_id="brief-1",
        type="research_brief",
        schema_version="1.0",
        producing_capability="research-framing",
        created_at=NOW,
        path="artifacts/brief.md",
        sha256="a" * 64,
        provenance_references=provenance or [],
    )


def result(
    *,
    artifacts: list[ArtifactEnvelope] | None = None,
    uncertainties: list[UncertaintyRecord] | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        request_id="req-1",
        run_id="run-1",
        target_id="research-framing",
        status=RunStatus.COMPLETED_WITH_UNCERTAINTY,
        artifacts=artifacts or [],
        uncertainties=uncertainties or [],
    )


@pytest.fixture
def gates():
    return {gate.gate_id: gate for gate in builtin_gates()}


def test_contract_gate_fails_without_validated_request(gates):
    outcome = gates["contract.valid"].evaluate(GateContext())

    assert outcome.status is GateStatus.FAIL
    assert outcome.severity.value == "blocking"


def test_required_inputs_gate_lists_missing_types(gates):
    outcome = gates["inputs.required"].evaluate(
        GateContext(request=request(), required_input_types=frozenset({"idea_memo"}))
    )

    assert outcome.status is GateStatus.FAIL
    assert "idea_memo" in outcome.findings[0]


def test_required_inputs_gate_passes_when_declared_type_is_present(gates):
    input_ref = InputArtifactRef(
        artifact_id="idea-1", type="idea_memo", path_or_uri="inputs/idea.md"
    )

    outcome = gates["inputs.required"].evaluate(
        GateContext(
            request=request(inputs=[input_ref]),
            required_input_types=frozenset({"idea_memo"}),
        )
    )

    assert outcome.status is GateStatus.PASS


def test_artifact_integrity_gate_blocks_drift(gates):
    verification = ArtifactVerification(
        artifact_id="brief-1",
        path="artifacts/brief.md",
        status="drifted",
        expected_sha256="a" * 64,
        actual_sha256="b" * 64,
    )

    outcome = gates["artifacts.integrity"].evaluate(
        GateContext(artifact_verifications=(verification,))
    )

    assert outcome.status is GateStatus.FAIL
    assert "brief-1" in outcome.findings[0]


def test_provenance_gate_rejects_output_without_source_trace(gates):
    outcome = gates["provenance.complete"].evaluate(
        GateContext(result=result(artifacts=[artifact()]))
    )

    assert outcome.status is GateStatus.FAIL
    assert "brief-1" in outcome.findings[0]


def test_uncertainty_gate_warns_when_material_uncertainty_is_hidden(gates):
    outcome = gates["uncertainty.explicit"].evaluate(
        GateContext(result=result(), material_uncertainty_detected=True)
    )

    assert outcome.status is GateStatus.WARN
    assert outcome.severity.value == "advisory"


def test_uncertainty_gate_passes_when_material_uncertainty_is_recorded(gates):
    uncertainty = UncertaintyRecord(
        uncertainty_id="uncertainty-1",
        description="Geographic scope is unresolved.",
        material=True,
    )

    outcome = gates["uncertainty.explicit"].evaluate(
        GateContext(
            result=result(uncertainties=[uncertainty]),
            material_uncertainty_detected=True,
        )
    )

    assert outcome.status is GateStatus.PASS


def test_checkpoint_gate_blocks_drifted_resume(gates):
    resume = ResumeVerification(
        checkpoint_id="checkpoint-1",
        status="drifted",
        state_matches=False,
        reasons=["project state changed after the checkpoint"],
    )

    outcome = gates["checkpoint.consistent"].evaluate(GateContext(resume_verification=resume))

    assert outcome.status is GateStatus.FAIL
    assert "project state" in outcome.findings[0]


@pytest.mark.parametrize(
    "provider_use",
    [
        ProviderUse(provider_id="qinyan", network=True, declared=True),
        ProviderUse(provider_id="unknown", network=False, declared=False),
    ],
)
def test_provider_gate_blocks_denied_network_or_undeclared_provider(gates, provider_use):
    outcome = gates["provider.policy"].evaluate(
        GateContext(request=request(network="deny"), provider_uses=(provider_use,))
    )

    assert outcome.status is GateStatus.FAIL
    assert provider_use.provider_id in outcome.findings[0]
