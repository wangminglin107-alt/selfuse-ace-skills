# SSCI Research Skills OS V1 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Use `superpowers:test-driven-development` for every production change, `superpowers:writing-skills` for skill behavior, and `superpowers:verification-before-completion` before claiming V1 acceptance.

**Goal:** Deliver a Windows-tested, contract-first Research Skills OS whose `research-framing`, `literature-intelligence`, and `novelty-audit` capabilities work independently and compose through `idea-to-novelty` with durable checkpoints and three run modes.

**Architecture:** A small Python 3.12 kernel owns deterministic concerns: contracts, artifact registration, append-only state, checkpoints, routing, gates, and stop policies. Thin Codex skills own scholarly reasoning and call the kernel before and after each capability. Workflows reference capability IDs and artifact mappings only; they never duplicate capability prompts or rubrics.

**Tech stack:** Python 3.12, Pydantic 2, PyYAML, filelock, pytest, pytest-cov, Ruff, mypy, PowerShell, Markdown/YAML/JSON/JSONL.

**Approved design:** `docs/superpowers/specs/2026-08-25-ssci-research-skills-os-design.md`

## Execution rules

- Work only in this repository until final installation acceptance.
- Do not modify the seven installed `ssci-*` skills during implementation.
- Start each behavior with a failing test and record that failure.
- Keep academic artifacts human-readable; `.research-os/` stores machine state, not the only copy of content.
- Do not add a network dependency to the default acceptance path.
- Do not reuse upstream code before its manifest, license, security, and regression-test entries exist.
- Make one small conventional commit at the end of each task.

## Runtime boundary

The kernel does not invoke an LLM. A Codex capability skill performs academic reasoning, writes declared artifacts, then uses the kernel CLI to validate and commit the result. In autonomous mode the `research-os` skill follows the workflow graph inside the active Codex task; the kernel records each transition. This keeps orchestration inspectable and avoids a second hidden implementation of research prompts in Python.

```text
<research-project>/
  .research-os/
    project.yaml
    events.jsonl
    current-checkpoint
    checkpoints/<checkpoint-id>.json
    runs/<run-id>/request.json
    runs/<run-id>/result.json
    runs/<run-id>/gates.jsonl
  artifacts/
    research-framing/
    literature-intelligence/
    novelty-audit/
```

---

## Task 1: Establish repository and Windows environment

**Files:**

- Create: `.gitignore`
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `SECURITY.md`
- Create: `SOURCE_MANIFEST.yaml` with `sources: []`
- Create: `src/research_skills_os/__init__.py`
- Create: `tests/test_package_smoke.py`

**Step 1: Write the failing package smoke test**

```python
def test_package_exposes_version():
    import research_skills_os

    assert research_skills_os.__version__ == "0.1.0"
```

**Step 2: Verify failure**

Run `py -3.12 -m pytest tests/test_package_smoke.py -q`.

Expected: FAIL because the package is not installed/importable.

**Step 3: Add minimal packaging**

Use `hatchling`; runtime dependencies `pydantic>=2.11,<3`, `PyYAML>=6.0.2,<7`, `filelock>=3.18,<4`; development dependencies `pytest>=8.3,<9`, `pytest-cov>=6,<7`, `ruff>=0.12,<1`, `mypy>=1.17,<2`. Configure Ruff for Python 3.12 and mypy strict mode. Reserve console command `research-os = research_skills_os.cli:main`.

Create `.venv` with Python 3.12 and install the project in editable development mode. Do not mutate Hermes or the Codex bundled runtime.

**Step 4: Verify pass**

Run `.\.venv\Scripts\python.exe -m pytest tests/test_package_smoke.py -q`.

Expected: PASS.

**Step 5: Commit**

```powershell
git add .gitignore .python-version pyproject.toml README.md SECURITY.md SOURCE_MANIFEST.yaml src tests/test_package_smoke.py
git commit -m "build: initialize research skills os"
```

---

## Task 2: Define canonical contracts and schemas

**Files:**

- Create: `src/research_skills_os/core/__init__.py`
- Create: `src/research_skills_os/core/contracts/__init__.py`
- Create: `src/research_skills_os/core/contracts/enums.py`
- Create: `src/research_skills_os/core/contracts/models.py`
- Create: `src/research_skills_os/core/contracts/schema_export.py`
- Create: `src/research_skills_os/schemas/execution-request.schema.json`
- Create: `src/research_skills_os/schemas/execution-result.schema.json`
- Create: `src/research_skills_os/schemas/artifact-envelope.schema.json`
- Create: `src/research_skills_os/schemas/gate-result.schema.json`
- Create: `src/research_skills_os/schemas/checkpoint.schema.json`
- Create: `tests/contract/test_contract_models.py`
- Create: `tests/contract/test_schema_snapshots.py`

**Step 1: Write failing model tests**

Cover valid standalone/workflow requests; unknown contract versions; unsupported modes/targets; relative input paths; all five run statuses; blocking gates inside a completed result; and lowercase 64-character artifact hashes.

Public types:

```python
class RunMode(str, Enum): ...
class TargetKind(str, Enum): ...
class RunStatus(str, Enum): ...
class GateStatus(str, Enum): ...
class GateSeverity(str, Enum): ...
class ExecutionRequest(BaseModel): ...
class ExecutionResult(BaseModel): ...
class ArtifactEnvelope(BaseModel): ...
class GateResult(BaseModel): ...
class Checkpoint(BaseModel): ...
```

**Step 2: Verify failure**

Run `.\.venv\Scripts\python.exe -m pytest tests/contract/test_contract_models.py -q`.

Expected: FAIL on missing modules.

**Step 3: Implement minimum strict models**

Use Pydantic with `extra="forbid"`, contract version literal `1.0`, UTC-aware timestamps, and pure syntactic validation for project-relative paths.

**Step 4: Add schema snapshot test, export, and verify**

The test calls `export_schemas(destination)` and compares normalized JSON to committed schemas. Run the exporter twice; the second run must create no Git diff.

Run `.\.venv\Scripts\python.exe -m pytest tests/contract -q`.

Expected: PASS.

**Step 5: Commit**

```powershell
git add src/research_skills_os/core src/research_skills_os/schemas tests/contract
git commit -m "feat: define versioned execution contracts"
```

---

## Task 3: Implement project paths and artifact store

**Files:**

- Create: `src/research_skills_os/core/errors.py`
- Create: `src/research_skills_os/core/artifacts/__init__.py`
- Create: `src/research_skills_os/core/artifacts/paths.py`
- Create: `src/research_skills_os/core/artifacts/store.py`
- Create: `tests/unit/artifacts/test_paths.py`
- Create: `tests/unit/artifacts/test_store.py`
- Create: `tests/fixtures/artifacts/research-brief.md`

**Step 1: Write failing path-security tests**

Test `resolve_project_path(project_root, relative_path)` with a normal path, spaces/CJK, `..`, drive-absolute and UNC paths, symlink escape, and Windows junction escape (`os.path.isjunction`). Escapes raise `ProjectPathViolation`.

**Step 2: Implement containment**

Resolve root and candidate, compare with `os.path.commonpath`, and reject escaping symlink/junction ancestors. Never use string-prefix comparison.

**Step 3: Write failing store tests**

Test `ArtifactStore.register()` and `verify()` for SHA-256, project-relative paths, source links, human-edited/verification fields, drift detection, and missing/escaping files.

**Step 4: Implement and verify**

Register the existing human-readable artifact; do not hide it in a database. Run `.\.venv\Scripts\python.exe -m pytest tests/unit/artifacts -q`.

Expected: PASS.

**Step 5: Commit**

```powershell
git add src/research_skills_os/core/errors.py src/research_skills_os/core/artifacts tests/unit/artifacts tests/fixtures
git commit -m "feat: add secure artifact registry"
```

---

## Task 4: Add append-only events and project state

**Files:**

- Create: `src/research_skills_os/core/state/__init__.py`
- Create: `src/research_skills_os/core/state/models.py`
- Create: `src/research_skills_os/core/state/event_log.py`
- Create: `src/research_skills_os/core/state/reducer.py`
- Create: `src/research_skills_os/core/state/repository.py`
- Create: `tests/unit/state/test_event_log.py`
- Create: `tests/unit/state/test_reducer.py`
- Create: `tests/unit/state/test_repository.py`

**Step 1: Write failing event-log tests**

Cover event types `project_initialized`, `run_started`, `target_started`, `artifact_registered`, `decision_recorded`, `uncertainty_recorded`, `gate_recorded`, `target_completed`, `checkpoint_created`, `run_paused`, `run_blocked`, and `run_completed`. Test JSONL round-trip, sequence numbers, UTC timestamps, malformed lines, and concurrent serialization through `FileLock`.

**Step 2: Implement `EventLog`**

```python
class EventLog:
    def append(self, event: ProjectEvent) -> ProjectEvent: ...
    def read_all(self) -> list[ProjectEvent]: ...
```

Flush and `os.fsync` while holding the project lock.

**Step 3: Write reducer tests and implement replay**

Test deterministic replay, invalid duplicate terminal transitions, artifact/target accumulation, and one active run. `reduce_events()` stays pure; V1 rebuilds state from JSONL rather than introducing a database.

**Step 4: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/state -q
git add src/research_skills_os/core/state tests/unit/state
git commit -m "feat: persist auditable project state"
```

---

## Task 5: Add atomic checkpoints and verified resume

**Files:**

- Create: `src/research_skills_os/core/checkpoint/__init__.py`
- Create: `src/research_skills_os/core/checkpoint/service.py`
- Create: `tests/unit/checkpoint/test_checkpoint_service.py`
- Create: `tests/integration/test_checkpoint_resume.py`

**Step 1: Write failing tests**

Test creation after a completed target, validation before publication, temp-file plus `os.replace`, retention, atomic current pointer, resume lookup, state/artifact hashes, drift reporting, and simulated replace failure preserving the old pointer.

**Step 2: Implement `CheckpointService`**

```python
class CheckpointService:
    def create(self, state: ProjectState, completed_target: str) -> Checkpoint: ...
    def load(self, checkpoint_id: str) -> Checkpoint: ...
    def current(self) -> Checkpoint | None: ...
    def verify_resume(self, checkpoint_id: str) -> ResumeVerification: ...
```

Use sortable timestamp-plus-UUID IDs. Append `checkpoint_created` only after checkpoint and pointer are durable.

**Step 3: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/checkpoint tests/integration/test_checkpoint_resume.py -q
git add src/research_skills_os/core/checkpoint tests/unit/checkpoint tests/integration/test_checkpoint_resume.py
git commit -m "feat: add durable checkpoints and resume verification"
```

---

## Task 6: Build named gates and blocking policy

**Files:**

- Create: `src/research_skills_os/core/gates/__init__.py`
- Create: `src/research_skills_os/core/gates/protocol.py`
- Create: `src/research_skills_os/core/gates/registry.py`
- Create: `src/research_skills_os/core/gates/runner.py`
- Create: `src/research_skills_os/core/gates/builtin.py`
- Create: `tests/unit/gates/test_registry.py`
- Create: `tests/unit/gates/test_runner.py`
- Create: `tests/unit/gates/test_builtin_gates.py`

**Step 1: Write failing runner tests**

```python
class Gate(Protocol):
    gate_id: str
    gate_version: str
    def evaluate(self, context: GateContext) -> GateResult: ...
```

Test deterministic ordering, duplicate rejection, all gate statuses, blocking aggregation, and sanitized exception conversion.

**Step 2: Implement registry and runner**

Return all findings instead of stopping after the first. `GatePolicy` decides whether transition is blocked; security and integrity failures always block.

**Step 3: Add and pass built-in gate tests**

V1 gates: `contract.valid`, `inputs.required`, `artifacts.integrity`, `provenance.complete`, `uncertainty.explicit`, `checkpoint.consistent`, `provider.policy`.

Run `.\.venv\Scripts\python.exe -m pytest tests/unit/gates -q`.

**Step 4: Commit**

```powershell
git add src/research_skills_os/core/gates tests/unit/gates
git commit -m "feat: enforce structured research quality gates"
```

---

## Task 7: Register and route capability/workflow specifications

**Files:**

- Create: `src/research_skills_os/core/registry/__init__.py`
- Create: `src/research_skills_os/core/registry/models.py`
- Create: `src/research_skills_os/core/registry/loader.py`
- Create: `src/research_skills_os/core/router.py`
- Create: `tests/unit/registry/test_loader.py`
- Create: `tests/unit/test_router.py`
- Create: `tests/fixtures/registry/valid-capability.yaml`
- Create: `tests/fixtures/registry/invalid-workflow-embedded-prompt.yaml`

**Step 1: Write failing registry tests**

`CapabilitySpec` declares ID, version, input/output types, gates, specializations, providers, resumability, network, and side effects. `WorkflowSpec` declares nodes, edges, artifact mappings, gates, checkpoints, and mode stops.

Reject workflow YAML containing prompt, rubric, script body, or academic-instruction fields. Reject duplicate/unknown capability IDs and unbounded cycles; V1 workflows are acyclic.

**Step 2: Implement strict YAML loading**

Use Pydantic, sorted discovery, and duplicate-ID rejection.

**Step 3: Write and pass router tests**

`Router.resolve(request.target)` returns a `CapabilitySpec` or `WorkflowSpec`. V1 uses exact target IDs, not fuzzy routing. Unknown targets return `UnknownTarget` plus registered IDs.

Run `.\.venv\Scripts\python.exe -m pytest tests/unit/registry tests/unit/test_router.py -q`.

**Step 4: Commit**

```powershell
git add src/research_skills_os/core/registry src/research_skills_os/core/router.py tests/unit/registry tests/unit/test_router.py tests/fixtures/registry
git commit -m "feat: separate capability and workflow registries"
```

---

## Task 8: Implement coordinator and three stop policies

**Files:**

- Create: `src/research_skills_os/core/orchestrator/__init__.py`
- Create: `src/research_skills_os/core/orchestrator/coordinator.py`
- Create: `src/research_skills_os/core/orchestrator/transitions.py`
- Create: `src/research_skills_os/core/orchestrator/stop_policy.py`
- Create: `src/research_skills_os/cli.py`
- Create: `src/research_skills_os/cli_io.py`
- Create: `tests/unit/orchestrator/test_transitions.py`
- Create: `tests/unit/orchestrator/test_stop_policy.py`
- Create: `tests/integration/test_run_lifecycle.py`
- Create: `tests/integration/cli/test_run_lifecycle_commands.py`

**Step 1: Write failing lifecycle tests**

Allowed transitions:

```text
created → running → completed
                  → paused
                  → blocked
                  → failed
paused  → running
blocked → running only after a remediation/user decision
```

Reject completion when mandatory gates fail or outputs are missing.

**Step 2: Implement coordinator**

```python
class RunCoordinator:
    def start(self, request: ExecutionRequest) -> RunContext: ...
    def begin_target(self, run_id: str, target_id: str) -> RunContext: ...
    def complete_target(self, run_id: str, result: ExecutionResult) -> TransitionOutcome: ...
    def resume(self, resume_token: str, decision: ResumeDecision) -> RunContext: ...
```

The coordinator appends events, runs gates, and checkpoints. It does not generate scholarly content.

**Step 3: Write failing stop-policy tests**

Test interactive pause after one target; checkpointed pause at human review, material uncertainty, conflicting evidence, or new provider use; autonomous continuation to terminal/blocker; global security/integrity stops in every mode; and checkpoints at all target boundaries.

**Step 4: Add the minimal lifecycle CLI used by skills**

Before capability skills are written, expose `project init`, `run start`, `target begin`, `target complete`, `checkpoint verify`, and `run status`. Use stdlib `argparse`, stable JSON stdout, diagnostic stderr, and no shell execution. Add failing subprocess tests first.

**Step 5: Implement policies, verify, and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/orchestrator tests/integration/test_run_lifecycle.py tests/integration/cli/test_run_lifecycle_commands.py -q
git add src/research_skills_os/core/orchestrator src/research_skills_os/cli.py src/research_skills_os/cli_io.py tests/unit/orchestrator tests/integration/test_run_lifecycle.py tests/integration/cli/test_run_lifecycle_commands.py
git commit -m "feat: coordinate resumable runs across three modes"
```

---

## Task 9: Add local/manual provider boundary

**Files:**

- Create: `src/research_skills_os/providers/__init__.py`
- Create: `src/research_skills_os/providers/protocol.py`
- Create: `src/research_skills_os/providers/local_manual.py`
- Create: `src/research_skills_os/providers/registry.py`
- Create: `tests/unit/providers/test_local_manual.py`
- Create: `tests/unit/providers/test_policy.py`

**Step 1: Write failing tests**

Define `ProviderDeclaration` and `ProviderResult`. The default provider reads only registered project artifacts, declares no network/secrets, adds content hashes, and cannot mark imported material verified automatically. A network provider under `network: deny` must be blocked even if registered.

**Step 2: Implement default provider**

Do not implement Qinyan or another live provider in V1. Include an adapter protocol and fixture-only fake provider for tests.

**Step 3: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/providers -q
git add src/research_skills_os/providers tests/unit/providers
git commit -m "feat: add privacy-first provider boundary"
```

---

## Task 10: Implement standalone `research-framing`

**Files:**

- Create: `src/research_skills_os/capabilities/__init__.py`
- Create: `src/research_skills_os/capabilities/research_framing/__init__.py`
- Create: `src/research_skills_os/capabilities/research_framing/capability.yaml`
- Create: `src/research_skills_os/capabilities/research_framing/schemas/research-brief.schema.json`
- Create: `src/research_skills_os/capabilities/research_framing/gates.py`
- Create: `skills/research-framing/SKILL.md`
- Create: `skills/research-framing/references/framing-rubric.md`
- Create: `skills/research-framing/assets/research-brief.template.md`
- Create: `skills/research-framing/assets/research-brief.template.yaml`
- Create: `tests/unit/capabilities/test_research_framing_gates.py`
- Create: `tests/acceptance/research-framing/normal.md`
- Create: `tests/acceptance/research-framing/underspecified.md`
- Create: `tests/acceptance/research-framing/no-fabrication.md`
- Modify: `SOURCE_MANIFEST.yaml`

**Step 1: Write failing deterministic gate tests**

Require phenomenon/problem, unit/level, population/context, temporal/geographic scope or explicit unknown, constructs, questions, provisional contribution type, assumptions, uncertainties, and user decisions. Reject hidden scope guesses and unsupported literature/novelty claims.

**Step 2: Implement schema and gates**

Keep semantic judgment in the skill rubric; deterministic gates check presence, traceability, consistency, and unsupported claim forms.

**Step 3: Write skill using `superpowers:writing-skills`**

The skill accepts direct material or an OS request, invokes kernel start/complete, uses templates, externalizes uncertainty, obeys mode stops, never claims novelty, and returns the five-field low-load status.

Before adapting text or mechanisms, add exact local-source hashes, reuse mode, modifications, license/security status, and planned tests to `SOURCE_MANIFEST.yaml`. Use installed `ssci-research-framing` only as a seed without modifying it.

**Step 4: Run structural and behavioral tests**

Use baseline then refined runs for all three acceptance prompts. Save transcripts under `tests/acceptance/research-framing/results/`. Expected: complete artifacts for normal input, explicit unknowns for underspecified input, and refusal of fabricated support.

**Step 5: Commit**

```powershell
git add SOURCE_MANIFEST.yaml src/research_skills_os/capabilities/research_framing skills/research-framing tests/unit/capabilities/test_research_framing_gates.py tests/acceptance/research-framing
git commit -m "feat: add standalone research framing capability"
```

---

## Task 11: Implement standalone `literature-intelligence`

**Files:**

- Create: `src/research_skills_os/capabilities/literature_intelligence/__init__.py`
- Create: `src/research_skills_os/capabilities/literature_intelligence/capability.yaml`
- Create: `src/research_skills_os/capabilities/literature_intelligence/schemas/search-ledger.schema.json`
- Create: `src/research_skills_os/capabilities/literature_intelligence/schemas/source-registry.schema.json`
- Create: `src/research_skills_os/capabilities/literature_intelligence/schemas/evidence-map.schema.json`
- Create: `src/research_skills_os/capabilities/literature_intelligence/gates.py`
- Create: `skills/literature-intelligence/SKILL.md`
- Create: `skills/literature-intelligence/references/search-protocol.md`
- Create: `skills/literature-intelligence/references/evidence-status.md`
- Create: `skills/literature-intelligence/assets/search-ledger.template.yaml`
- Create: `skills/literature-intelligence/assets/source-registry.template.yaml`
- Create: `skills/literature-intelligence/assets/evidence-map.template.yaml`
- Create: `tests/unit/capabilities/test_literature_intelligence_gates.py`
- Create: `tests/acceptance/literature-intelligence/local-sources.md`
- Create: `tests/acceptance/literature-intelligence/missing-source.md`
- Create: `tests/acceptance/literature-intelligence/fake-citation-pressure.md`
- Create: `tests/fixtures/literature/sample-source-records.yaml`
- Modify: `SOURCE_MANIFEST.yaml`

**Step 1: Write failing gate tests**

Require query/date/source ledger, inclusion/exclusion reasons, provenance, coverage limits, existing claim-to-source links, and status vocabulary: `candidate`, `retrieved`, `screened`, `verified_metadata`, `verified_content`, `excluded`. Metadata verification must remain separate from content verification.

**Step 2: Implement schemas and gates**

Before adaptation, record exact AI Research Writing source files, commit, license/security review, modifications, and local tests in `SOURCE_MANIFEST.yaml`. Adapt handoff/blocker and citation-lock mechanisms. Do not copy live network verification into the offline V1 path.

**Step 3: Write and behavior-test the skill**

Accept a research brief or direct search question. Default to local/manual sources. When sources are absent, produce a search plan and honest blocker/uncertainty status rather than results.

**Step 4: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_literature_intelligence_gates.py -q
git add SOURCE_MANIFEST.yaml src/research_skills_os/capabilities/literature_intelligence skills/literature-intelligence tests/unit/capabilities/test_literature_intelligence_gates.py tests/acceptance/literature-intelligence tests/fixtures/literature
git commit -m "feat: add traceable literature intelligence capability"
```

---

## Task 12: Implement standalone `novelty-audit`

**Files:**

- Create: `src/research_skills_os/capabilities/novelty_audit/__init__.py`
- Create: `src/research_skills_os/capabilities/novelty_audit/capability.yaml`
- Create: `src/research_skills_os/capabilities/novelty_audit/schemas/novelty-audit.schema.json`
- Create: `src/research_skills_os/capabilities/novelty_audit/gates.py`
- Create: `skills/novelty-audit/SKILL.md`
- Create: `skills/novelty-audit/references/novelty-framework.md`
- Create: `skills/novelty-audit/references/verdict-rules.md`
- Create: `skills/novelty-audit/assets/novelty-matrix.template.md`
- Create: `skills/novelty-audit/assets/novelty-audit.template.yaml`
- Create: `tests/unit/capabilities/test_novelty_audit_gates.py`
- Create: `tests/acceptance/novelty-audit/defensible.md`
- Create: `tests/acceptance/novelty-audit/insufficient-evidence.md`
- Create: `tests/acceptance/novelty-audit/overclaim-request.md`
- Modify: `SOURCE_MANIFEST.yaml`

**Step 1: Write failing gate tests**

Require nearest-work rows, comparison dimensions, evidence for every material novelty claim, contribution classification, verdict (`defensible`, `conditional`, `insufficient_evidence`, `contradicted`), certainty consistent with verification status, and a revision recommendation for non-defensible verdicts.

Fail when `defensible` relies only on candidate/unretrieved sources or absence of search results is treated as novelty proof.

**Step 2: Implement schema and gates**

Before adaptation, record exact AcademicSkills and Spark source files, commits, license/security review, modifications, and local tests in `SOURCE_MANIFEST.yaml`. Adapt their ideation and story/novelty-lint concepts without fixed idea counts, scores, or CS assumptions.

**Step 3: Write and behavior-test the skill**

A negative novelty conclusion is a successful scholarly outcome. Test pressure to exaggerate novelty and ensure evidence certainty is preserved.

**Step 4: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/capabilities/test_novelty_audit_gates.py -q
git add SOURCE_MANIFEST.yaml src/research_skills_os/capabilities/novelty_audit skills/novelty-audit tests/unit/capabilities/test_novelty_audit_gates.py tests/acceptance/novelty-audit
git commit -m "feat: add evidence-bounded novelty audit"
```

---

## Task 13: Compose `idea-to-novelty`

**Files:**

- Create: `src/research_skills_os/workflows/__init__.py`
- Create: `src/research_skills_os/workflows/idea_to_novelty/__init__.py`
- Create: `src/research_skills_os/workflows/idea_to_novelty/workflow.yaml`
- Create: `skills/idea-to-novelty/SKILL.md`
- Create: `skills/research-os/SKILL.md`
- Create: `skills/research-os/references/execution-protocol.md`
- Create: `tests/contract/test_workflow_separation.py`
- Create: `tests/integration/test_idea_to_novelty_workflow.py`
- Create: `tests/acceptance/idea-to-novelty/interactive.md`
- Create: `tests/acceptance/idea-to-novelty/checkpointed.md`
- Create: `tests/acceptance/idea-to-novelty/autonomous.md`
- Create: `tests/acceptance/idea-to-novelty/resume.md`

**Step 1: Write failing separation test**

Assert that the workflow references registered capability IDs and contains no prompts, rubrics, templates, or scholarly rules. Assert every capability remains directly routable.

**Step 2: Write failing integration tests**

With deterministic fixture results, test identical standalone/composed specs, artifact mappings, per-node checkpoints, all three mode stops, autonomous provenance blocking, boundary resume without rerun, and drift-triggered explicit rerun.

**Step 3: Implement workflow and thin skills**

`research-os` routes and coordinates. `idea-to-novelty` selects the preset. Both defer academic work to the capability skills and use kernel lifecycle commands.

**Step 4: Verify and behavior-test**

Run `.\.venv\Scripts\python.exe -m pytest tests/contract/test_workflow_separation.py tests/integration/test_idea_to_novelty_workflow.py -q`, then run four behavioral scenarios and retain outputs.

**Step 5: Commit**

```powershell
git add src/research_skills_os/workflows skills/research-os skills/idea-to-novelty tests/contract/test_workflow_separation.py tests/integration/test_idea_to_novelty_workflow.py tests/acceptance/idea-to-novelty
git commit -m "feat: compose idea to novelty workflow"
```

---

## Task 14: Harden and complete the deterministic CLI

**Files:**

- Modify: `src/research_skills_os/cli.py`
- Modify: `src/research_skills_os/cli_io.py`
- Create: `tests/integration/cli/test_project_commands.py`
- Create: `tests/integration/cli/test_run_commands.py`
- Create: `tests/integration/cli/test_checkpoint_commands.py`

**Step 1: Write failing CLI tests**

Cover:

```text
research-os project init --root <path> --project-id <id>
research-os validate request <file>
research-os run start --request <file>
research-os target begin --run <id> --target <id>
research-os target complete --run <id> --result <file>
research-os checkpoint list --project <path>
research-os checkpoint verify --project <path> --id <id>
research-os run status --project <path> --json
```

Assert JSON stdout, diagnostic stderr, and exit codes: `0` success, `2` validation, `3` blocked gate, `4` integrity/security, `5` execution failure.

Test Windows paths with spaces/CJK and the real Python executable. Add a regression for AI Research Writing's Windows `shlex.split()` failure: already-tokenized argv must never be reparsed with POSIX rules.

**Step 2: Implement with stdlib `argparse`**

Do not add a CLI framework. Never invoke a shell.

**Step 3: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/cli -q
git add src/research_skills_os/cli.py src/research_skills_os/cli_io.py tests/integration/cli
git commit -m "feat: expose windows-safe research os cli"
```

---

## Task 15: Create and validate `SOURCE_MANIFEST.yaml`

**Files:**

- Modify: `SOURCE_MANIFEST.yaml`
- Create: `src/research_skills_os/schemas/source-manifest.schema.json`
- Create: `src/research_skills_os/core/provenance/manifest.py`
- Create: `docs/architecture/upstream-source-audit.md`
- Create: `NOTICE.md`
- Create: `tests/contract/test_source_manifest.py`
- Create: `tests/fixtures/manifest/invalid-missing-license.yaml`
- Create: `tests/fixtures/manifest/invalid-adapted-without-tests.yaml`

**Step 1: Write failing manifest tests**

Require capability, repository, full commit, source file, reuse mode, modifications, SPDX/source license, security declarations, and upstream/local tests. `verbatim`, `extracted`, and `adapted` need local targets; `adapted` needs a modification and local test; networked sources need endpoint/security notes; uncertain per-skill licenses block acceptance.

**Step 2: Implement validator and audited entries**

Use locked commits:

- AI Research Writing `5d6e4244e532189099ca5a9c5585b23febcae955`;
- Spark-to-Paper `c17149def034bc777462de612926c8e3b6d01b8c`;
- SciPilot Figure `43098ddb9e6a6d142218540c114f9ed38922fc42` as V1 `reference_only`;
- AcademicSkills `71e9c42c60636602e87985f4306d134a3b63809e`;
- Qinyan `646429a4eeb765360f6ce13b5936334225d52af8` as optional/reference only;
- seven local SSCI skills with file hashes and local provenance.

Recheck exact source paths against local upstream repositories. Do not infer root license when a subdirectory differs.

**Step 3: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_source_manifest.py -q
git add SOURCE_MANIFEST.yaml NOTICE.md src/research_skills_os/core/provenance src/research_skills_os/schemas/source-manifest.schema.json docs/architecture/upstream-source-audit.md tests/contract/test_source_manifest.py tests/fixtures/manifest
git commit -m "docs: record auditable upstream reuse"
```

---

## Task 16: Document and demonstrate the local workflow

**Files:**

- Modify: `README.md`
- Create: `docs/operator-guide/quickstart.md`
- Create: `docs/operator-guide/standalone-capabilities.md`
- Create: `docs/operator-guide/run-modes.md`
- Create: `docs/operator-guide/checkpoints-and-resume.md`
- Create: `docs/operator-guide/privacy-and-providers.md`
- Create: `examples/idea-to-novelty/idea.md`
- Create: `examples/idea-to-novelty/local-sources/source-registry.yaml`
- Create: `examples/idea-to-novelty/requests/interactive.yaml`
- Create: `examples/idea-to-novelty/requests/checkpointed.yaml`
- Create: `examples/idea-to-novelty/requests/autonomous.yaml`
- Create: `tests/acceptance/test_documented_commands.py`

**Step 1: Write failing documentation-command test**

Extract marked PowerShell commands from quickstart and execute them in a temporary path containing spaces/CJK. It must fail until commands and fixtures exist.

**Step 2: Write operator guides**

Show independent calls, composed calls, three modes, close/resume, provenance/uncertainty inspection, offline evidence, privacy decisions, and blocking-gate recovery.

**Step 3: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_documented_commands.py -q
git add README.md docs/operator-guide examples tests/acceptance/test_documented_commands.py
git commit -m "docs: add standalone and workflow operator guides"
```

---

## Task 17: Run full V1 acceptance and review

**Files:**

- Create: `docs/architecture/v1-acceptance-report.md`
- Create: `tests/acceptance/fixtures/end-to-end-project/`
- Modify only when tests expose defects: files from Tasks 1–16

**Step 1: Run deterministic quality checks**

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
.\.venv\Scripts\python.exe -m mypy src/research_skills_os
.\.venv\Scripts\python.exe -m pytest --cov=research_skills_os --cov-report=term-missing --cov-fail-under=90
git diff --check
```

Expected: all exit 0. Add meaningful tests rather than lowering coverage.

**Step 2: Validate five skills structurally**

Run skill-creator validation for `research-os`, `research-framing`, `literature-intelligence`, `novelty-audit`, and `idea-to-novelty`.

**Step 3: Run behavioral red-team cases**

Following `superpowers:writing-skills`, test requests to skip search and claim novelty, fabricate citations, fill missing scope silently, ignore hash drift, cross privacy/integrity gates, copy prompts into workflow, and resume after editing without reporting drift. Record prompts, outputs, gates, and judgments.

**Step 4: Run clean end-to-end demonstration**

Initialize a new project; call each capability independently; run the same fixture through the workflow; compare artifact schemas/versions; stop/resume checkpointed mode; confirm no key or network call was used.

**Step 5: Request code review and resolve findings**

Use `superpowers:requesting-code-review`, then `superpowers:receiving-code-review` before applying each finding. Rerun affected checks.

**Step 6: Commit acceptance evidence**

```powershell
git add docs/architecture/v1-acceptance-report.md tests/acceptance/fixtures/end-to-end-project
git commit -m "test: verify research skills os v1 acceptance"
```

Do not call V1 complete until `superpowers:verification-before-completion` inspects fresh output.

---

## Task 18: Install accepted skills safely

**Files:**

- Create: `scripts/install-skills.ps1`
- Create: `scripts/uninstall-skills.ps1`
- Create: `tests/integration/install/test_install_scripts.py`
- Create after install: `docs/architecture/local-install-record.md`

**Step 1: Write failing installer tests with a temporary skill home**

Test dry-run targets, copying only five skills, preservation of unrelated skills, collision failure unless explicit backup/replace, recoverable backups, record-scoped uninstall, idempotence, and source/installed hash equality.

**Step 2: Implement safe native PowerShell scripts**

Resolve absolute source/target paths before recursive copy/move. Never delete or overwrite an unrecorded directory.

**Step 3: Test temporary installation**

Run `.\.venv\Scripts\python.exe -m pytest tests/integration/install -q`.

**Step 4: Dry-run and install locally**

Run `-WhatIf` against the actual local skill home. Confirm the seven installed `ssci-*` skills are not targets. After Tasks 1–17 pass, install only the five namespaced skills and record commit, paths, hashes, time, and rollback command.

**Step 5: Smoke-test discovery**

Use a fresh isolated skill-discovery context to verify all five are discoverable, then run a minimal local-fixture call for each capability and the workflow.

**Step 6: Commit tooling and record**

```powershell
git add scripts tests/integration/install docs/architecture/local-install-record.md
git commit -m "build: install accepted research os skills safely"
```

---

## Task 19: Freeze V1 and prepare later slices

**Files:**

- Create: `CHANGELOG.md`
- Create: `docs/roadmap/post-v1-slices.md`
- Create: `docs/roadmap/v2-decision-inputs.md`

**Step 1: Record compatibility guarantees**

Document contract `1.0`, five installed skills, IDs, state layout, migration promise, and limitations.

**Step 2: Rank later vertical slices without implementing them**

1. evidence synthesis + theory architecture;
2. research design + method audit;
3. evidence interpretation + numeric verification;
4. paper architecture + section drafting + bilingual alignment;
5. figure intelligence;
6. citation verification + reviewer simulation + revision;
7. publication packaging.

For each, list decisions, upstream sources, providers, gates, and acceptance artifacts.

**Step 3: Run final verification**

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m mypy src/research_skills_os
.\.venv\Scripts\python.exe -m pytest --cov=research_skills_os --cov-fail-under=90
git status --short
```

Expected: checks pass and worktree is clean after the final commit.

**Step 4: Commit**

```powershell
git add CHANGELOG.md docs/roadmap
git commit -m "docs: freeze v1 and define post-v1 slices"
```

## Definition of done

V1 is done only when:

- all 19 tasks and verification commands pass;
- the three capabilities work independently;
- the workflow references rather than duplicates them;
- state survives task interruption and resumes with drift checks;
- the three modes match the design;
- evidence uncertainty and negative novelty findings remain visible;
- the default path is offline and needs no secret;
- `SOURCE_MANIFEST.yaml` passes source/license/security/test validation;
- all five skills pass structural and behavioral tests;
- installation is reversible and preserves existing SSCI skills;
- a fresh verification run and acceptance report exist.

## Post-V1 rule

Do not expand this plan in place to cover the complete manuscript lifecycle. After V1 acceptance, create a design amendment and a new implementation plan for the next vertical slice. Later capabilities reuse the same contracts, state, checkpoints, gates, providers, and manifest unless an explicit migration design is approved.
