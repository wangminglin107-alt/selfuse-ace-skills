"""Coordinate validated lifecycle transitions around externally produced scholarly work."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from research_skills_os.core.checkpoint.service import CheckpointService
from research_skills_os.core.contracts.enums import (
    GateSeverity,
    GateStatus,
    RunStatus,
)
from research_skills_os.core.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    GateResult,
)
from research_skills_os.core.errors import InvalidStateTransition
from research_skills_os.core.gates.builtin import builtin_gates
from research_skills_os.core.gates.protocol import GateContext
from research_skills_os.core.gates.registry import GateRegistry
from research_skills_os.core.gates.runner import GateRunner, GateRunSummary
from research_skills_os.core.orchestrator.stop_policy import (
    StopAction,
    StopPolicy,
    StopSignals,
)
from research_skills_os.core.orchestrator.transitions import RunLifecycle
from research_skills_os.core.registry.models import CapabilitySpec, RegistryCatalog, WorkflowSpec
from research_skills_os.core.router import Router
from research_skills_os.core.state.models import EventType, ProjectEvent, ProjectLifecycle
from research_skills_os.core.state.repository import StateRepository


class ResumeDecision(StrEnum):
    CONTINUE = "continue"
    ACCEPT_DRIFT = "accept_drift"
    RERUN = "rerun"


class RunContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    request_id: str
    project_id: str
    target_id: str
    mode: str
    lifecycle: RunLifecycle
    next_target_id: str | None = None


class TransitionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: StopAction
    status: RunStatus
    checkpoint_id: str | None = None
    gate_results: list[GateResult] = Field(default_factory=list)


def _new_run_id() -> str:
    return f"run-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"


def _write_json_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{content}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class RunCoordinator:
    def __init__(self, project_root: str | Path, catalog: RegistryCatalog) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.catalog = catalog
        self.router = Router(catalog)
        self.repository = StateRepository(self.project_root)
        self.checkpoints = CheckpointService(self.project_root, repository=self.repository)
        self.gates = GateRunner(GateRegistry(builtin_gates()))
        self.stop_policy = StopPolicy()

    def start(self, request: ExecutionRequest) -> RunContext:
        self.router.resolve(request.target)
        history = self.repository.event_log.read_all()
        if not history:
            self.repository.append(
                ProjectEvent(
                    event_id=f"project-event-{uuid4().hex}",
                    type=EventType.PROJECT_INITIALIZED,
                    payload={"project_id": request.project_id, "goal": request.goal},
                )
            )
        else:
            state = self.repository.load()
            if state.project_id != request.project_id:
                raise InvalidStateTransition("request project_id does not match project state")
            if state.lifecycle is not ProjectLifecycle.INITIALIZED:
                raise InvalidStateTransition("project already has an active or terminal run")

        run_id = _new_run_id()
        _write_json_atomic(self._request_path(run_id), request.model_dump(mode="json"))
        self.repository.append(
            ProjectEvent(
                event_id=f"run-start-{run_id}",
                type=EventType.RUN_STARTED,
                payload={"run_id": run_id},
            )
        )
        return self._context(run_id, request, RunLifecycle.RUNNING)

    def begin_target(self, run_id: str, target_id: str) -> RunContext:
        state = self.repository.load()
        if state.active_run_id != run_id or state.lifecycle is not ProjectLifecycle.RUNNING:
            raise InvalidStateTransition("target begin requires the active running run")
        request = self._load_request(run_id)
        self._resolve_allowed_capability(request, target_id)
        rerun = self._validate_workflow_boundary(request, target_id, state.completed_targets)
        if rerun:
            self.repository.append(
                ProjectEvent(
                    event_id=f"rerun-consumed-{uuid4().hex}",
                    type=EventType.DECISION_RECORDED,
                    payload={
                        "decision": {
                            "decision_id": f"rerun-consumed-{uuid4().hex}",
                            "description": f"Resume rerun consumed: {target_id}",
                            "made_by": "system",
                        }
                    },
                )
            )
        self.repository.append(
            ProjectEvent(
                event_id=f"target-start-{uuid4().hex}",
                type=EventType.TARGET_STARTED,
                payload={"target_id": target_id},
            )
        )
        return self._context(run_id, request, RunLifecycle.RUNNING)

    def complete_target(
        self,
        run_id: str,
        result: ExecutionResult,
        *,
        signals: StopSignals | None = None,
    ) -> TransitionOutcome:
        request = self._load_request(run_id)
        state = self.repository.load()
        if result.run_id != run_id or result.request_id != request.request_id:
            raise InvalidStateTransition("result does not belong to the active request/run")
        if state.active_run_id != run_id or state.active_target != result.target_id:
            raise InvalidStateTransition("result target is not the active target")
        spec = self._resolve_allowed_capability(request, result.target_id)
        present_outputs = {artifact.type for artifact in result.artifacts}
        missing_outputs = sorted(set(spec.output_types) - present_outputs)
        if missing_outputs:
            raise InvalidStateTransition(
                f"missing declared output types: {', '.join(missing_outputs)}"
            )

        for artifact in result.artifacts:
            self.repository.append(
                ProjectEvent(
                    event_id=f"artifact-event-{uuid4().hex}",
                    type=EventType.ARTIFACT_REGISTERED,
                    payload={"artifact": artifact.model_dump(mode="json")},
                )
            )
        for decision in result.decisions:
            self.repository.append(
                ProjectEvent(
                    event_id=f"decision-event-{uuid4().hex}",
                    type=EventType.DECISION_RECORDED,
                    payload={"decision": decision.model_dump(mode="json")},
                )
            )
        for uncertainty in result.uncertainties:
            self.repository.append(
                ProjectEvent(
                    event_id=f"uncertainty-event-{uuid4().hex}",
                    type=EventType.UNCERTAINTY_RECORDED,
                    payload={"uncertainty": uncertainty.model_dump(mode="json")},
                )
            )

        requested = self.router.resolve(request.target)
        gate_ids = list(spec.exit_gates)
        if isinstance(requested, WorkflowSpec):
            gate_ids.extend(requested.global_gates)
        gate_summary = self._run_combined_gates(
            gate_ids,
            GateContext(
                request=request,
                result=result,
                material_uncertainty_detected=any(item.material for item in result.uncertainties),
            ),
            result.gate_results,
        )
        for gate_result in gate_summary.results:
            self.repository.append(
                ProjectEvent(
                    event_id=f"gate-event-{uuid4().hex}",
                    type=EventType.GATE_RECORDED,
                    payload={"gate_result": gate_result.model_dump(mode="json")},
                )
            )
        if gate_summary.blocked:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-blocked-{uuid4().hex}",
                    type=EventType.RUN_BLOCKED,
                    payload={"run_id": run_id},
                )
            )
            return TransitionOutcome(
                action=StopAction.BLOCK,
                status=RunStatus.BLOCKED,
                gate_results=gate_summary.results,
            )

        self.repository.append(
            ProjectEvent(
                event_id=f"target-complete-{uuid4().hex}",
                type=EventType.TARGET_COMPLETED,
                payload={"target_id": result.target_id},
            )
        )
        effective_signals = signals or self._stop_signals(
            request,
            result.target_id,
            material_uncertainty=any(item.material for item in result.uncertainties),
        )
        action = self.stop_policy.decide(request.mode, effective_signals)
        if action is StopAction.BLOCK:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-blocked-{uuid4().hex}",
                    type=EventType.RUN_BLOCKED,
                    payload={"run_id": run_id},
                )
            )
            return TransitionOutcome(
                action=action,
                status=RunStatus.BLOCKED,
                gate_results=gate_summary.results,
            )
        if action is StopAction.PAUSE:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-paused-{uuid4().hex}",
                    type=EventType.RUN_PAUSED,
                    payload={"run_id": run_id},
                )
            )

        checkpoint = self.checkpoints.create(self.repository.load(), result.target_id)
        if action is StopAction.COMPLETE:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-completed-{uuid4().hex}",
                    type=EventType.RUN_COMPLETED,
                    payload={"run_id": run_id},
                )
            )
        status = {
            StopAction.CONTINUE: RunStatus.COMPLETED,
            StopAction.PAUSE: RunStatus.PAUSED,
            StopAction.COMPLETE: RunStatus.COMPLETED,
        }[action]
        return TransitionOutcome(
            action=action,
            status=status,
            checkpoint_id=checkpoint.checkpoint_id,
            gate_results=gate_summary.results,
        )

    def resume(self, resume_token: str, decision: ResumeDecision) -> RunContext:
        verification = self.checkpoints.verify_resume(resume_token)
        if verification.status == "drifted" and decision not in {
            ResumeDecision.ACCEPT_DRIFT,
            ResumeDecision.RERUN,
        }:
            raise InvalidStateTransition("resume drift requires explicit acceptance or rerun")
        checkpoint = self.checkpoints.load(resume_token)
        state = self.repository.load()
        if state.lifecycle not in {ProjectLifecycle.PAUSED, ProjectLifecycle.BLOCKED}:
            raise InvalidStateTransition("only paused or blocked runs can resume")
        if state.lifecycle is ProjectLifecycle.BLOCKED or decision in {
            ResumeDecision.ACCEPT_DRIFT,
            ResumeDecision.RERUN,
        }:
            self.repository.append(
                ProjectEvent(
                    event_id=f"resume-decision-{uuid4().hex}",
                    type=EventType.DECISION_RECORDED,
                    payload={
                        "decision": {
                            "decision_id": f"resume-{uuid4().hex}",
                            "description": f"Resume decision: {decision.value}",
                            "made_by": "user",
                        }
                    },
                )
            )
        self.repository.append(
            ProjectEvent(
                event_id=f"run-resume-{uuid4().hex}",
                type=EventType.RUN_STARTED,
                payload={"run_id": checkpoint.run_id},
            )
        )
        request = self._load_request(checkpoint.run_id)
        next_target_id = (
            checkpoint.completed_target
            if decision is ResumeDecision.RERUN
            else self._next_workflow_target(request, self.repository.load().completed_targets)
        )
        return self._context(
            checkpoint.run_id,
            request,
            RunLifecycle.RUNNING,
            next_target_id=next_target_id,
        )

    def fail(self, run_id: str, reason: str) -> None:
        state = self.repository.load()
        if state.active_run_id != run_id:
            raise InvalidStateTransition("failure does not match the active run")
        self.repository.append(
            ProjectEvent(
                event_id=f"run-failed-{uuid4().hex}",
                type=EventType.RUN_FAILED,
                payload={"run_id": run_id, "reason": reason},
            )
        )

    def _resolve_allowed_capability(
        self, request: ExecutionRequest, capability_id: str
    ) -> CapabilitySpec:
        candidate = self.catalog.capabilities.get(capability_id)
        if candidate is None:
            raise InvalidStateTransition(f"capability is not registered: {capability_id}")
        requested = self.router.resolve(request.target)
        if isinstance(requested, CapabilitySpec) and requested.id != capability_id:
            raise InvalidStateTransition("capability does not match standalone request target")
        if isinstance(requested, WorkflowSpec) and capability_id not in {
            node.capability_id for node in requested.nodes
        }:
            raise InvalidStateTransition("capability is not a node in the requested workflow")
        return candidate

    def _validate_workflow_boundary(
        self,
        request: ExecutionRequest,
        capability_id: str,
        completed_targets: list[str],
    ) -> bool:
        requested = self.router.resolve(request.target)
        if not isinstance(requested, WorkflowSpec):
            return False
        nodes = {node.capability_id: node for node in requested.nodes}
        node = nodes[capability_id]
        rerun = self._rerun_is_authorized(capability_id)
        if capability_id in completed_targets and not rerun:
            raise InvalidStateTransition(
                f"workflow capability is already completed: {capability_id}"
            )
        predecessors = {
            next(item.capability_id for item in requested.nodes if item.id == edge.from_node)
            for edge in requested.edges
            if edge.to_node == node.id
        }
        missing_predecessors = sorted(predecessors - set(completed_targets))
        if missing_predecessors:
            raise InvalidStateTransition(
                "workflow predecessors are incomplete: " + ", ".join(missing_predecessors)
            )
        if not predecessors and node.id != requested.entry_node:
            raise InvalidStateTransition("workflow must begin at its declared entry node")
        required_types = {
            artifact_type
            for mapping in requested.artifact_mappings
            if mapping.to_node == node.id
            for artifact_type in mapping.artifact_types
        }
        present_types = {artifact.type for artifact in self.repository.load().artifacts.values()}
        missing_types = sorted(required_types - present_types)
        if missing_types:
            raise InvalidStateTransition(
                "workflow artifact mappings are unsatisfied: " + ", ".join(missing_types)
            )
        return rerun

    def _rerun_is_authorized(self, capability_id: str) -> bool:
        state = self.repository.load()
        if not state.decisions or state.decisions[-1].description != "Resume decision: rerun":
            return False
        checkpoint = self.checkpoints.current()
        return checkpoint is not None and checkpoint.completed_target == capability_id

    def _run_combined_gates(
        self,
        gate_ids: list[str],
        context: GateContext,
        supplied_results: list[GateResult],
    ) -> GateRunSummary:
        builtin_ids = [gate_id for gate_id in gate_ids if self.gates.registry.contains(gate_id)]
        custom_ids = sorted(set(gate_ids) - set(builtin_ids))
        builtin_summary = self.gates.run(builtin_ids, context)
        supplied_by_id: dict[str, list[GateResult]] = {}
        for item in supplied_results:
            supplied_by_id.setdefault(item.gate_id, []).append(item)
        custom_results: list[GateResult] = []
        for gate_id in custom_ids:
            matches = supplied_by_id.get(gate_id, [])
            if len(matches) == 1:
                custom_results.append(matches[0])
            else:
                custom_results.append(
                    GateResult(
                        gate_id=gate_id,
                        gate_version="1.0",
                        status=GateStatus.FAIL,
                        severity=GateSeverity.BLOCKING,
                        findings=["Required capability gate result is missing or duplicated."],
                        remediation=["Run the capability gate evaluator and resubmit the result."],
                    )
                )
        results = sorted([*builtin_summary.results, *custom_results], key=lambda item: item.gate_id)
        return GateRunSummary(
            results=results,
            failed_gate_ids=[item.gate_id for item in results if item.status is GateStatus.FAIL],
            blocked=any(self.gates.policy.blocks(item) for item in results),
        )

    def _stop_signals(
        self,
        request: ExecutionRequest,
        capability_id: str,
        *,
        material_uncertainty: bool,
    ) -> StopSignals:
        requested = self.router.resolve(request.target)
        if isinstance(requested, CapabilitySpec):
            return StopSignals(is_terminal=True, material_uncertainty=material_uncertainty)
        node = next(node for node in requested.nodes if node.capability_id == capability_id)
        return StopSignals(
            is_terminal=node.id in requested.terminal_nodes,
            human_review=(node.human_review or node.id in requested.mode_stops.checkpointed_nodes),
            material_uncertainty=material_uncertainty,
        )

    def _next_workflow_target(
        self, request: ExecutionRequest, completed_targets: list[str]
    ) -> str | None:
        requested = self.router.resolve(request.target)
        if not isinstance(requested, WorkflowSpec):
            return None
        completed = set(completed_targets)
        for node in requested.nodes:
            if node.capability_id in completed:
                continue
            predecessors = {
                next(item.capability_id for item in requested.nodes if item.id == edge.from_node)
                for edge in requested.edges
                if edge.to_node == node.id
            }
            if predecessors <= completed:
                return node.capability_id
        return None

    def _request_path(self, run_id: str) -> Path:
        return self.project_root / ".research-os" / "runs" / run_id / "request.json"

    def _load_request(self, run_id: str) -> ExecutionRequest:
        path = self._request_path(run_id)
        if not path.is_file():
            raise InvalidStateTransition(f"run request is missing: {run_id}")
        return ExecutionRequest.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _context(
        run_id: str,
        request: ExecutionRequest,
        lifecycle: RunLifecycle,
        *,
        next_target_id: str | None = None,
    ) -> RunContext:
        return RunContext(
            run_id=run_id,
            request_id=request.request_id,
            project_id=request.project_id,
            target_id=request.target.id,
            mode=request.mode.value,
            lifecycle=lifecycle,
            next_target_id=next_target_id,
        )
