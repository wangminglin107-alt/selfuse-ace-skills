"""V1 gates shared by standalone capabilities and workflows."""

from __future__ import annotations

from research_skills_os.core.contracts.enums import GateSeverity, GateStatus
from research_skills_os.core.contracts.models import GateResult
from research_skills_os.core.gates.protocol import Gate, GateContext


class BuiltinGate:
    gate_id: str
    gate_version = "1.0"
    severity: GateSeverity

    def result(
        self,
        status: GateStatus,
        *,
        findings: list[str] | None = None,
        evidence: list[str] | None = None,
        remediation: list[str] | None = None,
    ) -> GateResult:
        return GateResult(
            gate_id=self.gate_id,
            gate_version=self.gate_version,
            status=status,
            severity=self.severity,
            findings=findings or [],
            evidence=evidence or [],
            remediation=remediation or [],
        )


class ContractValidGate(BuiltinGate):
    gate_id = "contract.valid"
    severity = GateSeverity.BLOCKING

    def evaluate(self, context: GateContext) -> GateResult:
        if context.request is None:
            return self.result(
                GateStatus.FAIL,
                findings=["A validated execution request is required."],
                remediation=["Validate the request against contract version 1.0."],
            )
        return self.result(GateStatus.PASS)


class RequiredInputsGate(BuiltinGate):
    gate_id = "inputs.required"
    severity = GateSeverity.BLOCKING

    def evaluate(self, context: GateContext) -> GateResult:
        if context.request is None:
            return self.result(GateStatus.FAIL, findings=["Execution request is missing."])
        present = {item.type for item in context.request.inputs}
        missing = sorted(context.required_input_types - present)
        if missing:
            return self.result(
                GateStatus.FAIL,
                findings=[f"Missing required input types: {', '.join(missing)}"],
                remediation=["Register the missing input artifacts before continuing."],
            )
        return self.result(GateStatus.PASS)


class ArtifactIntegrityGate(BuiltinGate):
    gate_id = "artifacts.integrity"
    severity = GateSeverity.BLOCKING

    def evaluate(self, context: GateContext) -> GateResult:
        invalid = [item for item in context.artifact_verifications if item.status != "verified"]
        if invalid:
            return self.result(
                GateStatus.FAIL,
                findings=[f"Artifact {item.artifact_id} is {item.status}." for item in invalid],
                remediation=["Restore, accept, or rerun every changed artifact explicitly."],
            )
        if not context.artifact_verifications:
            return self.result(GateStatus.NOT_APPLICABLE)
        return self.result(GateStatus.PASS)


class ProvenanceCompleteGate(BuiltinGate):
    gate_id = "provenance.complete"
    severity = GateSeverity.BLOCKING

    def evaluate(self, context: GateContext) -> GateResult:
        if context.result is None:
            return self.result(GateStatus.NOT_APPLICABLE)
        missing = [
            artifact.artifact_id
            for artifact in context.result.artifacts
            if not artifact.provenance_references and not artifact.source_artifact_ids
        ]
        if missing:
            return self.result(
                GateStatus.FAIL,
                findings=[f"Artifacts lack provenance: {', '.join(sorted(missing))}"],
                remediation=["Link each artifact to source artifacts or provenance records."],
            )
        return self.result(GateStatus.PASS)


class UncertaintyExplicitGate(BuiltinGate):
    gate_id = "uncertainty.explicit"
    severity = GateSeverity.ADVISORY

    def evaluate(self, context: GateContext) -> GateResult:
        recorded = context.result.uncertainties if context.result is not None else []
        if context.material_uncertainty_detected and not any(item.material for item in recorded):
            return self.result(
                GateStatus.WARN,
                findings=["Material uncertainty was detected but not recorded."],
                remediation=["Add an explicit material uncertainty record."],
            )
        return self.result(GateStatus.PASS)


class CheckpointConsistentGate(BuiltinGate):
    gate_id = "checkpoint.consistent"
    severity = GateSeverity.BLOCKING

    def evaluate(self, context: GateContext) -> GateResult:
        verification = context.resume_verification
        if verification is None:
            return self.result(GateStatus.NOT_APPLICABLE)
        if verification.status == "drifted":
            return self.result(
                GateStatus.FAIL,
                findings=verification.reasons,
                remediation=["Choose rebase, rerun, or explicit acceptance before resume."],
            )
        return self.result(GateStatus.PASS)


class ProviderPolicyGate(BuiltinGate):
    gate_id = "provider.policy"
    severity = GateSeverity.BLOCKING

    def evaluate(self, context: GateContext) -> GateResult:
        if not context.provider_uses:
            return self.result(GateStatus.PASS)
        findings: list[str] = []
        for use in context.provider_uses:
            if not use.declared:
                findings.append(f"Provider {use.provider_id} is not declared.")
            elif use.network and (
                context.request is None or context.request.constraints.network == "deny"
            ):
                findings.append(f"Provider {use.provider_id} requires denied network access.")
        if findings:
            return self.result(
                GateStatus.FAIL,
                findings=findings,
                remediation=["Authorize a declared provider or use the local/manual provider."],
            )
        return self.result(GateStatus.PASS)


def builtin_gates() -> list[Gate]:
    return [
        ContractValidGate(),
        RequiredInputsGate(),
        ArtifactIntegrityGate(),
        ProvenanceCompleteGate(),
        UncertaintyExplicitGate(),
        CheckpointConsistentGate(),
        ProviderPolicyGate(),
    ]
