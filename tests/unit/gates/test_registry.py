import pytest

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult
from research_skills_os.core.errors import DuplicateGate, UnknownGate
from research_skills_os.core.gates.protocol import GateContext
from research_skills_os.core.gates.registry import GateRegistry


class StaticGate:
    gate_version = "1.0"

    def __init__(self, gate_id: str) -> None:
        self.gate_id = gate_id

    def evaluate(self, context: GateContext) -> GateResult:
        return GateResult(
            gate_id=self.gate_id,
            gate_version=self.gate_version,
            status=GateStatus.PASS,
            severity=GateSeverity.INFO,
        )


def test_registry_returns_gates_in_deterministic_id_order():
    registry = GateRegistry()
    registry.register(StaticGate("z.last"))
    registry.register(StaticGate("a.first"))

    assert [gate.gate_id for gate in registry.all()] == ["a.first", "z.last"]


def test_registry_rejects_duplicate_gate_id():
    registry = GateRegistry([StaticGate("contract.valid")])

    with pytest.raises(DuplicateGate, match=r"contract\.valid"):
        registry.register(StaticGate("contract.valid"))


def test_registry_reports_unknown_gate_with_registered_ids():
    registry = GateRegistry([StaticGate("contract.valid")])

    with pytest.raises(UnknownGate, match=r"contract\.valid"):
        registry.get("missing.gate")
