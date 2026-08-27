"""Run every requested gate and aggregate structured blocking outcomes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult
from research_skills_os.core.gates.protocol import GateContext
from research_skills_os.core.gates.registry import GateRegistry


class GateRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    results: list[GateResult] = Field(default_factory=list)
    failed_gate_ids: list[str] = Field(default_factory=list)
    blocked: bool = False


class GatePolicy:
    def blocks(self, result: GateResult) -> bool:
        return result.status is GateStatus.FAIL and result.severity is GateSeverity.BLOCKING


class GateRunner:
    def __init__(self, registry: GateRegistry, *, policy: GatePolicy | None = None) -> None:
        self.registry = registry
        self.policy = policy or GatePolicy()

    def run(self, gate_ids: list[str], context: GateContext) -> GateRunSummary:
        results: list[GateResult] = []
        for gate_id in sorted(set(gate_ids)):
            gate = self.registry.get(gate_id)
            try:
                result = gate.evaluate(context)
            except Exception:
                result = GateResult(
                    gate_id=gate.gate_id,
                    gate_version=gate.gate_version,
                    status=GateStatus.FAIL,
                    severity=GateSeverity.BLOCKING,
                    findings=["Gate evaluation failed safely."],
                    remediation=["Review the gate implementation and rerun."],
                )
            results.append(result)

        return GateRunSummary(
            results=results,
            failed_gate_ids=[
                result.gate_id for result in results if result.status is GateStatus.FAIL
            ],
            blocked=any(self.policy.blocks(result) for result in results),
        )
