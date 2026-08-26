"""Coordinate validated lifecycle transitions around externally produced scholarly work."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import Concatenate, cast
from urllib.parse import urlsplit
from uuid import uuid4

from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field

from research_skills_os.capabilities.gate_evaluators import evaluate_capability_artifacts
from research_skills_os.core.artifacts.store import ArtifactStore, ArtifactVerification
from research_skills_os.core.checkpoint.service import CheckpointService, ResumeArtifactStatus
from research_skills_os.core.contracts.enums import (
    GateSeverity,
    GateStatus,
    RunStatus,
)
from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    Checkpoint,
    ExecutionRequest,
    ExecutionResult,
    GateResult,
    InputArtifactRef,
)
from research_skills_os.core.errors import (
    ArtifactNotFound,
    BlockedGateError,
    CheckpointIntegrityError,
    InvalidStateTransition,
)
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
from research_skills_os.core.state.models import (
    EventType,
    ProjectEvent,
    ProjectLifecycle,
    ProjectState,
)
from research_skills_os.core.state.repository import StateRepository


def _operation_locked[**Parameters, ReturnValue](
    method: Callable[Concatenate[RunCoordinator, Parameters], ReturnValue],
) -> Callable[Concatenate[RunCoordinator, Parameters], ReturnValue]:
    @wraps(method)
    def locked(
        self: RunCoordinator, *args: Parameters.args, **kwargs: Parameters.kwargs
    ) -> ReturnValue:
        with self.operation_lock:
            return method(self, *args, **kwargs)

    return cast(
        "Callable[Concatenate[RunCoordinator, Parameters], ReturnValue]",
        locked,
    )


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
        operation_directory = self.project_root / ".research-os"
        operation_directory.mkdir(parents=True, exist_ok=True)
        self.operation_lock = FileLock(operation_directory / "operation.lock", timeout=10)
        self.catalog = catalog
        self.router = Router(catalog)
        self.repository = StateRepository(self.project_root)
        self.checkpoints = CheckpointService(self.project_root, repository=self.repository)
        self.gates = GateRunner(GateRegistry(builtin_gates()))
        self.stop_policy = StopPolicy()

    @_operation_locked
    def start(self, request: ExecutionRequest) -> RunContext:
        self.router.resolve(request.target)
        history = self.repository.event_log.read_all()
        replacing_blocked_run = False
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
            if state.lifecycle not in {
                ProjectLifecycle.INITIALIZED,
                ProjectLifecycle.BLOCKED,
                ProjectLifecycle.COMPLETED,
                ProjectLifecycle.FAILED,
            }:
                raise InvalidStateTransition("project already has an active or resumable run")
            replacing_blocked_run = state.lifecycle is ProjectLifecycle.BLOCKED

        run_id = _new_run_id()
        _write_json_atomic(self._request_path(run_id), request.model_dump(mode="json"))
        self.repository.append(
            ProjectEvent(
                event_id=f"run-start-{run_id}",
                type=EventType.RUN_STARTED,
                payload={
                    "run_id": run_id,
                    "goal": request.goal,
                    "replace_blocked": replacing_blocked_run,
                },
            )
        )
        return self._context(run_id, request, RunLifecycle.RUNNING)

    @_operation_locked
    def begin_target(self, run_id: str, target_id: str) -> RunContext:
        state = self.repository.load()
        if state.active_run_id != run_id:
            raise InvalidStateTransition("target begin requires the active running run")
        retrying_blocked_target = state.lifecycle is ProjectLifecycle.BLOCKED
        self._enforce_current_checkpoint(
            run_id,
            allow_state_only_drift=retrying_blocked_target,
        )
        if retrying_blocked_target:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-retry-{uuid4().hex}",
                    type=EventType.RUN_STARTED,
                    payload={"run_id": run_id},
                )
            )
            state = self.repository.load()
        elif state.lifecycle is not ProjectLifecycle.RUNNING:
            raise InvalidStateTransition("target begin requires the active running run")
        request = self._load_request(run_id)
        spec = self._resolve_allowed_capability(request, target_id)
        rerun = self._validate_workflow_boundary(request, target_id, state.completed_targets)
        entry_request = self._request_with_available_inputs(request, target_id, state)
        input_verifications, pending_inputs = self._prepare_entry_inputs(entry_request, state)
        entry_summary = self.gates.run(
            [*spec.entry_gates, "artifacts.integrity"],
            GateContext(
                request=entry_request,
                required_input_types=frozenset(spec.input_types),
                artifact_verifications=tuple(input_verifications),
            ),
        )
        for gate_result in entry_summary.results:
            self.repository.append(
                ProjectEvent(
                    event_id=f"gate-event-{uuid4().hex}",
                    type=EventType.GATE_RECORDED,
                    payload={"gate_result": gate_result.model_dump(mode="json")},
                )
            )
        if entry_summary.blocked:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-blocked-{uuid4().hex}",
                    type=EventType.RUN_BLOCKED,
                    payload={"run_id": run_id},
                )
            )
            failed_results = [
                result
                for result in entry_summary.results
                if result.gate_id in entry_summary.failed_gate_ids
            ]
            raise BlockedGateError(
                entry_summary.failed_gate_ids,
                findings=[finding for result in failed_results for finding in result.findings],
                remediation=[action for result in failed_results for action in result.remediation],
            )
        for artifact in pending_inputs:
            self.repository.append(
                ProjectEvent(
                    event_id=f"artifact-event-{uuid4().hex}",
                    type=EventType.ARTIFACT_REGISTERED,
                    payload={"artifact": artifact.model_dump(mode="json")},
                )
            )
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
                payload={
                    "target_id": target_id,
                    "input_artifact_ids": [
                        input_ref.artifact_id for input_ref in entry_request.inputs
                    ],
                },
            )
        )
        return self._context(run_id, request, RunLifecycle.RUNNING)

    @_operation_locked
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
        if result.status not in {
            RunStatus.COMPLETED,
            RunStatus.COMPLETED_WITH_UNCERTAINTY,
        }:
            raise InvalidStateTransition("target completion requires a completed result status")
        spec = self._resolve_allowed_capability(request, result.target_id)
        present_outputs = {artifact.type for artifact in result.artifacts}
        missing_outputs = sorted(set(spec.output_types) - present_outputs)
        if missing_outputs:
            raise InvalidStateTransition(
                f"missing declared output types: {', '.join(missing_outputs)}"
            )
        unexpected_outputs = sorted(present_outputs - set(spec.output_types))
        if unexpected_outputs:
            raise InvalidStateTransition(
                f"undeclared output types: {', '.join(unexpected_outputs)}"
            )
        for artifact in result.artifacts:
            if artifact.producing_capability != spec.id:
                raise InvalidStateTransition(
                    f"artifact producer does not match target: {artifact.artifact_id}"
                )
            if artifact.schema_version != "1.0":
                raise InvalidStateTransition(
                    f"unsupported artifact schema version: {artifact.artifact_id}"
                )

        artifact_verifications = self._verify_artifacts(result.artifacts)
        scholarly_results = evaluate_capability_artifacts(
            spec.id, self.project_root, result.artifacts
        )

        requested = self.router.resolve(request.target)
        gate_ids = [*spec.exit_gates, "artifacts.integrity", "provider.policy"]
        if isinstance(requested, WorkflowSpec):
            gate_ids.extend(requested.global_gates)
        gate_summary = self._run_combined_gates(
            gate_ids,
            GateContext(
                request=request,
                result=result,
                artifact_verifications=tuple(artifact_verifications),
                material_uncertainty_detected=any(item.material for item in result.uncertainties),
            ),
            scholarly_results,
        )
        for gate_result in gate_summary.results:
            self.repository.append(
                ProjectEvent(
                    event_id=f"gate-event-{uuid4().hex}",
                    type=EventType.GATE_RECORDED,
                    payload={"gate_result": gate_result.model_dump(mode="json")},
                )
            )
        artifacts_trusted = all(
            verification.status == "verified" for verification in artifact_verifications
        )
        if artifacts_trusted:
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

        checkpoint = self.checkpoints.create(
            self.repository.load(),
            result.target_id,
            inputs_used=state.active_input_artifact_ids,
            artifacts_created=result.artifacts,
        )
        if action is StopAction.COMPLETE:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-completed-{uuid4().hex}",
                    type=EventType.RUN_COMPLETED,
                    payload={"run_id": run_id},
                )
            )
        status = {
            StopAction.CONTINUE: result.status,
            StopAction.PAUSE: RunStatus.PAUSED,
            StopAction.COMPLETE: result.status,
        }[action]
        return TransitionOutcome(
            action=action,
            status=status,
            checkpoint_id=checkpoint.checkpoint_id,
            gate_results=gate_summary.results,
        )

    @_operation_locked
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
        if decision is ResumeDecision.ACCEPT_DRIFT and any(
            artifact.status == "missing" for artifact in verification.artifacts
        ):
            raise InvalidStateTransition("missing artifacts require rerun")
        accepted_artifacts = (
            self._accepted_drift_artifacts(
                checkpoint,
                verification.artifacts,
            )
            if decision is ResumeDecision.ACCEPT_DRIFT
            else []
        )
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
        for artifact in accepted_artifacts:
            self.repository.append(
                ProjectEvent(
                    event_id=f"artifact-event-{uuid4().hex}",
                    type=EventType.ARTIFACT_REGISTERED,
                    payload={"artifact": artifact.model_dump(mode="json")},
                )
            )
        if decision is ResumeDecision.ACCEPT_DRIFT:
            accepted_state = self.repository.load()
            self.checkpoints.create(
                accepted_state,
                checkpoint.completed_target,
                inputs_used=checkpoint.inputs_used,
                artifacts_created=[
                    accepted_state.artifacts[artifact.artifact_id]
                    for artifact in checkpoint.artifacts_created
                ],
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

    def _accepted_drift_artifacts(
        self,
        checkpoint: Checkpoint,
        verifications: list[ResumeArtifactStatus],
    ) -> list[ArtifactEnvelope]:
        envelopes = {
            artifact.artifact_id: artifact
            for artifact in [*checkpoint.input_artifacts, *checkpoint.artifacts_created]
        }
        accepted = []
        store = ArtifactStore(self.project_root)
        for verification in verifications:
            if verification.status != "drifted":
                continue
            original = envelopes[verification.artifact_id]
            accepted.append(
                store.register(
                    original.path,
                    artifact_id=original.artifact_id,
                    artifact_type=original.type,
                    schema_version=original.schema_version,
                    producing_capability=original.producing_capability,
                    source_artifact_ids=original.source_artifact_ids,
                    provenance_references=list(
                        dict.fromkeys(
                            [
                                *original.provenance_references,
                                f"resume-accepted-drift:{checkpoint.checkpoint_id}",
                            ]
                        )
                    ),
                    sensitivity=original.sensitivity,
                    human_edited=True,
                    verification_state="verified",
                )
            )
        return accepted

    @_operation_locked
    def fail(self, run_id: str, reason: str) -> None:
        del reason  # Raw exception/provider text is never durable project state.
        state = self.repository.load()
        if state.active_run_id != run_id:
            raise InvalidStateTransition("failure does not match the active run")
        self.repository.append(
            ProjectEvent(
                event_id=f"run-failed-{uuid4().hex}",
                type=EventType.RUN_FAILED,
                payload={
                    "run_id": run_id,
                    "error_code": "capability_execution_failed",
                    "reason": "Capability execution failed; raw details omitted.",
                },
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

    def _verify_artifacts(
        self, artifacts: list[ArtifactEnvelope]
    ) -> list[ArtifactVerification | ResumeArtifactStatus]:
        store = ArtifactStore(self.project_root)
        verifications: list[ArtifactVerification | ResumeArtifactStatus] = []
        for artifact in artifacts:
            verification: ArtifactVerification | ResumeArtifactStatus
            try:
                verification = store.verify(artifact)
            except FileNotFoundError:
                verification = ResumeArtifactStatus(
                    artifact_id=artifact.artifact_id,
                    path=artifact.path,
                    status="missing",
                    expected_sha256=artifact.sha256,
                )
            verifications.append(verification)
        return verifications

    def _request_with_available_inputs(
        self,
        request: ExecutionRequest,
        capability_id: str,
        state: ProjectState,
    ) -> ExecutionRequest:
        requested = self.router.resolve(request.target)
        if not isinstance(requested, WorkflowSpec):
            return request
        node_id = next(node.id for node in requested.nodes if node.capability_id == capability_id)
        node_capabilities = {node.id: node.capability_id for node in requested.nodes}
        inputs = list(request.inputs)
        present_ids = {item.artifact_id for item in inputs}
        mapped_artifacts = []
        for mapping in requested.artifact_mappings:
            if mapping.to_node != node_id:
                continue
            source_capability = node_capabilities[mapping.from_node]
            for artifact_type in sorted(mapping.artifact_types):
                matches = [
                    artifact
                    for artifact in state.artifacts.values()
                    if artifact.type == artifact_type
                    and artifact.producing_capability == source_capability
                    and artifact.artifact_id in state.current_run_artifact_ids
                ]
                if matches:
                    mapped_artifacts.append(max(matches, key=lambda artifact: artifact.created_at))
        for artifact in mapped_artifacts:
            if artifact.artifact_id not in present_ids:
                inputs.append(
                    InputArtifactRef(
                        artifact_id=artifact.artifact_id,
                        type=artifact.type,
                        path_or_uri=artifact.path,
                    )
                )
        return request.model_copy(update={"inputs": inputs})

    def _prepare_entry_inputs(
        self,
        request: ExecutionRequest,
        state: ProjectState,
    ) -> tuple[
        list[ArtifactVerification | ResumeArtifactStatus],
        list[ArtifactEnvelope],
    ]:
        store = ArtifactStore(self.project_root)
        verifications: list[ArtifactVerification | ResumeArtifactStatus] = []
        pending: list[ArtifactEnvelope] = []
        for input_ref in request.inputs:
            existing = state.artifacts.get(input_ref.artifact_id)
            if existing is not None:
                if existing.type != input_ref.type or existing.path != input_ref.path_or_uri:
                    verifications.append(
                        ResumeArtifactStatus(
                            artifact_id=input_ref.artifact_id,
                            path=input_ref.path_or_uri,
                            status="drifted",
                            expected_sha256=existing.sha256,
                        )
                    )
                    continue
                try:
                    verifications.append(store.verify(existing))
                except FileNotFoundError:
                    verifications.append(
                        ResumeArtifactStatus(
                            artifact_id=existing.artifact_id,
                            path=existing.path,
                            status="missing",
                            expected_sha256=existing.sha256,
                        )
                    )
                continue

            if urlsplit(input_ref.path_or_uri).scheme:
                verifications.append(
                    ResumeArtifactStatus(
                        artifact_id=input_ref.artifact_id,
                        path=input_ref.path_or_uri,
                        status="missing",
                        expected_sha256="0" * 64,
                    )
                )
                continue
            try:
                envelope = store.register(
                    input_ref.path_or_uri,
                    artifact_id=input_ref.artifact_id,
                    artifact_type=input_ref.type,
                    schema_version="1.0",
                    producing_capability="local-manual",
                    provenance_references=[f"user-input:{input_ref.artifact_id}"],
                )
            except (ArtifactNotFound, FileNotFoundError, OSError):
                verifications.append(
                    ResumeArtifactStatus(
                        artifact_id=input_ref.artifact_id,
                        path=input_ref.path_or_uri,
                        status="missing",
                        expected_sha256="0" * 64,
                    )
                )
                continue
            pending.append(envelope)
            verifications.append(store.verify(envelope))
        return verifications, pending

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
        workflow_state = self.repository.load()
        state_artifacts = workflow_state.artifacts.values()
        node_capabilities = {item.id: item.capability_id for item in requested.nodes}
        missing_mappings = []
        for mapping in requested.artifact_mappings:
            if mapping.to_node != node.id:
                continue
            source_capability = node_capabilities[mapping.from_node]
            for artifact_type in mapping.artifact_types:
                if not any(
                    artifact.type == artifact_type
                    and artifact.producing_capability == source_capability
                    and artifact.artifact_id in workflow_state.current_run_artifact_ids
                    for artifact in state_artifacts
                ):
                    missing_mappings.append(f"{source_capability}:{artifact_type}")
        if missing_mappings:
            raise InvalidStateTransition(
                "workflow artifact mappings are unsatisfied: " + ", ".join(sorted(missing_mappings))
            )
        return rerun

    def _rerun_is_authorized(self, capability_id: str) -> bool:
        state = self.repository.load()
        if not state.decisions or state.decisions[-1].description != "Resume decision: rerun":
            return False
        checkpoint = self.checkpoints.current()
        return (
            checkpoint is not None
            and checkpoint.run_id == state.active_run_id
            and checkpoint.completed_target == capability_id
        )

    def _enforce_current_checkpoint(
        self,
        run_id: str,
        *,
        allow_state_only_drift: bool,
    ) -> None:
        state = self.repository.load()
        if state.current_checkpoint is None:
            return
        checkpoint = self.checkpoints.load(state.current_checkpoint)
        if checkpoint.run_id != run_id:
            return
        if state.decisions and state.decisions[-1].description == "Resume decision: rerun":
            return
        continued_after_verification = bool(
            state.decisions and state.decisions[-1].description == "Resume decision: continue"
        )
        verification = self.checkpoints.verify_resume(checkpoint.checkpoint_id)
        if verification.status == "verified" or (
            (allow_state_only_drift or continued_after_verification)
            and all(artifact.status == "verified" for artifact in verification.artifacts)
        ):
            return
        gate_summary = self.gates.run(
            ["checkpoint.consistent"],
            GateContext(resume_verification=verification),
        )
        for gate_result in gate_summary.results:
            self.repository.append(
                ProjectEvent(
                    event_id=f"gate-event-{uuid4().hex}",
                    type=EventType.GATE_RECORDED,
                    payload={"gate_result": gate_result.model_dump(mode="json")},
                )
            )
        if state.lifecycle is ProjectLifecycle.RUNNING:
            self.repository.append(
                ProjectEvent(
                    event_id=f"run-blocked-{uuid4().hex}",
                    type=EventType.RUN_BLOCKED,
                    payload={"run_id": run_id},
                )
            )
        raise CheckpointIntegrityError("checkpoint drift requires explicit accept_drift or rerun")

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
            autonomous_review=node.autonomous_review,
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
