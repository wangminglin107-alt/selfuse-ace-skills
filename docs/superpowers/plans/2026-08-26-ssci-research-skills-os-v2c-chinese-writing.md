# SSCI Research Skills OS V2C Chinese Writing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the seven SSCI skills without duplicate ownership and produce an evidence-traceable Chinese theoretical research note.

**Architecture:** Register existing scholarly skills behind OS contracts, add a diagnostic-only prose-style capability, and compose an acyclic Chinese-note workflow. Existing skill names remain usable through canonical or compatibility routing.

**Tech Stack:** Markdown Codex skills, YAML registry, Python 3.12 deterministic gates, pytest, Zotero, Obsidian.

**Spec:** `docs/superpowers/specs/2026-08-26-ssci-research-skills-os-v2c-chinese-writing-design.md`

## Global Constraints

- `research-os` is the only lifecycle orchestrator.
- `ssci-section-drafting` is the only manuscript prose writer.
- Style audit is diagnostic and cannot alter protected anchors.
- Chinese is the required main deliverable; English is optional.
- No durable claim may rely on metadata-only or abstract-only evidence.
- Every upstream reuse is file-level and recorded in `SOURCE_MANIFEST.yaml`.

---

### Task 1: Freeze ownership and compatibility contracts

**Files:**
- Create: `docs/architecture/ssci-skill-ownership.md`
- Modify: `skills/research-os/SKILL.md`
- Create: `skills/ssci-paper-writer/SKILL.md`
- Create: `skills/ssci-research-framing/SKILL.md`
- Test: `tests/acceptance/test_ssci_skill_ownership.py`

**Interfaces:**
- Produces one canonical owner per task and compatibility-only legacy entry points.

- [ ] Write tests that reject duplicate scholarly procedures in compatibility skills.
- [ ] Run the focused test and verify missing skill failures.
- [ ] Add thin compatibility Skills and ownership documentation.
- [ ] Rerun and commit `refactor(skills): unify ssci capability ownership`.

### Task 2: Register manuscript architecture and drafting

**Files:**
- Create: `src/research_skills_os/capabilities/ssci_argument_architecture/capability.yaml`
- Create: `src/research_skills_os/capabilities/ssci_section_drafting/capability.yaml`
- Create: `skills/ssci-argument-architecture/SKILL.md`
- Create: `skills/ssci-section-drafting/SKILL.md`
- Create: `skills/ssci-section-drafting/references/theoretical-note.md`
- Create: `skills/ssci-section-drafting/references/zh-style.md`
- Test: `tests/acceptance/test_ssci_writing_skill_contracts.py`

**Interfaces:**
- Architecture outputs `paper_argument_map`, `section_outline`, `claim_evidence_plan`, `terminology_ledger`.
- Drafting outputs `chinese_manuscript`, `draft_trace`, `author_input_needed`.

- [ ] Write failing structural and behavior-contract tests.
- [ ] Add minimal capability YAML and short routers with on-demand references.
- [ ] Validate that drafting consumes approved architecture and evidence rather than recreating theory.
- [ ] Rerun and commit `feat(writing): register argument and chinese drafting`.

### Task 3: Add diagnostic prose-style audit

**Files:**
- Create: `src/research_skills_os/capabilities/academic_prose_style_audit/__init__.py`
- Create: `src/research_skills_os/capabilities/academic_prose_style_audit/models.py`
- Create: `src/research_skills_os/capabilities/academic_prose_style_audit/gates.py`
- Create: `src/research_skills_os/capabilities/academic_prose_style_audit/capability.yaml`
- Create: `skills/academic-prose-style-audit/SKILL.md`
- Create: `skills/academic-prose-style-audit/references/zh-patterns.md`
- Test: `tests/unit/capabilities/test_academic_prose_style_audit.py`

**Interfaces:**
- Produces `audit_prose(text: str, protected_anchors: tuple[str, ...]) -> ProseStyleReport` and revision findings without rewritten prose.

- [ ] Write failing tests for filler, repeated starts, connector density, protected-anchor coverage and neutral human prose.
- [ ] Implement deterministic advisory metrics and blocking coverage/anchor gates.
- [ ] Add the skill procedure and bounded three-pass maximum.
- [ ] Rerun and commit `feat(writing): add academic prose style audit`.

### Task 4: Register bilingual, revision and peer-review skills

**Files:**
- Create: `src/research_skills_os/capabilities/ssci_bilingual_writing/capability.yaml`
- Create: `src/research_skills_os/capabilities/ssci_revision_audit/capability.yaml`
- Create: `src/research_skills_os/capabilities/ssci_peer_review/capability.yaml`
- Create: `skills/ssci-bilingual-writing/SKILL.md`
- Create: `skills/ssci-revision-audit/SKILL.md`
- Create: `skills/ssci-peer-review/SKILL.md`
- Modify: `SOURCE_MANIFEST.yaml`
- Test: `tests/acceptance/test_ssci_writing_skill_contracts.py`

**Interfaces:**
- Bilingual output remains optional; revision audit consumes specialist reports; peer review produces external concerns only.

- [ ] Write failing ownership and output-contract assertions.
- [ ] Add narrowed Skills and capability registrations without duplicating citation or style logic.
- [ ] Record exact local/upstream source hashes, license decisions and tests.
- [ ] Rerun and commit `feat(writing): integrate bilingual revision and review`.

### Task 5: Compose the Chinese-note workflow

**Files:**
- Create: `src/research_skills_os/workflows/evidence_to_chinese_note/workflow.yaml`
- Create: `skills/evidence-to-chinese-note/SKILL.md`
- Test: `tests/integration/test_evidence_to_chinese_note_workflow.py`

**Interfaces:**
- Produces an acyclic seven-node preset with explicit artifact mappings and checkpoints.

- [ ] Write a failing graph/order/mapping/mode test.
- [ ] Add the thin workflow and Skill; keep prompts and rubrics outside workflow YAML.
- [ ] Verify every mapped artifact is declared by source and target.
- [ ] Rerun and commit `feat(workflow): compose chinese research note`.

### Task 6: Expand and run the GSMA pilot

**Files:**
- Modify: `projects/gsma-sentiment-engagement/sources/`
- Modify: `projects/gsma-sentiment-engagement/artifacts/`
- Create: `projects/gsma-sentiment-engagement/writing/chinese-research-note.md`
- Create: `projects/gsma-sentiment-engagement/writing/prose-revision-matrix.md`
- Create: `projects/gsma-sentiment-engagement/writing/revision-audit.md`
- Create: `projects/gsma-sentiment-engagement/writing/peer-review.md`
- Create: `projects/gsma-sentiment-engagement/writing/abstract-alignment.md`
- Test: `tests/acceptance/test_gsma_v2c_project.py`

**Interfaces:**
- Produces 8–12 verified records, a 4,000–6,000-character Chinese note, all audit artifacts and durable checkpoints.

- [ ] Write acceptance assertions for source count, evidence IDs, character band, no unsupported placeholders, style anchors, audits and checkpoint verification.
- [ ] Search authoritative scholarly sources, inspect accessible full text, verify identities and update Zotero/Obsidian.
- [ ] Run the registered workflow, generate the note and record every limitation instead of inventing results.
- [ ] Run style, citation, revision, peer-review and bilingual-abstract checks; repair only evidence-backed failures.
- [ ] Rerun acceptance and commit `test(v2c): run chinese theory note tracer bullet`.

### Task 7: Full verification, install and acceptance report

**Files:**
- Modify: `scripts/install-skills.ps1`
- Create: `docs/architecture/v2c-acceptance-report.md`
- Modify: `README.md`
- Test: `tests/integration/install/test_install_scripts.py`

**Interfaces:**
- Produces safe installation of new/updated Skills and a reproducible final report.

- [ ] Extend installer targets while preserving unrelated and legacy SSCI skill backups.
- [ ] Run the full suite with coverage at least 90%, Ruff, mypy and `git diff --check`.
- [ ] Install idempotently, verify source/installed hashes and record rollback information.
- [ ] Commit `docs(v2c): verify chinese writing workflow` and push the existing PR branch.

