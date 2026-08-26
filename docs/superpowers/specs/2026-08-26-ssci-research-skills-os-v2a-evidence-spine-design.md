# SSCI Research Skills OS V2A — Evidence Spine Design

**Status:** Approved in conversation; written specification awaiting user review

**Date:** 2026-08-26

**Parent design:** `2026-08-25-ssci-research-skills-os-design.md`

**Target environment:** Local Windows workstation, Codex/ChatGPT skill runtime

**Primary domains:** Communication studies and sociology

## 1. Decision summary

V2 will be delivered as three independently useful slices rather than one large release:

1. **V2A — evidence spine:** paper knowledge base, evidence synthesis, citation verification,
   and theory architecture.
2. **V2B — empirical spine:** research design, data audit, statistical verification, and figure
   intelligence.
3. **V2C — manuscript spine:** argument architecture, section drafting, bilingual alignment,
   LaTeX packaging, peer review, revision, and reproducibility packaging.

This specification authorizes planning for V2A only. V2B and V2C remain program-level extension
points and require their own design amendments and implementation plans. The same real project is
carried across all three slices so that each slice contributes to one end-to-end research artifact
instead of producing disconnected demonstrations.

V2A preserves the V1 separation between the Core Research OS, independently callable
capabilities, and lightweight workflows. It does not create a monolithic research Skill and does
not place academic reasoning inside the workflow layer.

## 2. Why this slice comes first

The V1 route can frame a question, discover literature, and audit novelty, but it cannot yet turn
verified source content into a traceable synthesis or theory decision. Writing, statistics, and
figures would therefore lack a reliable evidence authority.

V2A creates that authority. Its central invariant is:

> A research claim may progress to theory or writing only when its source identity, exact source
> passage, locator, and support relationship remain inspectable.

Retrieval relevance, model confidence, citation metadata, and author reputation do not substitute
for content verification.

## 3. Scope

### 3.1 In scope

V2A adds four independently callable capabilities:

- `paper-knowledge-base`
- `evidence-synthesis`
- `citation-verification`
- `theory-architecture`

It also adds one lightweight workflow:

```text
literature-to-theory
  paper-knowledge-base
    → evidence-synthesis
    → citation-verification
    → theory-architecture
    → checkpoint
```

The workflow is a preset. Every node can be called alone when its minimum input contract is met.

### 3.2 Out of scope

V2A will not:

- execute statistical models or generate publication figures;
- write a complete manuscript;
- install or require a vector database, local embedding model, LaTeX, R, or a paid API;
- treat semantic search output as verified evidence;
- upload private PDFs, notes, or unpublished manuscripts without an explicit provider decision;
- scrape authenticated databases by bypassing their access controls;
- force a named theory when a descriptive or exploratory design is more defensible;
- modify or replace the seven pre-existing local SSCI Skills;
- implement the unresolved extensions for patents, presentations, mentor distillation, Visio, or
  daily arXiv digests.

## 4. Architectural choices

### 4.1 Chosen approach

V2A uses **capability-level adaptation behind stable OS contracts**. Licensed upstream mechanisms
may be copied with attribution or rewritten when adaptation is substantial. Unlicensed or
non-commercial sources may inform tests and design only; their code is not copied.

Rejected alternatives:

- **Monolithic upstream import:** fast initially, but mixes workflows with capabilities and creates
  license, security, and maintenance coupling.
- **Thin external-tool wrappers:** broad coverage, but leave evidence states, checkpoints, and
  quality gates inconsistent.

### 4.2 Core compatibility

V2A remains additive to contract `1.0`:

- no V1 event or checkpoint schema is rewritten;
- new artifact types are registered through existing capability manifests;
- `source_artifact_ids`, artifact hashes, and provenance references remain the core lineage
  mechanism;
- claim-to-passage and contradiction edges live inside V2A artifacts rather than introducing a
  global graph database;
- older V1 projects remain writable and may append V2A events after their existing artifacts pass
  integrity verification.

A contract `1.1` migration is deferred until a concrete requirement cannot be represented by
additive artifacts. V2A tests must prove that branching synthesis, checkpointing, and stale-input
detection work under contract `1.0`.

### 4.3 Offline-first provider boundary

The project-local filesystem is the source of truth for evidence content. A provider can discover
or import candidates, but it cannot mark them verified.

Provider classes are separated by data exposure:

| Class | Default | Permitted data |
|---|---:|---|
| `local-manual` | enabled | registered project artifacts only |
| public bibliographic metadata | optional | title, author, DOI, venue, public query terms |
| public full text | optional | operator-selected public URLs and files |
| authenticated literature service | disabled | only after endpoint, credential, and privacy declaration |
| model/embedding service | disabled | only after explicit disclosure of content leaving the machine |

Network clients must verify TLS certificates and fail closed. No retry may disable certificate
verification. Secrets must come from declared environment variables or the runtime secret store,
never source files, fixtures, logs, or generated reports.

## 5. Capability design

### 5.1 `paper-knowledge-base`

**Purpose:** create and maintain a durable, project-scoped corpus whose documents and locators can
be referenced across sessions.

**Minimum inputs:** one or more registered local text/PDF-derived artifacts or declared public
source records.

**Outputs:**

- `document-index.json`
- updated `source-registry.json`
- `corpus-status.json`

Each document record contains:

- stable `source_id` and bibliographic identity fields;
- local artifact ID, path, file SHA-256, and import timestamp;
- document type, language, access state, and privacy label;
- page/section map and content-block hashes;
- extraction method and extraction warnings;
- version/supersession relationship;
- metadata-verification and content-availability states.

The knowledge base does not require embeddings. V2A provides deterministic title/author/identifier
lookup and text search. Hybrid or semantic retrieval may be added later through a replaceable
provider. Retrieval results are candidate passages, not evidence rows.

**Exit gates:** file integrity, stable source identity, locator availability, duplicate/conflict
visibility, project-bound paths, and declared privacy state.

### 5.2 `evidence-synthesis`

**Purpose:** convert inspected passages into claim-addressable evidence without collapsing source
statements, author inference, contradictions, or null findings.

**Minimum inputs:** a V1 literature brief or research question plus a verified document index.

**Outputs:**

- `evidence-rows.jsonl`
- `synthesis-matrix.json`
- `contradiction-ledger.json`
- `coverage-report.json`

An evidence row contains:

- stable row ID and research-question dimension;
- `source_id`, artifact hash, exact passage, and page/section locator;
- passage language and optional user-reviewed translation;
- source claim, study context, method, population, and boundary conditions;
- evidence role: `supports`, `qualifies`, `contradicts`, `null`, or `background`;
- author inference in a separate field;
- verification status and verifier note;
- downstream claim IDs, if any.

The exact passage is authoritative. Summaries and translations never overwrite it.

The contradiction ledger groups rows that address the same construct or mechanism but disagree.
Every item records the competing claims, possible scope explanations, unresolved issue, and
materiality. A material unresolved contradiction blocks autonomous progression to a theory
decision. A non-material disagreement may remain open if the synthesis states its boundary and
does not conceal it.

**Exit gates:** exact-locator coverage, source/content hash consistency, source-versus-inference
separation, contradiction preservation, material-gap visibility, and question-dimension coverage.
There is no fixed citation-count or recency quota.

### 5.3 `citation-verification`

**Purpose:** independently verify bibliographic identity and claim support.

**Minimum inputs:** source records and, for support verification, evidence rows or manuscript
claims.

**Outputs:**

- `citation-identity-audit.json`
- `citation-support-audit.json`
- `citation-blockers.json`

Identity and support are separate states:

```text
identity: verified | mismatch | not_found | suspicious | manual_needed
support: supports | partial | misaligned | contradicted | unavailable | manual_needed
```

Rules:

- metadata-only verification can establish identity but never passage support;
- inaccessible candidates remain `unavailable` and do not count toward verified evidence coverage;
- DOI is a strong identifier for sources that use it, but is not universally mandatory;
- Chinese journal articles, books, theses, policies, standards, and reports use source-appropriate
  routes such as title-first matching, official journal/publisher records, and CNKI/Wanfang/VIP
  metadata when authorized;
- author, title, year, venue, volume/issue, pages, DOI or other stable identifier are compared as
  applicable to the source type;
- retractions, corrections, duplicate versions, and metadata conflicts remain visible blockers or
  warnings according to severity.

**Exit gates:** identity sufficiency, content-support sufficiency, route traceability, no fabricated
identifiers, and no silent downgrade from full-text to metadata-only verification.

### 5.4 `theory-architecture`

**Purpose:** construct an evidence-bounded explanation and expose the user decision among theory
candidates, integration, or a deliberately descriptive study.

**Minimum inputs:** research framing, novelty audit, verified synthesis matrix, contradiction
ledger, and citation support audit.

**Outputs:**

- `theory-candidates.json`
- `construct-map.json`
- `theory-rationale.md`
- `theory-decision-packet.json`

Each theory candidate records explanatory target, constructs, mechanisms, level of analysis,
boundary conditions, required assumptions, evidence links, tensions, and expected contribution.
The construct map distinguishes conceptual definition, operational indicator, level, role, and
near-synonym conflicts.

The decision packet may recommend:

- one primary theory;
- a bounded integration of compatible theories;
- a mechanism-centered framework without a named grand theory;
- a descriptive/exploratory study because theory support is insufficient.

The user owns the final theory decision. Autonomous mode must stop at this packet and may not
record a theory as selected without explicit authorization.

**Exit gates:** theory/evidence fit, construct consistency, level-of-analysis consistency,
assumption visibility, contradiction acknowledgement, novelty-claim compatibility, and no forced
theorization.

## 6. Workflow and run-mode behavior

### 6.1 Standalone invocation

Each capability accepts a normal OS request and stops after producing its own artifacts and
checkpoint. Examples:

- add newly downloaded papers to an existing corpus;
- verify a bibliography without running synthesis;
- rebuild a theory candidate table from an existing evidence matrix;
- synthesize one new sub-question without rerunning discovery.

### 6.2 `literature-to-theory` workflow

The workflow declares capability IDs, artifact mappings, gates, and stop policies only.

| Mode | Behavior |
|---|---|
| `interactive` | stops after each capability and presents one recommended next action |
| `checkpointed` | runs knowledge base, synthesis, and verification; stops at material contradictions and the theory decision packet |
| `autonomous` | advances through deterministic gates, but still stops at material contradictions, theory selection, privacy authorization, and any failed evidence gate |

The OS must save a checkpoint after every completed node and before every human stop. Resume uses
the checkpoint and artifact hashes, not conversational memory.

### 6.3 Human gates that no autonomous workflow may cross

Across the V2 program, these remain human-owned:

1. final research direction;
2. acceptance of a novelty claim;
3. resolution of a material evidence contradiction;
4. final theory or descriptive-framework choice;
5. research-design approval and any causal-language commitment;
6. release of private data to a provider;
7. publication, submission, filing, or other external write.

V2A implements gates 3, 4, and 6 while preserving V1 gates 1 and 2.

## 7. Error, blocker, and stale-state behavior

Errors are classified as:

- **invalid input:** schema, path, encoding, or unsupported document failure;
- **integrity failure:** missing file, content hash drift, or locator drift;
- **evidence insufficiency:** metadata-only, unavailable full text, anchorless passage, or uncovered
  research dimension;
- **identity conflict:** duplicate, DOI/title mismatch, version conflict, retraction, or correction;
- **scholarly blocker:** material contradiction, theory/evidence mismatch, or unsupported novelty
  transition;
- **provider failure:** network, credential, rate limit, endpoint, or TLS failure;
- **human decision required:** a valid packet awaits explicit user authorization.

Partial work is retained. A failed provider may leave candidates marked `retrieval_failed`, but it
cannot produce verified evidence. An upstream hash change marks affected evidence rows, synthesis
groups, citation audits, and theory artifacts stale. Unrelated branches remain valid.

## 8. Humanities and social-science specialization

The specialization layer strengthens the generic capabilities without changing their interfaces.

It must support:

- journal articles, books, chapters, theses, policies, standards, reports, and archival texts;
- Chinese and international bibliographic routes;
- qualitative, quantitative, mixed-method, historical, and interpretive evidence descriptions;
- construct ambiguity, translation alternatives, context, historical period, and level of analysis;
- negative and null evidence;
- theory pluralism and defensible descriptive work;
- exact original-language passages with page or stable section locators.

English/Chinese termbase authority and prose alignment belong to V2C. V2A may store reviewed
translations beside original passages, but only the original passage is treated as citation
evidence.

## 9. Upstream source decisions

All implementation use is conditional on a complete `SOURCE_MANIFEST.yaml` entry containing the
locked repository, commit, source file, SHA-256, reuse mode, modifications, license, security
surface, upstream tests, and local tests.

The initial capability-to-source mapping is frozen as follows. `conceptual` means no source code is
copied or executed. `adapted` permits a narrowly scoped implementation only after its exact manifest
entry and attribution pass validation.

| Capability | Upstream source file | Reuse mode | Required modification | Security boundary | Required local test family |
|---|---|---|---|---|---|
| `paper-knowledge-base` | Nature `skills/nature-academic-search/scripts/converters.py` | adapted | retain deterministic bibliography conversion; replace provider assumptions with registered project artifacts | no network in converter; project-bound paths | conversion fixtures, malformed input, stable identity |
| `paper-knowledge-base` | Nature `skills/nature-academic-search/scripts/academic_search.py` | conceptual | use only work/author normalization ideas; provider clients remain separate | declared public-metadata endpoints only | provider contract and offline fallback |
| `citation-verification` | Nature `skills/nature-citation/scripts/nature_citation.py` | adapted | preserve status/retry and author-integrity concepts; route calls through OS providers | verified TLS, declared endpoints, no embedded secrets | identity conflict, retry exhaustion, offline mode |
| `citation-verification` | PaperSpine `src/scripts/citation_quality_audit.py` | adapted | remove computer-science-specific thresholds and fixed recency assumptions | local artifacts by default | DOI/title mismatch, metadata-only, manual-needed |
| `citation-verification` | Reference Checker `SKILL.md` | conceptual | express Chinese and source-type-specific routes as schemas and gate rules | authenticated services disabled by default | Chinese no-DOI, book/thesis/policy routes |
| `citation-verification` | Humanities Thesis `scripts/search.py` | conceptual | retain provider separation and Chinese query expansion; do not reuse the HTTP client | insecure TLS fallback prohibited | fail-closed TLS and provider isolation |
| `evidence-synthesis` | PaperSpine `src/scripts/results_validation_check.py` | conceptual | generalize contribution-to-result mapping into claim-to-passage and allowed-interpretation rows | local verified content only | support/qualify/contradict/null fixtures |
| `evidence-synthesis` | Academic Research Skills `scripts/evidence_rows.py` | conceptual | independently implement exact anchors, hashes, and failure states under the OS contract | CC BY-NC code not copied | anchorless, source-missing, hash-drift fixtures |
| `theory-architecture` | local `ssci-argument-architecture/SKILL.md` | conceptual | add construct, mechanism, boundary, contradiction, and human-decision artifacts | local read-only source | level mismatch, forced-theory rejection |
| Core Research OS | Light `skills/light-orchestrator/scripts/execution_mode.py` and `workflow_ledger.py` | conceptual | retain V1 core; add only minimum-sufficient mode and human-stop tests | no runtime import or external execution | autonomous stop, dependency/join, resume |

Content hashes recorded during the source audit and required for the corresponding manifest entries:

| Source file | SHA-256 |
|---|---|
| Nature `academic_search.py` | `48a749c71f66ab000bf28795fc7e2388b26e5c22d7c0eb0500b8fc7f5d13a96f` |
| Nature `converters.py` | `25155cd7070e34f344b20c7841c22918f1733b1cd95b5cf4ca51899728692d6d` |
| Nature `nature_citation.py` | `0cdc8290bc7b9294bcc8ba99cf57f202ad24251cd8fcc4b8d07c4bbfbe9f9079` |
| PaperSpine `artifact_check.py` | `2e979463addcb31fe334ef2aaefeab3e3d4eece226f34961ca022833d8b0ad7b` |
| PaperSpine `citation_quality_audit.py` | `4d2f1717ddc19e06eb0f490d808e6ad9253d242b004eb2048ad47685196e3963` |
| PaperSpine `results_validation_check.py` | `f977562f3edfc990a6a9bd95cb11c7278cf4bb194668a2b139db7d70ffe23195` |
| Humanities Thesis `search.py` | `4e515464397fc48f52fe1b206db2c1ed28b0fb6bcc33d6129c923b267a6b9985` |
| Humanities Thesis excluded `http_client.py` | `e4bf4a6cab4b0a90a22f906fda0da68f5c4654c61b1db7d639c65883f7913901` |
| Reference Checker `SKILL.md` | `8f5ad92c6a8b2acab7ecf8f6d09934573f876927717b1ec00fc2be445928e353` |
| Academic Research Skills `evidence_rows.py` | `70fed660ae6e10a644d597338d625949f2a306ffa62a83de1d079eec0489f2c8` |
| Light `execution_mode.py` | `d78dc3a0c5b802fb83fd8907d084a5595368578d6c800c823282e4dc1d961269` |
| Light `workflow_ledger.py` | `d6c1a25078a3ad15dbde2ef18c388f4cd1de4bf899c059eda67b1c0fa60b4f2a` |

### 9.1 Eligible for source-level adaptation

| Upstream | Locked commit | Candidate source | License | V2 use |
|---|---|---|---|---|
| `Yuan1z0825/nature-skills` | `3817cd194c31010febb1312ab786e53cd8154333` | `skills/nature-academic-search/scripts/converters.py`, `skills/nature-citation/scripts/nature_citation.py`, dedup and verification references | Apache-2.0 | isolated identity normalization, retry/status patterns, deterministic format conversion |
| `WUBING2023/PaperSpine` | `360ae775639a27458d4f24040b65a4cbe935b213` | `src/scripts/artifact_check.py`, `citation_quality_audit.py`, `results_validation_check.py` | MIT | artifact gates, citation audit structure, claim-to-result checks |
| `ganzhi-black/humanities-thesis-skill` | `9f9c97162e250df8d6c214b828bb973828a2a780` | `scripts/search.py`, `scripts/lib/review_rules.py` | MIT | Chinese/international route concepts and deterministic textual checks |
| `Liuxiangjian-ai/reference-checker-skill` | `f30bd18b79f38bb24e57cad6ea0132323e329c94` | `SKILL.md` | MIT | source-type-specific Chinese citation routes and audit vocabulary |
| `Light0305/Light-skills` | `6b44f57d1274eb38a6c79dc29c2d21e5e0a225a9` | orchestrator execution-mode and workflow-ledger mechanisms | MIT | conceptual refinement of minimum-sufficient orchestration and fail-closed human gates |

The humanities-thesis HTTP client is explicitly excluded because it can retry with TLS
certificate verification disabled. No equivalent behavior is permitted locally.

### 9.2 Reserved for later licensed slices

| Upstream | Locked commit | License | Reserved use |
|---|---|---|---|
| `TingxiYu/academic-figure-skill` | `1df9940dd01ac939f072b12fe28d6353b79b90f9` | Apache-2.0 | V2B figure contract and deterministic visual QA |
| `um-dang/repro-packs` | `6ad3f433329da864b1f055bce07243ef4355bb2b` | MIT | V2C self-contained project and automated-output packaging |
| `pengjunchi0/codex-visio-paper-figure-skill` | `816960dd9608d21d3f47a2af8768c5a00464988a` | MIT | optional Windows-only editable-diagram provider after V2B |
| `handsomestWei/patent-disclosure-skill` | `424da1ae803df738e0831b36c4308018804016c2` | MIT | separate patent extension, never part of the scientific DAG |

### 9.3 Conceptual reference only

- `Imbad0202/academic-research-skills` is CC BY-NC 4.0. Its evidence-row, reproducibility-lock,
  cross-artifact invariant, and adversarial-test ideas may inform requirements, but code is not
  copied into the public project.
- `HKUSTDial/Supervisor-Skills` is CC BY-NC-SA 4.0 and remains a later, separate mentor extension.
- `JasperPWang/lab-codex-skills`, `ChenLiu-1996/figures4papers`,
  `Guangwen0429/paper-rag`, `zhangzzk/arxiv-digest-skill`, and
  `wqwshn/literature-review-workflow` have no applicable root license at the inspected commits.
  They are not code sources.

### 9.4 Rejected sources or mechanisms

- `uuforeverr/CiteVerify`: no root license and test files contain a hard-coded provider credential.
- `LiPu-jpg/PaperPilot`: fixed computer-science stages, weak hypothesis templates, and statistical
  routines without adequate assumptions, effect-size, or test coverage.
- the inspected Paper RAG implementation: tutorial-grade chunking/retrieval without durable corpus
  identity, update/delete lifecycle, or claim-to-source verification.
- arbitrary subprocess evaluation, dynamic `eval`, insecure TLS fallback, embedded credentials,
  and network-dependent tests.

Unresolved names from social posts or private distributions are not guessed. They enter the source
manifest only after an authoritative repository, license, and source file are identified.

## 10. Real-project tracer bullet

### 10.1 Project question

The cross-slice project is:

> How is daily sentiment valence associated with 30-day engagement per post across mutually
> exclusive account types in U.S. or unspecified-location English-language marijuana-related
> Twitter discourse?

The wording is explicitly associational. The project must not infer individual attitudes,
exposure, persuasion, or causal effects from aggregated daily platform data.

### 10.2 Data authority

The project uses NORC's General Social Media Archive `GSMA PowerTrack All Daily` data:

- 2,038 daily observations from 2016-08-01 through 2022-02-28;
- daily volume, VADER positive-to-negative sentiment ratio, and 30-day engagement;
- engagement defined as retweets, replies, or quotes received within 30 days of the original post;
- selected mutually exclusive groups: commercial non-bot, bot non-commercial, commercial bot,
  and other accounts;
- CSV reserve value `888888` treated as missing, never as a numeric sentiment value.

The official archive page, methodology report, data dictionary, download URL, retrieval time, and
file SHA-256 become provenance records. Raw downloaded data remains project-local until its
redistribution terms are recorded. The repository may store a retrieval recipe and checksum rather
than the downloaded archive.

### 10.3 Slice-level acceptance

V2A completes the project's literature and theory layer:

- a real, content-addressed corpus of inspected full texts;
- nearest-work and domain coverage linked to the V1 novelty audit;
- evidence rows with exact quotations and locators;
- at least one real contradiction, qualification, or null finding preserved in the ledger;
- citation identity and support audits;
- theory candidates and a user-facing decision packet;
- an allowed descriptive outcome if no theory is sufficiently supported.

V2B will add preregistered cleaning, transformed sentiment and engagement-rate definitions,
time-series-aware uncertainty, robustness checks, and figures. V2C will add the manuscript,
review/revision record, and reproducibility package.

The real project is not an acceptance shortcut. Automated tests use small local fixtures; the real
project separately demonstrates that the contracts work on genuine sources and data.

## 11. Testing strategy

Every production change follows red-green-refactor. Tests are offline and deterministic.

### 11.1 Contract and unit tests

- capability manifests accept only registered artifact types and declared permissions;
- document identity, hashes, locators, version links, and privacy states validate;
- evidence rows reject missing exact passages or locators;
- source claims and author inference cannot occupy the same field;
- material contradictions block theory progression;
- metadata-only identity verification cannot satisfy passage support;
- Chinese sources without DOI can pass through an applicable official-record route;
- DOI/title/author conflicts remain visible;
- hash drift stales only dependent outputs;
- provider errors cannot upgrade evidence states;
- autonomous mode stops at theory and privacy decisions.

### 11.2 Acceptance fixtures

Fixtures include:

- verified full text with page locators;
- metadata-only candidate;
- inaccessible source;
- duplicate/version conflict;
- Chinese journal article without DOI;
- exact passage that partially supports a proposed claim;
- contradictory and null findings;
- changed source bytes after checkpoint;
- request to fabricate or strengthen an unsupported citation;
- provider attempting insecure TLS behavior;
- autonomous theory-selection attempt without authorization.

### 11.3 Integration and regression tests

- standalone runs for all four capabilities;
- `literature-to-theory` in all three run modes;
- checkpoint, resume, blocker, and stale-recovery paths;
- V1 `idea-to-novelty` regression suite unchanged;
- source-manifest schema and source-hash validation;
- Windows path, UTF-8/Chinese text, and atomic-write behavior.

No live API is required for the default test suite. Optional provider contract tests use recorded,
non-secret fixtures.

## 12. Documentation and installation

V2A adds or updates:

- standalone capability guides;
- evidence-state and citation-verification guide;
- corpus privacy/provider guide;
- contradiction and theory-decision guide;
- workflow/resume examples;
- `SOURCE_MANIFEST.yaml` and third-party notices;
- real-project provenance and execution notes.

New Skills are installed locally only after repository tests, acceptance fixtures, source-manifest
validation, and preservation checks for the seven existing SSCI Skills pass.

## 13. Implementation sequence

The implementation plan must use tracer-bullet vertical tasks rather than building four complete
capabilities in isolation:

1. register V2A artifact schemas and one end-to-end failing fixture;
2. implement document indexing and exact locator preservation;
3. create one evidence row and verify its citation identity/support;
4. preserve a contradiction and block progression;
5. generate a theory decision packet and enforce the human stop;
6. generalize the four standalone capabilities and workflow route;
7. run the real NORC literature/theory checkpoint;
8. install accepted Skills and update operator documentation.

Each task must leave the system runnable and retain V1 behavior.

## 14. Completion criteria

V2A is complete only when:

- all four capabilities run independently and through `literature-to-theory`;
- interactive, checkpointed, and autonomous stop policies are demonstrated;
- exact passage and locator evidence survives checkpoint/resume;
- identity and support verification remain separate;
- material contradictions cannot be silently bypassed;
- theory selection remains human-owned and descriptive work remains allowed;
- the default test suite is offline and passes on Windows;
- every reused or referenced source has a complete, validated manifest record;
- prohibited sources/mechanisms are absent from runtime and tests;
- the seven existing local SSCI Skills remain byte-identical;
- the real NORC project reaches a reviewable V2A theory-decision checkpoint with genuine sources;
- documentation explains the smallest next action and exact resume point.

Passing tests demonstrate contract and workflow behavior. They do not by themselves establish the
truth of a scholarly interpretation; the human evidence and theory gates remain mandatory.
