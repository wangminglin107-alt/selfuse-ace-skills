# SSCI Research Skills OS V2B Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add idempotent Zotero PDF attachment archiving and fail-closed registry semantic validation.

**Architecture:** Extend the existing no-delete Zotero bridge with verified local attachment contracts and keep semantic validation in `RegistryLoader`. No downloading or access-control bypass is implemented.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, pytest, Zotero 10 local API.

**Spec:** `docs/superpowers/specs/2026-08-26-ssci-research-skills-os-v2b-foundation-design.md`

## Global Constraints

- Use red-green-refactor for every production change.
- Zotero is the attachment source of truth; default Obsidian policy is link-only.
- Never delete or overwrite an attachment.
- Validate contained absolute resolutions before filesystem reads or writes.
- Preserve compatibility with attachment-free version-1 sync specs.

---

### Task 1: Attachment contracts and hash validation

**Files:**
- Modify: `src/research_skills_os/integrations/zotero_obsidian/models.py`
- Test: `tests/integrations/test_zotero_attachment_models.py`

**Interfaces:**
- Produces: `AttachmentSpec`, `AttachmentStatus`, extended `SyncSource` and `SyncStateRecord`.

- [ ] Write tests for contained paths, PDF media type, SHA-256, metadata-only state and backward-compatible specs.
- [ ] Run `pytest tests/integrations/test_zotero_attachment_models.py -q` and verify failure.
- [ ] Implement immutable Pydantic contracts and validators.
- [ ] Rerun the focused tests and commit `feat(integration): contract zotero attachments`.

### Task 2: Verified attachment preparation

**Files:**
- Create: `src/research_skills_os/integrations/zotero_obsidian/attachments.py`
- Test: `tests/integrations/test_attachment_preparation.py`

**Interfaces:**
- Produces: `prepare_attachment(spec: AttachmentSpec, project_root: Path) -> PreparedAttachment`.

- [ ] Write tests for hash match, hash drift, non-PDF signature, missing file and path escape.
- [ ] Run the tests and verify the missing module failure.
- [ ] Implement read-only validation and a frozen `PreparedAttachment` result.
- [ ] Rerun and commit `feat(integration): verify local pdf attachments`.

### Task 3: Zotero attachment boundary and bridge integration

**Files:**
- Modify: `src/research_skills_os/integrations/zotero_obsidian/zotero.py`
- Modify: `src/research_skills_os/integrations/zotero_obsidian/service.py`
- Test: `tests/integrations/test_zotero_attachment_client.py`
- Modify: `tests/integrations/test_zotero_bridge_service.py`

**Interfaces:**
- Adds: `find_attachment(parent_key: str, sha256: str) -> str | None` and `create_attachment(parent_key: str, prepared: PreparedAttachment) -> str`.

- [ ] Write protocol and service tests proving reuse, create-after-item, no overwrite and state persistence.
- [ ] Run focused tests and verify protocol/attribute failures.
- [ ] Implement the smallest local-API adapter and service coordination.
- [ ] Rerun focused bridge tests and commit `feat(integration): archive zotero pdf attachments`.

### Task 4: Deep registry semantic validation

**Files:**
- Modify: `src/research_skills_os/core/registry/models.py`
- Modify: `src/research_skills_os/core/registry/loader.py`
- Create: `tests/fixtures/registry/invalid-unreachable-node.yaml`
- Create: `tests/fixtures/registry/invalid-target-input.yaml`
- Test: `tests/unit/registry/test_semantic_validation.py`

**Interfaces:**
- Produces deterministic `SpecLoadError` messages for graph reachability, terminal, mapping and review invariants.

- [ ] Write failing tests for each semantic invariant and confirm existing registries remain valid.
- [ ] Run `pytest tests/unit/registry -q` and verify new failures.
- [ ] Implement reachability and source/target artifact validation in focused helpers.
- [ ] Rerun registry and workflow tests and commit `feat(registry): validate workflow semantics`.

### Task 5: V2B acceptance and documentation

**Files:**
- Modify: `docs/operator-guide/privacy-and-providers.md`
- Modify: `docs/operator-guide/standalone-capabilities.md`
- Create: `docs/architecture/v2b-acceptance-report.md`
- Test: `tests/acceptance/test_v2b_foundation.py`

**Interfaces:**
- Produces documented attachment states, recovery rules and acceptance evidence.

- [ ] Write acceptance tests for an idempotent fake-client archive and invalid registry fixtures.
- [ ] Implement documentation and record exact commands/results.
- [ ] Run focused acceptance, full pytest, Ruff, mypy and `git diff --check`.
- [ ] Commit `test(v2b): verify attachment and registry foundations`.

