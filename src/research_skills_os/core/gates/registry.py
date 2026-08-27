"""Deterministic registry for named gate implementations."""

from __future__ import annotations

from collections.abc import Iterable

from research_skills_os.core.errors import DuplicateGate, UnknownGate
from research_skills_os.core.gates.protocol import Gate


class GateRegistry:
    def __init__(self, gates: Iterable[Gate] = ()) -> None:
        self._gates: dict[str, Gate] = {}
        for gate in gates:
            self.register(gate)

    def register(self, gate: Gate) -> None:
        if gate.gate_id in self._gates:
            raise DuplicateGate(f"gate is already registered: {gate.gate_id}")
        self._gates[gate.gate_id] = gate

    def get(self, gate_id: str) -> Gate:
        try:
            return self._gates[gate_id]
        except KeyError as exc:
            registered = ", ".join(sorted(self._gates)) or "<none>"
            raise UnknownGate(f"unknown gate {gate_id}; registered gates: {registered}") from exc

    def contains(self, gate_id: str) -> bool:
        return gate_id in self._gates

    def all(self) -> list[Gate]:
        return [self._gates[gate_id] for gate_id in sorted(self._gates)]
