# Zotero–Obsidian Minimal Research Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove a token-efficient, idempotent Zotero-to-Obsidian research loop with the real GSMA
pilot and no repeated model work for unchanged sources.

**Architecture:** A deterministic integration package consumes a versioned sync specification,
upserts bibliographic records through a narrow Zotero protocol, and writes marker-bounded notes
to a caller-selected Obsidian vault. A JSON state artifact maps stable source identities to Zotero
keys, note paths, and hashes so subsequent runs skip unchanged work.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, Python standard-library HTTP client, pytest,
Obsidian Markdown, Zotero 10+ local API.

**Spec:** `docs/superpowers/specs/2026-08-26-zotero-obsidian-minimal-bridge-design.md`

## Global Constraints

- Use the existing isolated `feature/ssci-research-skills-os-v1` worktree.
- Production behavior follows red-green-refactor; no production code precedes its failing test.
- Zotero is the bibliographic source of truth; Obsidian contains derived reading and synthesis.
- No delete operation, credential storage, absolute vault path in Git, or background daemon.
- DOI, then canonical URL, then title-plus-year defines duplicate identity.
- A source hash change marks reading output stale; an unchanged hash skips note rewriting.
- Text outside generated markers is user-owned and survives reruns byte-for-byte.
- Live mode must finish Zotero upserts before writing Obsidian.
- Existing seven SSCI writing Skills remain untouched.
- The detected Zotero 9.0.5 may preview reads but must not be treated as local-write capable.

---

### Task 1: Define the deterministic sync contract and planner

**Files:**

- Create: `src/research_skills_os/integrations/__init__.py`
- Create: `src/research_skills_os/integrations/zotero_obsidian/__init__.py`
- Create: `src/research_skills_os/integrations/zotero_obsidian/models.py`
- Create: `src/research_skills_os/integrations/zotero_obsidian/planner.py`
- Test: `tests/integrations/test_zotero_obsidian_planner.py`

**Interfaces:**

- Consumes: versioned YAML-compatible values for one project and a prior state mapping.
- Produces: `SyncSpec`, `SyncState`, `SyncAction`, `build_sync_plan(spec, state)` and stable
  `source_identity(source)`.

- [ ] **Step 1: Write the failing identity and planning tests**

Cover DOI normalization, URL fallback, title/year fallback, identity collision rejection, a new
source producing `upsert`, unchanged state producing `skip`, and changed content producing
`refresh_note`.

```python
def test_unchanged_source_is_skipped() -> None:
    source = source_record(content_sha256="a" * 64)
    state = SyncState(records={source.source_id: state_record(source)})
    plan = build_sync_plan(sync_spec(source), state)
    assert [(action.kind, action.reason) for action in plan.actions] == [
        (SyncActionKind.SKIP, "identity and content hash unchanged")
    ]
```

- [ ] **Step 2: Run the tests and verify the expected import failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integrations/test_zotero_obsidian_planner.py -q
```

Expected: FAIL because the integration package does not exist.

- [ ] **Step 3: Implement the minimal strict models and pure planner**

Use frozen Pydantic models with these public fields:

```python
class SyncSource(BaseModel):
    source_id: str
    title: str
    year: int
    item_type: str
    authors: tuple[str, ...] = ()
    doi: str | None = None
    url: str | None = None
    content_sha256: str
    note_source: str
    inspected_content: bool

class SyncSpec(BaseModel):
    version: Literal[1]
    project_id: str
    zotero_collection: str
    obsidian_project: str
    sources: tuple[SyncSource, ...]

class SyncStateRecord(BaseModel):
    identity: str
    content_sha256: str
    zotero_item_key: str
    obsidian_note: str

class SyncState(BaseModel):
    version: Literal[1] = 1
    records: dict[str, SyncStateRecord] = Field(default_factory=dict)
```

Reject empty source sets, malformed SHA-256 values, unsafe note paths, duplicate `source_id`, and
two source IDs resolving to the same bibliographic identity.

- [ ] **Step 4: Run focused tests, Ruff, and mypy**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integrations/test_zotero_obsidian_planner.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/integrations tests/integrations/test_zotero_obsidian_planner.py
.\.venv\Scripts\python.exe -m mypy src/research_skills_os/integrations
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add src/research_skills_os/integrations tests/integrations/test_zotero_obsidian_planner.py
git commit -m "feat(integration): plan idempotent library sync"
```

---

### Task 2: Write Obsidian notes without overwriting human text

**Files:**

- Create: `src/research_skills_os/integrations/zotero_obsidian/obsidian.py`
- Test: `tests/integrations/test_obsidian_writer.py`

**Interfaces:**

- Consumes: resolved vault root, vault-relative project path, source metadata, Zotero item key,
  and inspected note-source Markdown.
- Produces: `render_source_note(...) -> str`, `merge_generated_block(existing, generated) -> str`,
  and `ObsidianWriter.write_source_note(...) -> Path`.

- [ ] **Step 1: Write failing tests for containment and marker ownership**

Tests must prove a new source note includes frontmatter and a `zotero://select/library/items/KEY`
link, a rerun replaces only the generated block, text under `## 我的想法` remains byte-identical,
unchanged content leaves file modification time unchanged, and `..` cannot escape the vault.

```python
def test_rerun_preserves_user_section(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    path = writer.write_source_note(note_request(generated="first"))
    path.write_text(path.read_text(encoding="utf-8") + "\n## 我的想法\n保留我写的内容。\n", encoding="utf-8")
    writer.write_source_note(note_request(generated="second"))
    text = path.read_text(encoding="utf-8")
    assert "second" in text and "first" not in text
    assert "## 我的想法\n保留我写的内容。" in text
```

- [ ] **Step 2: Verify the tests fail because the writer is absent**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integrations/test_obsidian_writer.py -q
```

- [ ] **Step 3: Implement marker-bounded, atomic, idempotent writes**

Use exactly these markers:

```text
<!-- research-os:auto:start -->
<!-- research-os:auto:end -->
```

Resolve every destination and verify `destination.is_relative_to(vault_root.resolve())`. Write to
a sibling temporary file and replace only when bytes differ. Source notes live at
`<project>/Sources/Papers/<safe-title>.md`.

- [ ] **Step 4: Run focused and static checks**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integrations/test_obsidian_writer.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/integrations/zotero_obsidian/obsidian.py tests/integrations/test_obsidian_writer.py
.\.venv\Scripts\python.exe -m mypy src/research_skills_os/integrations/zotero_obsidian/obsidian.py
```

- [ ] **Step 5: Commit**

```powershell
git add src/research_skills_os/integrations/zotero_obsidian/obsidian.py tests/integrations/test_obsidian_writer.py
git commit -m "feat(integration): preserve human obsidian notes"
```

---

### Task 3: Add a narrow Zotero adapter and transactional coordinator

**Files:**

- Create: `src/research_skills_os/integrations/zotero_obsidian/zotero.py`
- Create: `src/research_skills_os/integrations/zotero_obsidian/service.py`
- Test: `tests/integrations/test_zotero_bridge_service.py`

**Interfaces:**

- Produces protocol methods `ensure_collection(name) -> str`, `find_item(identity) -> str | None`,
  `create_item(source, collection_key) -> str`, and `add_to_collection(item_key, collection_key)`.
- Produces `ZoteroObsidianBridge.preview(...) -> SyncPlan` and `.apply(...) -> SyncResult`.

- [ ] **Step 1: Write failing coordinator tests with an in-memory Zotero implementation**

Prove dry-run performs zero writes, duplicates reuse an existing Zotero key, Zotero failure causes
zero Obsidian files, successful application stores all mappings, and a second application is a
no-op.

```python
def test_zotero_failure_prevents_obsidian_mutation(tmp_path: Path) -> None:
    zotero = FailingZotero()
    bridge = ZoteroObsidianBridge(zotero=zotero, vault_root=tmp_path)
    with pytest.raises(ZoteroUnavailable):
        bridge.apply(spec, SyncState())
    assert list(tmp_path.rglob("*.md")) == []
```

- [ ] **Step 2: Verify the tests fail for the missing service**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integrations/test_zotero_bridge_service.py -q
```

- [ ] **Step 3: Implement the protocol, local HTTP adapter, and coordinator**

Use `urllib.request` against `http://127.0.0.1:23119/api/` with
`Zotero-API-Version: 3`. Read `/api/` first and reject a reported major version below 10. Before
the first write, POST `{"appName":"Research Skills OS"}` to `/api/local/authorize`, retain the
returned key in process memory, and send it as `Zotero-API-Key`. Normalize returned DOI/URL values
before comparison, never expose a delete method, and convert connection, denial, and version
failures into typed bridge errors. The coordinator resolves every Zotero key before it constructs
any Obsidian write request.

- [ ] **Step 4: Run focused/static checks**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integrations/test_zotero_bridge_service.py -q
.\.venv\Scripts\python.exe -m ruff check src/research_skills_os/integrations tests/integrations
.\.venv\Scripts\python.exe -m mypy src/research_skills_os/integrations
```

- [ ] **Step 5: Commit**

```powershell
git add src/research_skills_os/integrations tests/integrations/test_zotero_bridge_service.py
git commit -m "feat(integration): coordinate zotero and obsidian sync"
```

---

### Task 4: Add the dry-run CLI and GSMA pilot sync specification

**Files:**

- Create: `src/research_skills_os/integrations/zotero_obsidian/cli.py`
- Create: `projects/gsma-sentiment-engagement/library-sync.yaml`
- Create: `projects/gsma-sentiment-engagement/artifacts/library-sync-state.json`
- Create: `projects/gsma-sentiment-engagement/notes/project-index.md`
- Create: `projects/gsma-sentiment-engagement/notes/initial-synthesis.md`
- Create: `projects/gsma-sentiment-engagement/notes/research-memo.md`
- Test: `tests/acceptance/test_library_sync_cli.py`

**Interfaces:**

- Command: `python -m research_skills_os.integrations.zotero_obsidian.cli --spec PATH --vault PATH`
  previews by default; `--apply` performs writes; `--state PATH` overrides the default adjacent
  state path.
- Exit codes: `0` success/no-op, `2` invalid spec/path, `3` Zotero unavailable, `4` partial block.

- [ ] **Step 1: Write failing CLI acceptance tests**

Assert preview JSON reports intended actions but does not create state or vault files; an invalid
absolute vault path in the spec is rejected; and apply with the in-memory adapter produces stable
state and notes.

- [ ] **Step 2: Run and observe the expected CLI failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_library_sync_cli.py -q
```

- [ ] **Step 3: Implement the CLI and create a two-or-three-source pilot spec**

The committed specification contains only vault-relative paths. Every source references a checked
Markdown note and an exact content hash. The state begins with `{"version": 1, "records": {}}`.
Preview output contains no private absolute paths.

- [ ] **Step 4: Run the acceptance test and preview the real spec**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_library_sync_cli.py -q
.\.venv\Scripts\python.exe -m research_skills_os.integrations.zotero_obsidian.cli --spec projects/gsma-sentiment-engagement/library-sync.yaml --vault "C:\Users\10710\Documents\日常学习"
```

Expected: tests pass; preview proposes the collection and source-note actions without mutation.

- [ ] **Step 5: Commit**

```powershell
git add src/research_skills_os/integrations/zotero_obsidian/cli.py projects/gsma-sentiment-engagement tests/acceptance/test_library_sync_cli.py
git commit -m "feat(pilot): preview gsma library sync"
```

---

### Task 5: Run the real pilot, audit gaps, and verify idempotency

**Files:**

- Modify: `projects/gsma-sentiment-engagement/artifacts/library-sync-state.json`
- Create: `projects/gsma-sentiment-engagement/artifacts/library-sync-audit.md`
- Modify: `projects/gsma-sentiment-engagement/README.md`
- Test: `tests/acceptance/test_gsma_library_sync_state.py`
- External create/update: active Zotero library collection `Pilot｜GSMA情绪与互动`
- External create/update: `C:\Users\10710\Documents\日常学习\Research\GSMA情绪与互动\`

**Interfaces:**

- Consumes the verified GSMA V2A project artifacts and live local applications.
- Produces a durable mapping state plus a user-visible synchronized research folder.

- [ ] **Step 1: Write the failing live-state acceptance test**

The test validates that every configured source has a Zotero key and vault-relative note path,
the state hashes match the sync spec, no source identity is duplicated, and the audit reports at
least one discovered gap and one concrete improvement.

- [ ] **Step 2: Verify failure because live state is empty**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_gsma_library_sync_state.py -q
```

- [ ] **Step 3: Start/probe Zotero and apply once**

Confirm Zotero 10 or later is installed, then start the desktop application if it is not already
running. Probe local API port `23119`; if communication is disabled, stop with the exact Zotero
setting that must be enabled. The first live write pauses for Zotero's own authorization dialog.
After approval, run:

```powershell
.\.venv\Scripts\python.exe -m research_skills_os.integrations.zotero_obsidian.cli --spec projects/gsma-sentiment-engagement/library-sync.yaml --vault "C:\Users\10710\Documents\日常学习" --apply
```

- [ ] **Step 4: Apply a second time and prove no-op behavior**

Record the hashes and modification times of generated notes, run the same command again, and
assert the result reports zero create/update actions and unchanged note bytes.

- [ ] **Step 5: Write the audit and run verification**

The audit distinguishes implementation defects from deferred scope. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_gsma_library_sync_state.py tests/acceptance/test_gsma_v2a_project.py -q
.\.venv\Scripts\python.exe -m pytest --cov=research_skills_os --cov-report=term-missing --cov-fail-under=90 -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/research_skills_os
git diff --check
```

Expected: all pass, coverage at least 90%, and no formatting errors.

- [ ] **Step 6: Commit**

```powershell
git add projects/gsma-sentiment-engagement tests/acceptance/test_gsma_library_sync_state.py
git commit -m "feat(pilot): sync gsma sources to zotero and obsidian"
```
