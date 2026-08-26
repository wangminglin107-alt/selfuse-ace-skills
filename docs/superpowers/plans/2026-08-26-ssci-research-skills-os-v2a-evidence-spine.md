# SSCI Research Skills OS V2A Evidence Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Windows-tested evidence spine whose paper knowledge base, evidence synthesis,
citation verification, and theory architecture capabilities work independently and compose through
`literature-to-theory` while preserving exact source passages, contradictions, and human theory
decisions.

**Architecture:** Extend the V1 contract `1.0` additively. Each V2A capability owns strict Pydantic
artifact models and deterministic gate evaluation; the existing kernel owns routing, artifacts,
state, checkpoints, and stop policies. The workflow contains only capability IDs and artifact
mappings, while Codex-facing Skills perform the scholarly work and write human-readable artifacts.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, filelock, pytest, pytest-cov, Ruff, mypy,
PowerShell, Markdown, YAML, JSON, JSONL.

**Spec:** `docs/superpowers/specs/2026-08-26-ssci-research-skills-os-v2a-evidence-spine-design.md`

## Global Constraints

- Keep execution contract, checkpoint, event, capability, and workflow schema versions at `1.0`.
- Default execution and tests are offline; live providers are optional and declared.
- Never disable TLS certificate verification or place credentials in source, fixtures, or logs.
- Exact original-language passages plus page or stable section locators are required for content
  support; metadata-only records cannot satisfy support gates.
- Material contradictions remain visible and block progression until a human resolves or accepts
  the bounded limitation.
- Theory selection is human-owned; autonomous mode stops at the theory decision packet.
- Do not modify the seven installed local SSCI Skills; verify their SHA-256 values before install.
- No fixed literature count, recency percentage, or forced named theory.
- Every production change starts with a failing test and ends with a small conventional commit.
- Do not add R, LaTeX, a vector database, embedding runtime, or paid API to V2A dependencies.

## File map

```text
src/research_skills_os/capabilities/
  evidence_common/models.py           shared closed vocabularies and locators
  paper_knowledge_base/               durable document-index validation
  evidence_synthesis/                 evidence rows and contradiction validation
  citation_verification/              identity/support audit validation
  theory_architecture/                construct/theory decision validation
  gate_evaluators.py                  artifact loading and capability dispatch
src/research_skills_os/workflows/literature_to_theory/workflow.yaml
src/research_skills_os/core/orchestrator/
  stop_policy.py                      autonomous-review stop signal
  coordinator.py                      workflow-node signal propagation
src/research_skills_os/core/registry/models.py
skills/<v2a-capability>/               thin Codex-facing scholarly instructions
tests/unit/capabilities/               deterministic gate tests
tests/integration/                     routing, workflow, checkpoint, stop tests
tests/acceptance/fixtures/v2a-project/ small offline full-text fixture
projects/gsma-sentiment-engagement/    real V2A research checkpoint
```

---

### Task 1: Lock V2A upstream provenance before reuse

**Files:**

- Modify: `SOURCE_MANIFEST.yaml`
- Modify: `tests/contract/test_source_manifest.py`
- Modify: `docs/architecture/upstream-source-audit.md`
- External checkouts: `../upstream/nature-skills`, `../upstream/paperspine`,
  `../upstream/humanities-thesis-skill`, `../upstream/reference-checker-skill`,
  `../upstream/light-skills`, `../upstream/academic-research-skills`

**Interfaces:**

- Consumes: `load_manifest(path: Path) -> SourceManifest`
- Produces: validated entries addressable by `upstream_repo`, `upstream_commit`, and
  `source_file`; later tasks may reuse only rows whose `reuse_mode` permits it.

- [ ] **Step 1: Add failing provenance assertions**

Add locked commits and checkout paths:

```python
V2A_LOCKED_COMMITS = {
    "Yuan1z0825/nature-skills": "3817cd194c31010febb1312ab786e53cd8154333",
    "WUBING2023/PaperSpine": "360ae775639a27458d4f24040b65a4cbe935b213",
    "ganzhi-black/humanities-thesis-skill": "9f9c97162e250df8d6c214b828bb973828a2a780",
    "Liuxiangjian-ai/reference-checker-skill": "f30bd18b79f38bb24e57cad6ea0132323e329c94",
    "Light0305/Light-skills": "6b44f57d1274eb38a6c79dc29c2d21e5e0a225a9",
    "Imbad0202/academic-research-skills": "127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb",
}
```

Assert that adapted rows have a local target and local tests, V2A conceptual rows introduce no
copied target, the Humanities Thesis HTTP client is absent from the accepted manifest, and every
accepted hash matches bytes at the locked checkout.

- [ ] **Step 2: Verify the test fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_source_manifest.py -q
```

Expected: FAIL because the six repositories and V2A manifest entries are absent.

- [ ] **Step 3: Populate checkouts and manifest rows**

Use the already audited local Git repositories as clone sources, checkout the exact commits, and
record the file hashes from the approved spec. Add one manifest row per accepted source file; do
not group multiple files behind one unverifiable entry. Record the insecure HTTP client only in
`docs/architecture/upstream-source-audit.md`, mark it blocked there, and assert that its path never
appears in the accepted manifest. Record Academic Research Skills as conceptual because its CC
BY-NC license is not compatible with code copying into this public project.

- [ ] **Step 4: Verify provenance**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_source_manifest.py -q
.\.venv\Scripts\python.exe -m pytest tests/contract -q
```

Expected: PASS; every locked file hash matches and no adapted entry lacks tests.

- [ ] **Step 5: Commit**

```powershell
git add SOURCE_MANIFEST.yaml tests/contract/test_source_manifest.py docs/architecture/upstream-source-audit.md
git commit -m "docs(v2a): lock evidence spine sources"
```

---

### Task 2: Define shared evidence vocabularies and locators

**Files:**

- Create: `src/research_skills_os/capabilities/evidence_common/__init__.py`
- Create: `src/research_skills_os/capabilities/evidence_common/models.py`
- Create: `tests/unit/capabilities/test_evidence_common_models.py`

**Interfaces:**

- Produces: `ContentLocator`, `EvidenceRole`, `IdentityState`, `SupportState`, `AccessState`,
  `PrivacyLabel`, and `VerificationRoute`.
- Consumers: Tasks 3–6.

- [ ] **Step 1: Write failing model tests**

```python
def test_content_locator_requires_page_or_stable_section():
    with pytest.raises(ValidationError, match="page or section"):
        ContentLocator(block_id="block-1", content_sha256="a" * 64)


def test_original_passage_hash_is_lowercase_sha256():
    locator = ContentLocator(
        page=7,
        block_id="p7-b2",
        content_sha256="a" * 64,
    )
    assert locator.page == 7
```

Also test closed values:

```python
EvidenceRole = Literal["supports", "qualifies", "contradicts", "null", "background"]
IdentityState = Literal["verified", "mismatch", "not_found", "suspicious", "manual_needed"]
SupportState = Literal[
    "supports", "partial", "misaligned", "contradicted", "unavailable", "manual_needed"
]
```

- [ ] **Step 2: Verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_evidence_common_models.py -q
```

Expected: FAIL on missing module.

- [ ] **Step 3: Implement strict shared models**

```python
class ContentLocator(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, min_length=1)
    block_id: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_human_locator(self) -> "ContentLocator":
        if self.page is None and self.section is None:
            raise ValueError("page or section locator is required")
        return self
```

Use `StrEnum` for runtime states and export them through `__init__.py`.

- [ ] **Step 4: Verify and type-check**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_evidence_common_models.py -q
.\.venv\Scripts\python.exe -m mypy src/research_skills_os/capabilities/evidence_common
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/research_skills_os/capabilities/evidence_common tests/unit/capabilities/test_evidence_common_models.py
git commit -m "feat(v2a): define traceable evidence types"
```

---

### Task 3: Add the paper knowledge base capability

**Files:**

- Create: `src/research_skills_os/capabilities/paper_knowledge_base/__init__.py`
- Create: `src/research_skills_os/capabilities/paper_knowledge_base/models.py`
- Create: `src/research_skills_os/capabilities/paper_knowledge_base/gates.py`
- Create: `src/research_skills_os/capabilities/paper_knowledge_base/capability.yaml`
- Create: `src/research_skills_os/capabilities/paper_knowledge_base/schemas/document-index.schema.json`
- Create: `src/research_skills_os/capabilities/paper_knowledge_base/schemas/corpus-status.schema.json`
- Create: `tests/unit/capabilities/test_paper_knowledge_base_gates.py`

**Interfaces:**

- Consumes artifact types: `source_registry`, `source_document`
- Produces artifact types: `document_index`, `corpus_status`
- Produces function:
  `evaluate_paper_knowledge_base(document_index: Mapping[str, Any], corpus_status: Mapping[str, Any]) -> list[GateResult]`

- [ ] **Step 1: Write failing gate tests**

Use a valid document with artifact ID, project-relative path, file SHA-256, public privacy state,
verified metadata, available content, and one page locator. Test failures for duplicate source IDs,
missing locator, hash mismatch between document and block, missing privacy state, absolute path,
and a superseded version without a replacement source ID.

```python
def test_metadata_only_document_does_not_pass_content_ready_gate(valid_index, valid_status):
    valid_index["documents"][0]["content_availability"] = "metadata_only"
    results = by_id(evaluate_paper_knowledge_base(valid_index, valid_status))
    assert results["corpus.locators"].status is GateStatus.FAIL
```

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_paper_knowledge_base_gates.py -q
```

Expected: FAIL on missing capability.

- [ ] **Step 3: Implement models and independent gates**

Define `DocumentRecord`, `DocumentIndex`, and `CorpusStatus` with `extra="forbid"`. Return these
blocking gates in stable order:

```text
corpus.required
corpus.identity_integrity
corpus.locators
corpus.privacy_declared
```

Do not perform network I/O or PDF extraction in gate code. Validate the declared result only.

- [ ] **Step 4: Add capability manifest and schemas**

Declare `network: none`, provider `local-manual`, output types `document_index` and
`corpus_status`, and all four capability gates plus `provenance.complete` and
`uncertainty.explicit`.

- [ ] **Step 5: Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_paper_knowledge_base_gates.py tests/unit/registry/test_loader.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/capabilities/paper_knowledge_base tests/unit/capabilities/test_paper_knowledge_base_gates.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/research_skills_os/capabilities/paper_knowledge_base tests/unit/capabilities/test_paper_knowledge_base_gates.py
git commit -m "feat(v2a): add paper knowledge base gates"
```

---

### Task 4: Add evidence synthesis and contradiction preservation

**Files:**

- Create: `src/research_skills_os/capabilities/evidence_synthesis/__init__.py`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/models.py`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/gates.py`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/capability.yaml`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/schemas/evidence-row.schema.json`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/schemas/synthesis-matrix.schema.json`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/schemas/contradiction-ledger.schema.json`
- Create: `src/research_skills_os/capabilities/evidence_synthesis/schemas/coverage-report.schema.json`
- Create: `tests/unit/capabilities/test_evidence_synthesis_gates.py`

**Interfaces:**

- Consumes: `research_brief_metadata`, `novelty_audit`, `document_index`
- Produces: `evidence_rows`, `synthesis_matrix`, `contradiction_ledger`, `coverage_report`
- Produces function:
  `evaluate_evidence_synthesis(rows: list[Mapping[str, Any]], matrix: Mapping[str, Any], ledger: Mapping[str, Any], coverage: Mapping[str, Any]) -> list[GateResult]`

- [ ] **Step 1: Write failing evidence-row tests**

```python
def test_evidence_row_separates_source_claim_from_author_inference(valid_row):
    valid_row["source_claim"] = valid_row["author_inference"]
    result = by_id(evaluate_evidence_synthesis([valid_row], matrix(), ledger(), coverage()))
    assert result["synthesis.source_inference_boundary"].status is GateStatus.FAIL


def test_exact_passage_and_locator_are_required(valid_row):
    valid_row["exact_passage"] = ""
    result = by_id(evaluate_evidence_synthesis([valid_row], matrix(), ledger(), coverage()))
    assert result["synthesis.content_trace"].status is GateStatus.FAIL
```

Test unknown source IDs, duplicate row IDs, invalid downstream claim references, and a translated
passage that replaces rather than accompanies the original.

- [ ] **Step 2: Write failing contradiction tests**

Test that opposing roles on the same synthesis group require a ledger entry; a material unresolved
entry fails `synthesis.material_contradictions`; a non-material unresolved entry passes only when
its boundary note is non-empty; null results remain `null` rather than being removed.

- [ ] **Step 3: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_evidence_synthesis_gates.py -q
```

Expected: FAIL on missing capability.

- [ ] **Step 4: Implement models and gates**

Return stable gate IDs:

```text
synthesis.required
synthesis.content_trace
synthesis.source_inference_boundary
synthesis.contradiction_preserved
synthesis.material_contradictions
synthesis.coverage
```

`EvidenceRow` stores `exact_passage`, optional `reviewed_translation`, `ContentLocator`, source
claim, separate author inference, evidence role, verification status, and downstream claim IDs.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_evidence_synthesis_gates.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/capabilities/evidence_synthesis tests/unit/capabilities/test_evidence_synthesis_gates.py
git add src/research_skills_os/capabilities/evidence_synthesis tests/unit/capabilities/test_evidence_synthesis_gates.py
git commit -m "feat(v2a): preserve claim-level evidence conflicts"
```

---

### Task 5: Add separate citation identity and support audits

**Files:**

- Create: `src/research_skills_os/capabilities/citation_verification/__init__.py`
- Create: `src/research_skills_os/capabilities/citation_verification/models.py`
- Create: `src/research_skills_os/capabilities/citation_verification/gates.py`
- Create: `src/research_skills_os/capabilities/citation_verification/capability.yaml`
- Create: `src/research_skills_os/capabilities/citation_verification/schemas/citation-identity-audit.schema.json`
- Create: `src/research_skills_os/capabilities/citation_verification/schemas/citation-support-audit.schema.json`
- Create: `src/research_skills_os/capabilities/citation_verification/schemas/citation-blockers.schema.json`
- Create: `tests/unit/capabilities/test_citation_verification_gates.py`

**Interfaces:**

- Consumes: `source_registry`, `document_index`, `evidence_rows`
- Produces: `citation_identity_audit`, `citation_support_audit`, `citation_blockers`
- Produces function:
  `evaluate_citation_verification(identity: Mapping[str, Any], support: Mapping[str, Any], blockers: Mapping[str, Any]) -> list[GateResult]`

- [ ] **Step 1: Write failing identity-route tests**

Test DOI/title mismatch, author mismatch, retraction/correction visibility, manual-needed state, and
a Chinese journal article without DOI verified through title, author, journal, year, and an
authorized official-record locator.

```python
def test_missing_doi_does_not_fail_source_type_without_doi(valid_chinese_identity):
    results = by_id(evaluate_citation_verification(
        valid_chinese_identity, valid_support(), empty_blockers()
    ))
    assert results["citation.identity"].status is GateStatus.PASS
```

- [ ] **Step 2: Write failing support-boundary tests**

Test that `verified` identity plus `unavailable` support does not pass content support, a partial
passage cannot support a stronger causal statement, and support records must point to evidence-row
IDs and exact locator hashes.

- [ ] **Step 3: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_citation_verification_gates.py -q
```

Expected: FAIL on missing capability.

- [ ] **Step 4: Implement closed audit models and gates**

Return:

```text
citation.required
citation.identity
citation.content_support
citation.route_trace
citation.blockers_visible
```

Metadata-only audits may pass `citation.identity` but must fail or remain not applicable for
`citation.content_support` when a content claim is requested.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_citation_verification_gates.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/capabilities/citation_verification tests/unit/capabilities/test_citation_verification_gates.py
git add src/research_skills_os/capabilities/citation_verification tests/unit/capabilities/test_citation_verification_gates.py
git commit -m "feat(v2a): separate citation identity and support"
```

---

### Task 6: Add evidence-bounded theory architecture

**Files:**

- Create: `src/research_skills_os/capabilities/theory_architecture/__init__.py`
- Create: `src/research_skills_os/capabilities/theory_architecture/models.py`
- Create: `src/research_skills_os/capabilities/theory_architecture/gates.py`
- Create: `src/research_skills_os/capabilities/theory_architecture/capability.yaml`
- Create: `src/research_skills_os/capabilities/theory_architecture/schemas/theory-candidates.schema.json`
- Create: `src/research_skills_os/capabilities/theory_architecture/schemas/construct-map.schema.json`
- Create: `src/research_skills_os/capabilities/theory_architecture/schemas/theory-decision-packet.schema.json`
- Create: `tests/unit/capabilities/test_theory_architecture_gates.py`

**Interfaces:**

- Consumes: `research_brief_metadata`, `novelty_audit`, `synthesis_matrix`,
  `contradiction_ledger`, `citation_support_audit`
- Produces: `theory_candidates`, `construct_map`, `theory_rationale`,
  `theory_decision_packet`
- Produces function:
  `evaluate_theory_architecture(candidates: Mapping[str, Any], constructs: Mapping[str, Any], decision: Mapping[str, Any], rationale: str) -> list[GateResult]`

- [ ] **Step 1: Write failing theory/evidence tests**

Test unknown evidence-row references, incompatible levels of analysis, hidden assumptions, theory
integration without a compatibility rationale, and an unresolved material contradiction omitted
from a candidate.

- [ ] **Step 2: Write the no-forced-theory test**

```python
def test_descriptive_recommendation_is_valid_when_theory_support_is_insufficient():
    decision = valid_decision(
        recommendation="descriptive",
        authorization_state="proposed",
        rationale="Verified evidence does not establish a defensible mechanism.",
    )
    results = by_id(evaluate_theory_architecture(
        candidates={"schema_version": "1.0", "candidates": []},
        constructs=construct_map(),
        decision=decision,
        rationale="Bounded synthesis.",
    ))
    assert results["theory.no_forced_theory"].status is GateStatus.PASS
```

Test that `authorization_state="selected"` requires a user decision ID.

- [ ] **Step 3: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_theory_architecture_gates.py -q
```

Expected: FAIL on missing capability.

- [ ] **Step 4: Implement models and gates**

Return:

```text
theory.required
theory.evidence_fit
theory.construct_consistency
theory.level_consistency
theory.contradictions_acknowledged
theory.no_forced_theory
theory.user_decision
```

The decision recommendation vocabulary is `single_theory`, `bounded_integration`,
`mechanism_framework`, or `descriptive`. The selection state is `proposed` or `selected`.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_theory_architecture_gates.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/capabilities/theory_architecture tests/unit/capabilities/test_theory_architecture_gates.py
git add src/research_skills_os/capabilities/theory_architecture tests/unit/capabilities/test_theory_architecture_gates.py
git commit -m "feat(v2a): add human-owned theory decisions"
```

---

### Task 7: Connect V2A artifacts to kernel-owned gate evaluation

**Files:**

- Modify: `src/research_skills_os/capabilities/gate_evaluators.py`
- Create: `tests/unit/capabilities/test_v2a_gate_evaluators.py`
- Modify: `tests/integration/test_kernel_trust_boundary.py`

**Interfaces:**

- Consumes existing:
  `evaluate_capability_artifacts(capability_id: str, project_root: Path, artifacts: list[ArtifactEnvelope]) -> list[GateResult]`
- Produces loaders `_load_json`, `_load_jsonl`, and dispatch for all four V2A capability IDs.

- [ ] **Step 1: Write failing loader and trust-boundary tests**

Create project-contained JSON and JSONL artifacts, register them, and assert kernel evaluation
passes. Change one artifact after registration and assert the kernel blocks before accepting a
caller-supplied PASS. Test malformed JSONL returns a failing `*.required` gate instead of raising.

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_v2a_gate_evaluators.py tests/integration/test_kernel_trust_boundary.py -q
```

Expected: FAIL because V2A IDs currently return no scholarly gates.

- [ ] **Step 3: Implement narrow artifact loaders and dispatch**

Use `resolve_project_path`, UTF-8, `json.loads`, and line-number-aware JSONL parsing. Never load an
unregistered path and never trust artifact content supplied directly by a caller.

- [ ] **Step 4: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_v2a_gate_evaluators.py tests/integration/test_kernel_trust_boundary.py -q
.\.venv\Scripts\python.exe -m mypy src/research_skills_os/capabilities
git add src/research_skills_os/capabilities/gate_evaluators.py tests/unit/capabilities/test_v2a_gate_evaluators.py tests/integration/test_kernel_trust_boundary.py
git commit -m "feat(v2a): evaluate evidence artifacts inside kernel"
```

---

### Task 8: Compose `literature-to-theory` and enforce autonomous review

**Files:**

- Modify: `src/research_skills_os/core/registry/models.py`
- Modify: `src/research_skills_os/core/orchestrator/stop_policy.py`
- Modify: `src/research_skills_os/core/orchestrator/coordinator.py`
- Create: `src/research_skills_os/workflows/literature_to_theory/__init__.py`
- Create: `src/research_skills_os/workflows/literature_to_theory/workflow.yaml`
- Modify: `tests/unit/orchestrator/test_stop_policy.py`
- Create: `tests/integration/test_literature_to_theory_workflow.py`
- Modify: `tests/contract/test_workflow_separation.py`

**Interfaces:**

- Adds `WorkflowNode.autonomous_review: bool = False`
- Adds `StopSignals.autonomous_review: bool = False`
- Preserves V1 behavior because existing nodes default to `False`.

- [ ] **Step 1: Write failing stop-policy tests**

```python
def test_autonomous_mode_pauses_at_explicit_autonomous_review():
    action = StopPolicy().decide(
        RunMode.AUTONOMOUS,
        StopSignals(autonomous_review=True),
    )
    assert action is StopAction.PAUSE


def test_autonomous_mode_keeps_v1_default_behavior():
    assert StopPolicy().decide(RunMode.AUTONOMOUS, StopSignals()) is StopAction.CONTINUE
```

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/orchestrator/test_stop_policy.py -q
```

Expected: FAIL because the new signal does not exist.

- [ ] **Step 3: Implement additive review signal**

Add the two defaulted fields, pass the workflow node value through `Coordinator._stop_signals`,
and pause autonomous runs before terminal completion when `autonomous_review` is true.

- [ ] **Step 4: Write workflow integration tests**

Assert the node order is knowledge base, synthesis, verification, theory; every mapped artifact is
declared by its producer; all capabilities remain directly routable; interactive pauses after each
node; checkpointed stops on material contradictions and theory review; autonomous stops at the
theory decision packet.

- [ ] **Step 5: Add thin workflow YAML**

Set `human_review: true` and `autonomous_review: true` only on the theory node. Map document index
to synthesis and verification, evidence rows to verification, synthesis/audit artifacts to theory,
and keep global gates `artifacts.integrity` and `provider.policy`.

- [ ] **Step 6: Verify V1 and V2A**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/orchestrator/test_stop_policy.py tests/contract/test_workflow_separation.py tests/integration/test_idea_to_novelty_workflow.py tests/integration/test_literature_to_theory_workflow.py -q
```

Expected: PASS, including unchanged V1 autonomous expectations.

- [ ] **Step 7: Commit**

```powershell
git add src/research_skills_os/core/registry/models.py src/research_skills_os/core/orchestrator src/research_skills_os/workflows/literature_to_theory tests/unit/orchestrator/test_stop_policy.py tests/contract/test_workflow_separation.py tests/integration/test_literature_to_theory_workflow.py
git commit -m "feat(v2a): compose literature to theory workflow"
```

---

### Task 9: Write the five thin Codex Skills

**Required sub-skill:** `superpowers:writing-skills`

**Files:**

- Create: `skills/paper-knowledge-base/SKILL.md`
- Create: `skills/paper-knowledge-base/assets/document-index.template.json`
- Create: `skills/evidence-synthesis/SKILL.md`
- Create: `skills/evidence-synthesis/assets/evidence-row.template.json`
- Create: `skills/evidence-synthesis/assets/contradiction-ledger.template.json`
- Create: `skills/citation-verification/SKILL.md`
- Create: `skills/citation-verification/assets/citation-audit.template.json`
- Create: `skills/theory-architecture/SKILL.md`
- Create: `skills/theory-architecture/assets/theory-decision.template.json`
- Create: `skills/literature-to-theory/SKILL.md`
- Modify: `skills/research-os/SKILL.md`
- Create: `tests/acceptance/test_v2a_skill_contracts.py`

**Interfaces:**

- Each capability Skill writes only its declared artifacts and invokes the kernel lifecycle.
- `literature-to-theory` contains routing instructions only and delegates scholarly rules.

- [ ] **Step 1: Write failing skill-contract tests**

Assert each Skill exists, names its capability, declares exact inputs/outputs, preserves exact
passages and locators, and contains the five low-cognitive-load status fields. Assert workflow text
does not embed evidence, citation, or theory rubrics. Assert no Skill contains insecure TLS flags,
provider credentials, fabricated-source instructions, or fixed literature quotas.

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_v2a_skill_contracts.py -q
```

Expected: FAIL because the Skills are absent.

- [ ] **Step 3: Write capability Skills from the approved contracts**

Each standalone Skill ends with:

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```

The theory Skill must stop after producing a proposed decision packet; it records `selected` only
when a kernel user-decision record is supplied.

- [ ] **Step 4: Write the workflow Skill and update Research OS routing**

The workflow Skill names the next registered capability and mapped artifacts only. Add the V2A
workflow to `research-os` examples without copying capability methods.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_v2a_skill_contracts.py tests/contract/test_workflow_separation.py -q
git add skills tests/acceptance/test_v2a_skill_contracts.py
git commit -m "feat(v2a): add evidence spine skills"
```

---

### Task 10: Build the offline tracer-bullet acceptance project

**Files:**

- Create: `tests/acceptance/fixtures/v2a-project/artifacts/source-registry.yaml`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/document-index.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/corpus-status.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/evidence-rows.jsonl`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/synthesis-matrix.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/contradiction-ledger.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/coverage-report.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/citation-identity-audit.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/citation-support-audit.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/citation-blockers.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/theory-candidates.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/construct-map.json`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/theory-rationale.md`
- Create: `tests/acceptance/fixtures/v2a-project/artifacts/theory-decision-packet.json`
- Create: `tests/acceptance/fixtures/v2a-project/sources/source-a.md`
- Create: `tests/acceptance/fixtures/v2a-project/sources/source-b.md`
- Create: `tests/acceptance/test_v2a_end_to_end.py`

**Interfaces:**

- Produces a fully local fixture with two contradictory source passages, exact section locators,
  hashes, citation audits, and a proposed descriptive decision.

- [ ] **Step 1: Write the failing end-to-end test**

Initialize a project, register fixture inputs, run all four capability boundaries, verify each
checkpoint, and assert autonomous execution pauses at theory. Add a mutation test that changes
`source-b.md` and verifies dependent evidence/theory artifacts are rejected as drifted.

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_v2a_end_to_end.py -q
```

Expected: FAIL because the fixture artifacts do not exist.

- [ ] **Step 3: Create minimal honest fixture artifacts**

Use original fixture prose rather than copyrighted literature. Include one supporting passage and
one null/qualifying passage. Keep the material contradiction unresolved so checkpointed and
autonomous behavior can be verified without pretending to resolve it.

- [ ] **Step 4: Verify all run modes and resume**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_v2a_end_to_end.py tests/integration/test_checkpoint_resume.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tests/acceptance/fixtures/v2a-project tests/acceptance/test_v2a_end_to_end.py
git commit -m "test(v2a): add evidence spine tracer bullet"
```

---

### Task 11: Run the real NORC literature-and-theory checkpoint

**Files:**

- Create: `projects/gsma-sentiment-engagement/README.md`
- Create: `projects/gsma-sentiment-engagement/project.yaml`
- Create: `projects/gsma-sentiment-engagement/provenance/gsma-data-source.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/source-registry.yaml`
- Create: `projects/gsma-sentiment-engagement/artifacts/document-index.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/corpus-status.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/evidence-rows.jsonl`
- Create: `projects/gsma-sentiment-engagement/artifacts/synthesis-matrix.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/contradiction-ledger.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/coverage-report.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/citation-identity-audit.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/citation-support-audit.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/citation-blockers.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/theory-candidates.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/construct-map.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/theory-rationale.md`
- Create: `projects/gsma-sentiment-engagement/artifacts/theory-decision-packet.json`
- Create: `tests/acceptance/test_gsma_v2a_project.py`

**Interfaces:**

- Consumes official NORC GSMA documentation and inspected primary literature.
- Produces a real V2A checkpoint that V2B will consume; it does not claim a selected theory.

- [ ] **Step 1: Write the failing real-project acceptance test**

Assert the project question is associational, the NORC archive/methodology/data-dictionary URLs
and downloaded archive SHA-256 are recorded, every included source has inspected content and an
exact locator, every evidence row passes V2A gates, at least one qualification/null/conflict is
preserved, and the decision packet remains `proposed`.

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_gsma_v2a_project.py -q
```

Expected: FAIL because the project artifacts are absent.

- [ ] **Step 3: Build the source corpus from primary material**

Use the official NORC archive and methodology plus primary research seeds with stable identities,
including DOI `10.1073/pnas.1618923114`, DOI `10.1186/s42238-022-00132-1`, and DOI
`10.2196/jmir.3247`. Treat them as candidates until full text is inspected. Add other nearest work
only after identity and passage verification. Record exact original passages within copyright
limits, page/section locators, source hashes, access limitations, and retrieval routes.

- [ ] **Step 4: Produce synthesis, audits, and theory alternatives**

Separate sentiment valence, arousal, diffusion, engagement, account type, platform affordance,
and cannabis-discourse constructs. Preserve differences among observational, experimental, and
descriptive evidence. Recommend one of the four allowed decision types, leave it `proposed`, and
state why causal and individual-level claims are prohibited.

- [ ] **Step 5: Run the real checkpoint and acceptance test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_gsma_v2a_project.py -q
```

Expected: PASS with a reviewable theory decision packet and no fabricated or metadata-only support.

- [ ] **Step 6: Commit**

```powershell
git add projects/gsma-sentiment-engagement tests/acceptance/test_gsma_v2a_project.py
git commit -m "feat(v2a): add real gsma evidence checkpoint"
```

---

### Task 12: Document, install, and verify V2A

**Files:**

- Modify: `README.md`
- Modify: `docs/operator-guide/standalone-capabilities.md`
- Modify: `docs/operator-guide/run-modes.md`
- Modify: `docs/operator-guide/checkpoints-and-resume.md`
- Modify: `docs/operator-guide/privacy-and-providers.md`
- Create: `docs/operator-guide/evidence-and-citation-states.md`
- Create: `docs/operator-guide/contradictions-and-theory-decisions.md`
- Create: `docs/architecture/v2a-acceptance-report.md`
- Modify: `scripts/install-skills.ps1`
- Modify: `tests/integration/install/test_install_scripts.py`
- Modify: `tests/acceptance/test_documented_commands.py`

**Interfaces:**

- Installs five new Skills without modifying the seven existing SSCI Skills.
- Documents standalone, workflow, checkpoint, privacy, and decision behavior.

- [ ] **Step 1: Write failing install and documentation tests**

Assert the installer exposes the five V2A Skills, preserves hashes for the seven existing Skills,
rejects an incomplete source manifest, and every documented command executes against a temporary
project.

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/install tests/acceptance/test_documented_commands.py -q
```

Expected: FAIL because the new Skills and commands are not installed/documented.

- [ ] **Step 3: Update installer and guides**

Keep installation transactional and rollback-safe. Add the five status fields and exact resume
instructions to examples. Document identity versus support states, material contradiction stops,
and proposed versus selected theory decisions.

- [ ] **Step 4: Run focused verification**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities tests/integration/test_literature_to_theory_workflow.py tests/integration/install tests/acceptance/test_v2a_skill_contracts.py tests/acceptance/test_v2a_end_to_end.py tests/acceptance/test_gsma_v2a_project.py -q
```

Expected: PASS.

- [ ] **Step 5: Run full verification**

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=research_skills_os --cov-report=term-missing --cov-fail-under=90
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/research_skills_os
git diff --check
git status --short
```

Expected: all tests pass, coverage is at least 90%, Ruff and mypy report no errors, diff check is
clean, and only intended V2A files are changed.

- [ ] **Step 6: Record acceptance and commit**

Write exact command outputs, test counts, coverage, installed Skill hashes, known limitations, and
the GSMA checkpoint ID into `docs/architecture/v2a-acceptance-report.md`.

```powershell
git add README.md docs scripts tests/integration/install tests/acceptance/test_documented_commands.py
git commit -m "docs(v2a): verify evidence spine acceptance"
```

---

## Execution handoff

Execute inline in batches with `superpowers:executing-plans` because the user requested continuous
completion and did not authorize subagent dispatch. Use `superpowers:test-driven-development` for
Tasks 2–8 and 10–12, `superpowers:writing-skills` for Task 9, and
`superpowers:verification-before-completion` before reporting V2A complete.

Batch checkpoints:

1. Tasks 1–3: provenance, shared types, paper knowledge base.
2. Tasks 4–6: synthesis, citation verification, theory architecture.
3. Tasks 7–9: kernel evaluation, workflow stops, Skills.
4. Tasks 10–12: offline fixture, real project, install, and acceptance.
