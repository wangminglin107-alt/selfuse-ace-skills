from dataclasses import dataclass, field

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult
from research_skills_os.core.gates.protocol import GateContext
from research_skills_os.core.gates.registry import GateRegistry
from research_skills_os.core.gates.runner import GatePolicy, GateRunner


@dataclass
class RecordingGate:
    gate_id: str
    status: GateStatus
    severity: GateSeverity
    record: list[str] = field(default_factory=list)
    gate_version: str = "1.0"

    def evaluate(self, context: GateContext) -> GateResult:
        self.record.append(self.gate_id)
        return GateResult(
            gate_id=self.gate_id,
            gate_version=self.gate_version,
            status=self.status,
            severity=self.severity,
            findings=[f"{self.gate_id} finding"] if self.status is GateStatus.FAIL else [],
        )


class ExplodingGate:
    gate_id = "gate.explodes"
    gate_version = "1.0"

    def evaluate(self, context: GateContext) -> GateResult:
        raise RuntimeError("secret local path and stack details")


def test_runner_evaluates_all_gates_in_deterministic_order_after_failure():
    record: list[str] = []
    registry = GateRegistry(
        [
            RecordingGate("z.warning", GateStatus.WARN, GateSeverity.ADVISORY, record),
            RecordingGate("a.failure", GateStatus.FAIL, GateSeverity.BLOCKING, record),
            RecordingGate("m.pass", GateStatus.PASS, GateSeverity.INFO, record),
        ]
    )

    summary = GateRunner(registry).run(["z.warning", "m.pass", "a.failure"], GateContext())

    assert record == ["a.failure", "m.pass", "z.warning"]
    assert [result.gate_id for result in summary.results] == record
    assert summary.blocked is True
    assert summary.failed_gate_ids == ["a.failure"]


def test_runner_converts_gate_exception_to_sanitized_blocking_result():
    summary = GateRunner(GateRegistry([ExplodingGate()])).run(["gate.explodes"], GateContext())

    result = summary.results[0]
    assert result.status is GateStatus.FAIL
    assert result.severity is GateSeverity.BLOCKING
    assert result.findings == ["Gate evaluation failed safely."]
    assert "secret" not in " ".join(result.findings + result.remediation)
    assert summary.blocked is True


def test_policy_does_not_block_advisory_failure_or_warning():
    policy = GatePolicy()
    advisory_failure = GateResult(
        gate_id="uncertainty.explicit",
        gate_version="1.0",
        status=GateStatus.FAIL,
        severity=GateSeverity.ADVISORY,
    )
    blocking_warning = GateResult(
        gate_id="provenance.complete",
        gate_version="1.0",
        status=GateStatus.WARN,
        severity=GateSeverity.BLOCKING,
    )

    assert policy.blocks(advisory_failure) is False
    assert policy.blocks(blocking_warning) is False
