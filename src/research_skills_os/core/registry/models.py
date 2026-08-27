"""Declarative specification models with a hard capability/workflow boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CapabilitySpec(SpecModel):
    spec_version: Literal["1.0"] = "1.0"
    kind: Literal["capability"] = "capability"
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    entry_gates: list[str] = Field(default_factory=list)
    exit_gates: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    resumable: bool = True
    network: Literal["none", "optional", "required"] = "none"
    side_effects: list[str] = Field(default_factory=list)


class WorkflowNode(SpecModel):
    id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    checkpoint: bool = True
    human_review: bool = False
    autonomous_review: bool = False


class WorkflowEdge(SpecModel):
    from_node: str = Field(alias="from", min_length=1)
    to_node: str = Field(alias="to", min_length=1)
    condition: str | None = None


class ArtifactMapping(SpecModel):
    from_node: str = Field(min_length=1)
    artifact_types: list[str] = Field(min_length=1)
    to_node: str = Field(min_length=1)


class ModeStops(SpecModel):
    interactive_after_each: bool = True
    checkpointed_nodes: list[str] = Field(default_factory=list)
    autonomous_terminal_only: bool = True


class WorkflowSpec(SpecModel):
    spec_version: Literal["1.0"] = "1.0"
    kind: Literal["workflow"] = "workflow"
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    entry_node: str = Field(min_length=1)
    terminal_nodes: list[str] = Field(min_length=1)
    nodes: list[WorkflowNode] = Field(min_length=1)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    artifact_mappings: list[ArtifactMapping] = Field(default_factory=list)
    global_gates: list[str] = Field(default_factory=list)
    mode_stops: ModeStops = Field(default_factory=ModeStops)

    @model_validator(mode="after")
    def validate_graph(self) -> WorkflowSpec:
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("workflow node ids must be unique")
        known = set(node_ids)
        if self.entry_node not in known:
            raise ValueError(f"unknown entry node: {self.entry_node}")
        unknown_terminals = sorted(set(self.terminal_nodes) - known)
        if unknown_terminals:
            raise ValueError(f"unknown terminal nodes: {', '.join(unknown_terminals)}")
        for edge in self.edges:
            if edge.from_node not in known or edge.to_node not in known:
                raise ValueError(
                    f"workflow edge references unknown node: {edge.from_node} -> {edge.to_node}"
                )
        for mapping in self.artifact_mappings:
            if mapping.from_node not in known or mapping.to_node not in known:
                raise ValueError(
                    "workflow artifact mapping references unknown node: "
                    f"{mapping.from_node} -> {mapping.to_node}"
                )
        if _contains_cycle(known, self.edges):
            raise ValueError("workflow graph contains a cycle; V1 workflows must be acyclic")
        invalid_review = sorted(
            node.id for node in self.nodes if node.autonomous_review and not node.human_review
        )
        if invalid_review:
            raise ValueError(
                "autonomous_review requires human_review on nodes: " + ", ".join(invalid_review)
            )
        outgoing = _adjacency(known, self.edges)
        terminal_outgoing = sorted(
            terminal for terminal in self.terminal_nodes if outgoing[terminal]
        )
        if terminal_outgoing:
            raise ValueError(
                "terminal nodes cannot have outgoing edges: " + ", ".join(terminal_outgoing)
            )
        reachable = _reachable_from(self.entry_node, outgoing)
        unreachable = sorted(known - reachable)
        if unreachable:
            raise ValueError("unreachable workflow nodes: " + ", ".join(unreachable))
        can_reach_terminal = _nodes_reaching(set(self.terminal_nodes), known, self.edges)
        stranded = sorted(known - can_reach_terminal)
        if stranded:
            raise ValueError("workflow nodes cannot reach a terminal: " + ", ".join(stranded))
        return self


def _contains_cycle(node_ids: set[str], edges: list[WorkflowEdge]) -> bool:
    outgoing = _adjacency(node_ids, edges)
    indegree = dict.fromkeys(node_ids, 0)
    for edge in edges:
        indegree[edge.to_node] += 1
    ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        node_id = ready.pop(0)
        visited += 1
        for target in sorted(outgoing[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    return visited != len(node_ids)


def _adjacency(node_ids: set[str], edges: list[WorkflowEdge]) -> dict[str, list[str]]:
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        outgoing[edge.from_node].append(edge.to_node)
    return outgoing


def _reachable_from(start: str, outgoing: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    ready = [start]
    while ready:
        node = ready.pop()
        if node in seen:
            continue
        seen.add(node)
        ready.extend(outgoing[node])
    return seen


def _nodes_reaching(targets: set[str], node_ids: set[str], edges: list[WorkflowEdge]) -> set[str]:
    incoming: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        incoming[edge.to_node].append(edge.from_node)
    seen: set[str] = set()
    ready = list(targets)
    while ready:
        node = ready.pop()
        if node in seen:
            continue
        seen.add(node)
        ready.extend(incoming[node])
    return seen


class RegistryCatalog(SpecModel):
    capabilities: dict[str, CapabilitySpec] = Field(default_factory=dict)
    workflows: dict[str, WorkflowSpec] = Field(default_factory=dict)
