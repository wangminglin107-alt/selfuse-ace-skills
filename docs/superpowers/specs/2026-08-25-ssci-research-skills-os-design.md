# SSCI Research Skills OS — Architecture and V1 Design

**Status:** Approved architecture; formal design awaiting user review  
**Date:** 2026-08-25  
**Target environment:** Local Windows workstation, Codex/ChatGPT skill runtime  
**Primary domains:** Communication studies and sociology, with SSCI-oriented research and publication workflows

## 1. Purpose

Build a maintainable local Research Skills OS whose research capabilities can be invoked in either of two ways:

1. **Standalone:** the user calls one capability with sufficient input and receives a complete, reusable artifact.
2. **Composed:** a lightweight workflow invokes the same capability through a stable contract and passes its artifacts to later capabilities.

The system must support work spread across days, expose its current state, preserve provenance and uncertainty, and allow the user to stop, inspect, revise, or resume at meaningful checkpoints. Automation must reduce execution friction without reducing SSCI-level analytical depth.

## 2. Frozen design decisions

The following decisions are architectural constraints rather than implementation preferences:

- Capabilities and workflows are separate layers.
- A capability never owns workflow progression.
- A workflow never embeds the academic logic of a capability.
- Every capability is independently callable.
- Every capability can also be composed through the shared contract.
- Checkpoints are first-class, versioned project artifacts.
- The three run modes are `interactive`, `checkpointed`, and `autonomous`.
- The default interaction protocol minimizes cognitive load: show the current goal, externalized state, smallest meaningful action, result, and one recommended next action.
- Evidence, citation, numeric, security, and reproducibility gates fail visibly. The system does not silently fabricate, downgrade, or bypass them.
- Upstream projects are reused at source level only when their source, license, security posture, adaptations, and tests are recorded in `SOURCE_MANIFEST.yaml`.
- V1 is a vertical slice, not a premature implementation of the entire research lifecycle.

## 3. Scope

### 3.1 V1 deliverable

V1 establishes the OS kernel and proves one useful end-to-end route:

```text
research-framing
    → literature-intelligence
    → novelty-audit
    → checkpoint
```

It contains:

- shared request/result contracts;
- project state and checkpoint persistence;
- capability registry and router;
- gate registry and gate runner;
- run-mode semantics;
- three independently callable capabilities;
- one `idea-to-novelty` workflow;
- provider interfaces with a local/manual provider as the default;
- provenance, uncertainty, and decision logs;
- `SOURCE_MANIFEST.yaml`;
- Windows-compatible automated tests and operator documentation.

### 3.2 Later increments

Later, separately specified slices may add:

- evidence synthesis and structured literature reviews;
- theory architecture;
- research design and method audit;
- quantitative, qualitative, mixed-method, SEM, and fsQCA specializations;
- evidence interpretation and numeric verification;
- figure intelligence;
- paper architecture and section drafting;
- citation verification;
- reviewer simulation and revision;
- publication packaging.

These names reserve architectural extension points. They are not V1 implementation commitments.

### 3.3 Non-goals for V1

V1 will not:

- produce a complete autonomous manuscript;
- install or require LaTeX, Quarto, Pandoc, or R;
- require a paid API or secret key;
- treat an external provider response as verified evidence;
- duplicate Zotero, Obsidian, CNKI, or existing paper-ingestion systems;
- implement a general multi-agent platform;
- hard-code journal-specific citation counts, paper sections, or figure quotas;
- install unfinished capabilities globally before acceptance tests pass.

## 4. Architectural model

```text
User / Codex / CLI
        │
        ▼
Core Research OS
  contract validation ─ router ─ orchestrator
        │                  │          │
        │                  ▼          ▼
        │             capability   workflow
        │              registry     runner
        │                  │          │
        ├──────────────────┴──────────┤
        ▼                             ▼
state + checkpoint              gate runner
        │                             │
        └──────── artifact store ─────┘
                      │
          capabilities / specializations
                      │
              provider adapters
```

### 4.1 Core Research OS

The core is deliberately academic-domain-neutral. It provides:

- contract validation and schema versioning;
- deterministic routing to a named capability or workflow;
- workflow execution without embedding capability logic;
- state transitions and append-only event recording;
- atomic checkpoints and resumption;
- artifact registration and integrity metadata;
- quality-gate execution;
- mode and stopping-policy enforcement;
- structured error and blocker reporting.

The core does not write literature reviews, judge theory, select methods, or draft manuscripts.

### 4.2 Capabilities

A capability owns one bounded research responsibility. It declares:

- stable capability identifier and version;
- accepted input artifact types;
- required and optional context;
- produced artifact types;
- entry and exit gates;
- supported specializations and providers;
- resumability behavior;
- side-effect and network declarations.

A capability receives a validated request and returns a validated result. It may recommend a next action, but it cannot invoke that action unless a workflow or user request authorizes it.

### 4.3 Workflows

A workflow is a declarative graph or ordered route containing only:

- capability identifiers;
- artifact mappings;
- conditional branches based on explicit result fields;
- gate references;
- checkpoint boundaries;
- run-mode stop policies.

It does not copy prompts, rubrics, scripts, or academic rules out of a capability.

### 4.4 Specializations

A specialization extends a capability through explicit configuration, schemas, rubrics, or adapters. It may narrow or strengthen behavior but cannot bypass the base contract or global gates.

Initial namespace:

```text
social-science/
  communication/
  sociology/
  quantitative/
  qualitative/
  mixed-methods/
  sem/
  fsqca/
```

V1 implements only the minimum communication-studies and sociology framing/novelty rules needed for the vertical slice.

### 4.5 Providers

Providers isolate external search, metadata, reference-manager, and model services. Each provider declares:

- data sent off the machine;
- required credentials;
- network endpoints;
- timeouts and retry policy;
- caching behavior;
- response schema;
- provenance fields;
- offline behavior.

Provider output is evidence input, not verified truth. Capabilities and gates remain responsible for validation.

## 5. Proposed repository structure

```text
research-skills-os/
  pyproject.toml
  README.md
  SECURITY.md
  SOURCE_MANIFEST.yaml
  src/research_skills_os/
    core/
      contracts/
      router/
      orchestrator/
      state/
      checkpoint/
      gates/
      artifacts/
    capabilities/
      research_framing/
      literature_intelligence/
      novelty_audit/
    workflows/
      idea_to_novelty/
    specializations/
      social_science/
    providers/
      local_manual/
    schemas/
  skills/
    research-framing/
    literature-intelligence/
    novelty-audit/
    idea-to-novelty/
  tests/
    contract/
    unit/
    integration/
    acceptance/
    fixtures/
  docs/
    architecture/
    operator-guide/
    superpowers/
      specs/
      plans/
  upstream/
    README.md
```

The Python package contains the reusable runtime. The `skills/` layer contains thin Codex-facing instructions that invoke the same contracts; it is not a second implementation of the research logic.

Upstream Git repositories remain in the workspace-level `work/upstream/` source area during development. The product repository stores source references, commit hashes, patches or extracted files where license-compatible, and reproducible retrieval instructions; it does not silently vendor whole repositories.

## 6. Unified execution contract

### 6.1 Request

```yaml
contract_version: "1.0"
request_id: string
project_id: string
target:
  kind: capability | workflow
  id: string
mode: interactive | checkpointed | autonomous
goal: string
inputs:
  - artifact_id: string
    type: string
    path_or_uri: string
constraints:
  language: zh | en | bilingual
  domain: communication | sociology | other
  stop_after: optional string
  network: deny | allow_declared_providers
prior_checkpoint: optional string
user_decisions: {}
```

Rules:

- A standalone invocation and a workflow invocation use the same request schema.
- Paths are resolved inside the declared project root unless explicitly allowlisted.
- Missing required inputs produce a structured blocker, not an improvised substitution.
- Network access defaults to denied unless the request and provider declaration both allow it.

### 6.2 Result

```yaml
contract_version: "1.0"
request_id: string
run_id: string
target_id: string
status: completed | completed_with_uncertainty | paused | blocked | failed
artifacts:
  - artifact_id: string
    type: string
    path: string
    sha256: string
evidence_added: []
decisions: []
uncertainties: []
gate_results: []
failed_gates: []
next_action:
  target_id: optional string
  reason: string
resume_token: optional string
```

The result distinguishes uncertainty, blockers, and execution failures. A completed result may contain uncertainty, but it may not hide a failed mandatory gate.

### 6.3 Artifact envelope

Every registered artifact carries:

- artifact ID, type, schema version, and producing capability;
- creation timestamp and project-relative path;
- content hash;
- source artifact IDs;
- evidence/provenance references;
- sensitivity classification;
- human-edited flag;
- verification state.

Academic content remains in readable Markdown, YAML, JSON, CSV, or standard document formats. The OS metadata does not trap the user in an opaque database.

## 7. State and checkpoint model

### 7.1 Project state

Project state is a materialized view rebuilt from an append-only event log. It records:

- current goal and active target;
- completed capabilities and workflows;
- registered artifacts and their hashes;
- decisions and unresolved questions;
- evidence and citation status;
- gate outcomes;
- current run mode and stopping policy;
- recommended next action;
- last durable checkpoint.

### 7.2 Checkpoint

A checkpoint is created at every capability boundary and before any user-review stop. It includes:

```yaml
checkpoint_version: "1.0"
checkpoint_id: string
project_id: string
run_id: string
completed_target: string
inputs_used: []
artifacts_created: []
key_decisions: []
evidence_added: []
uncertainties: []
failed_gates: []
recommended_next: optional string
resume_from: string
state_hash: string
created_at: string
```

Checkpoint writes are atomic: write to a temporary file, validate, then replace the current pointer. Previous checkpoints are retained. Resume verifies the state and artifact hashes before continuing. If content changed after the checkpoint, the system reports drift and asks for an explicit rebase, rerun, or accept decision.

## 8. Run modes and low-load interaction

### 8.1 Interactive

- Execute one capability or one explicitly requested workflow step.
- Save a checkpoint.
- Stop even if a next action is obvious.
- Present one recommended next action.

### 8.2 Checkpointed

- Continue across low-risk steps.
- Stop at workflow-declared human gates, material uncertainty, conflicting evidence, new external data use, or irreversible/export actions.
- Save a checkpoint at each capability boundary.

### 8.3 Autonomous

- Continue until the workflow terminal node or an unresolvable blocker.
- Never bypass mandatory evidence, citation, security, or integrity gates.
- Record all decisions, assumptions, provider calls, and checkpoints for later audit.

### 8.4 Visible response protocol

Default user-facing status is limited to five stable fields:

```text
Current goal
Current state
Smallest meaningful action
Result / blocker
One recommended next action
```

This is a presentation default, not a restriction on scholarly artifacts. Literature reviews, theory arguments, and audit reports remain as detailed as their quality requirements demand.

## 9. Gates

Gates are named, versioned validators returning structured results:

```yaml
gate_id: string
gate_version: string
status: pass | warn | fail | not_applicable
severity: info | advisory | blocking
findings: []
evidence: []
remediation: []
```

V1 gates cover:

- contract/schema validity;
- required input presence;
- artifact path containment and hash integrity;
- provenance completeness;
- explicit uncertainty labeling;
- framing completeness;
- literature-search trace completeness;
- novelty-claim support and overclaim detection;
- checkpoint consistency;
- declared network/provider policy.

Gate policy is defined by workflow and run mode, but global security and integrity gates are always blocking.

## 10. V1 capability responsibilities

### 10.1 `research-framing`

Inputs may be a phenomenon, observation, topic, draft question, or early memo. Outputs:

- `research-brief.md`;
- machine-readable research-brief metadata;
- candidate research questions;
- constructs, units of analysis, scope conditions, and contribution hypotheses;
- uncertainty and decision entries.

It does not claim novelty or invent literature support.

### 10.2 `literature-intelligence`

Inputs include a research brief or direct user-defined search problem. Outputs:

- search strategy and query ledger;
- provider/source provenance;
- candidate-source registry;
- inclusion/exclusion decisions;
- evidence map with verification status;
- coverage gaps and search limitations.

V1 must work with manually supplied sources and local files. External search adapters are optional and explicitly declared.

### 10.3 `novelty-audit`

Inputs include a research brief and literature evidence. Outputs:

- novelty matrix;
- competing nearest-work comparisons;
- contribution classification;
- unsupported or overstated claim findings;
- verdict: defensible, conditional, insufficient_evidence, or contradicted;
- recommended revision to the research question or contribution claim.

It may conclude that novelty is not established. That is a valid successful result, not a system failure.

## 11. V1 workflow: `idea-to-novelty`

```text
validate request
  → research-framing
  → framing gate
  → checkpoint
  → literature-intelligence
  → provenance + coverage gates
  → checkpoint
  → novelty-audit
  → novelty-support gate
  → terminal checkpoint
```

Mode behavior:

- `interactive`: stop after the first requested node.
- `checkpointed`: default stop after framing for scope approval and after novelty audit for contribution approval.
- `autonomous`: run the full route if inputs and provider policy permit; stop on blocking gates.

Each of the three capability nodes must pass the same acceptance tests when called outside the workflow.

## 12. Upstream source reuse strategy

### 12.1 AI Research Writing

Use as the primary mechanism source for:

- paper/project state contracts;
- research handoff and blocker semantics;
- artifact terminal checks;
- claim/evidence mapping;
- citation freshness and lock concepts;
- numeric evidence verification in later slices;
- path containment and build-record integrity.

Reuse mode: selective extraction and deep adaptation. Windows process execution must be corrected and regression-tested; POSIX command parsing will not be copied unchanged.

### 12.2 Spark-to-Paper

Use as a mechanism source for:

- explicit stage input/output trace files;
- centralized gate execution;
- story, blueprint, citation, and draft linting concepts;
- reviewer-issue close criteria.

Reuse mode: conceptual adaptation and selective extraction. Its workflow-owned capabilities, experiment automation, dependency installation, fixed CS/LaTeX assumptions, and hard-coded thresholds are excluded.

### 12.3 SciPilot Figure

Reserved for the later figure-intelligence slice:

- data profiling;
- argument-before-chart selection;
- final-size vector export;
- CJK font setup;
- deterministic clipping, glyph, and overlap checks;
- visual QA loop.

Reuse mode: script extraction plus new tests and social-science chart rules. It is not part of V1 runtime dependencies.

### 12.4 AcademicSkills

Use as a conceptual source for:

- modular parent/child routing;
- abstraction ladder;
- contradiction hunting;
- stakeholder rotation;
- failure analysis;
- cross-domain transfer.

Reuse mode: conceptual adaptation. ML-specific conference assumptions, Traditional-Chinese defaults, mandatory large idea counts, and fixed scoring are excluded.

### 12.5 Qinyan skills

Treat as an optional external provider only. Consolidate duplicated client behavior and require explicit credential, privacy, provenance, timeout, caching, and response-validation policies. Qinyan output cannot be the canonical or automatically verified evidence source.

### 12.6 Existing local SSCI skills

The seven existing SSCI skills are migration seeds for capability prompts, artifacts, bilingual conventions, and audit rubrics. They remain usable during development. V1 does not overwrite or globally replace them; accepted capability logic is migrated behind the new contract and tested before installation.

## 13. `SOURCE_MANIFEST.yaml`

Every adapted mechanism or file receives an entry with at least:

```yaml
- capability: string
  upstream_repo: owner/repository
  upstream_commit: full_sha
  source_file: repository/relative/path
  reuse_mode: verbatim | extracted | adapted | conceptual | reference_only
  local_target: optional repository/relative/path
  modifications:
    - string
  license:
    spdx: string
    source: string
    notice_required: boolean
  security:
    network: none | optional | required
    secrets: []
    subprocess: boolean
    filesystem_scope: string
    review_status: pending | approved | rejected
  tests:
    upstream: []
    local: []
  notes: optional string
```

Manifest validation fails when a copied or adapted source file lacks commit, license, security, modification, or local-test information.

## 14. Security and privacy

- Default offline operation; network access is opt-in per request and declared provider.
- Secrets come only from environment variables or an OS credential mechanism and are never written into checkpoints, logs, prompts, or fixtures.
- All file writes stay within the resolved project root or an explicit allowlist.
- Artifact and checkpoint paths reject traversal and symlink/junction escapes.
- Subprocess execution uses argument arrays, no implicit shell, an executable allowlist, timeouts, and captured logs.
- Provider logs record endpoint class, request timestamp, query hash, response hash, and policy outcome without recording secrets.
- Research materials receive a sensitivity label; provider use is blocked for material not approved to leave the machine.
- Upstream update checks do not auto-execute downloaded code.

## 15. Windows environment and dependency policy

- Create a project-local Python 3.12 virtual environment after the implementation plan is approved.
- Do not mutate the existing Hermes environment or Codex bundled runtime.
- Pin direct dependencies and record hashes through the chosen lock mechanism.
- Keep V1 runtime dependencies minimal; development and optional provider dependencies use separate groups.
- Use `pathlib` and Windows-native path tests.
- Test spaces, non-ASCII/CJK names, drive letters, long paths within practical limits, and subprocess argument handling.
- Defer LaTeX, Pandoc, Quarto, R, and figure-stack installation until a slice needs them.

## 16. Testing and acceptance

Implementation follows test-first development. The minimum test layers are:

### 16.1 Contract tests

- valid requests/results/checkpoints round-trip;
- invalid versions, modes, targets, and missing inputs fail clearly;
- independently invoked and workflow-invoked capabilities use identical schemas.

### 16.2 Unit tests

- router selection;
- state transitions;
- atomic checkpoint creation and rollback;
- hash/drift detection;
- gate aggregation and blocking policy;
- provider-policy enforcement;
- Windows path and subprocess safety.

### 16.3 Integration tests

- invoke each V1 capability independently;
- compose all three through `idea-to-novelty`;
- stop and resume from every checkpoint boundary;
- reproduce a run from recorded local fixtures;
- preserve artifacts and report a blocking gate without data loss.

### 16.4 Skill behavior tests

Each Codex-facing skill is tested against:

- a normal prompt;
- an underspecified prompt;
- a prompt attempting to skip evidence or invent citations;
- standalone invocation;
- workflow invocation;
- resume from checkpoint;
- all three run modes where applicable.

### 16.5 V1 acceptance criteria

V1 is accepted only when:

1. The three capabilities work independently from documented minimum inputs.
2. The workflow composes the same capability implementations without duplicate logic.
3. A run can stop, close, and resume with verified artifact integrity.
4. Mode behavior is observably different and matches this specification.
5. Unsupported novelty claims are blocked or labeled, never silently promoted.
6. No paid key is needed for the local-fixture acceptance path.
7. `SOURCE_MANIFEST.yaml` validates every reused mechanism.
8. All automated tests pass on the user's Windows environment.
9. Existing local SSCI skills remain unchanged until migration acceptance.
10. Operator documentation demonstrates standalone, checkpointed, and autonomous examples.

## 17. Failure and recovery behavior

- **Missing input:** return `blocked` with the exact missing artifact and smallest recovery action.
- **Provider unavailable:** retain the checkpoint; offer local/manual evidence input or an authorized alternate provider.
- **Gate failure:** save findings and artifacts, mark the target incomplete, and recommend remediation.
- **Artifact drift:** do not overwrite history; require rebase, rerun, or explicit acceptance.
- **Capability exception:** record a sanitized failure event, preserve the last valid checkpoint, and provide the resumable boundary.
- **Schema upgrade:** migrate through an explicit versioned migration; retain the original checkpoint.
- **Upstream change:** do not update silently; refresh the manifest, review diffs/security/license, and rerun affected tests.

## 18. Delivery sequence after design approval

The implementation plan will decompose V1 into small test-first tasks:

1. repository baseline and dedicated environment;
2. schemas and contract tests;
3. artifact store, event state, and checkpoints;
4. router, capability registry, and gate runner;
5. standalone `research-framing`;
6. standalone `literature-intelligence`;
7. standalone `novelty-audit`;
8. `idea-to-novelty` workflow and mode policies;
9. thin Codex skill wrappers and behavioral tests;
10. manifest, security, Windows, documentation, and acceptance verification.

Each task must name exact files, tests, commands, and expected outcomes. No later lifecycle capability is implemented inside this V1 plan.

## 19. Design review checklist

- [x] Capabilities and workflows have non-overlapping responsibilities.
- [x] Every V1 capability has a standalone input/output contract.
- [x] Workflow composition uses the same capability implementation.
- [x] Modes and checkpoint stopping behavior are explicit.
- [x] State, evidence, uncertainty, blockers, and recovery are externalized.
- [x] V1 is bounded enough for a test-first implementation plan.
- [x] Upstream reuse is source-level and auditable.
- [x] Windows-specific risks are captured.
- [x] External providers are optional and privacy-controlled.
- [x] Existing skills are preserved until migration is verified.

## 20. Decision requested

Approval of this document authorizes creation of the detailed V1 implementation plan. It does not yet authorize implementation. Material changes to the frozen boundaries, contract shape, V1 vertical slice, or provider/security policy require a design amendment before implementation.
