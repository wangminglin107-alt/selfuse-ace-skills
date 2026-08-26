# Zotero–Obsidian Minimal Research Bridge Design

## Purpose

Validate the Research Skills OS with one very small real project while making Zotero the source
of truth for bibliographic material and the currently open Obsidian vault the source of truth for
human-readable research thinking. The first project is `gsma-sentiment-engagement`.

## Scope

V1 of the bridge handles two or three verified sources. It can:

- find or create one Zotero collection;
- upsert sources without creating duplicates;
- create project-local Obsidian source notes and short synthesis notes;
- preserve user-written note sections;
- record Zotero item keys, Obsidian paths, source hashes, and sync outcomes;
- skip unchanged sources on later runs;
- preview every mutation in dry-run mode.

It does not run continuously, install an Obsidian plugin, generate a Canvas graph, summarize an
unchanged paper again, or replace Zotero/Obsidian's own synchronization services.

## Token-Efficiency Decision

Deterministic code performs collection lookup, DOI/URL normalization, duplicate detection, file
hashing, note rendering, marker-bounded updates, sync-state comparison, and checkpoint reporting.
Model work is limited to the first evidence-grounded reading and synthesis of a changed source.

The alternatives were rejected:

- Better BibTeX alone exports metadata but cannot ingest new sources or create evidence notes.
- An Obsidian Zotero plugin would add another UI dependency and is not installed in the active
  vault.
- A permanent background service would add state and security cost before the workflow is proven.

## Local Boundaries

- Repository: the existing isolated `research-skills-os-v1-implementation` worktree.
- Active vault: `C:\Users\10710\Documents\日常学习`, resolved from Obsidian's local config rather
  than hard-coded in reusable code.
- Zotero: local Zotero 7 API at `127.0.0.1:23119`; no account password or API key is stored.
- Zotero collection: `Pilot｜GSMA情绪与互动`.
- Obsidian project root: `Research/GSMA情绪与互动`.

Live writes require Zotero to be running with local application communication enabled. A closed
or unavailable Zotero instance blocks cleanly before Obsidian mutation.

## Components

### Sync specification and state

A versioned YAML sync specification names the project, collection, vault-relative destination,
and source records. A JSON state artifact maps each stable source ID to its normalized identity,
content hash, Zotero item key, Obsidian note path, and last successful result.

Identity priority is normalized DOI, then canonical URL, then `title + year`. Content hashes do
not replace bibliographic identity; they decide whether reading output is stale.

### Zotero adapter

The adapter exposes a small protocol so tests use an in-memory implementation and live runs use
the local Zotero API. It lists/creates a collection, finds matching items, creates missing items,
and attaches them to the collection. It never deletes items or collections.

### Obsidian writer

Each source has one canonical note under `Sources/Papers/`. Generated content is confined between
explicit markers. Text outside the markers is user-owned and must survive reruns byte-for-byte.
The bridge also creates a project index, a short synthesis under `Knowledge/`, and a research memo
under `Writing/`. The first pilot omits Canvas generation.

### Coordinator

The coordinator builds a complete plan first. `dry_run=true` returns the plan without writes.
Live application runs Zotero operations first and writes Obsidian only after every Zotero source
has a stable item key. A partial failure is recorded as blocked and can be resumed idempotently.

## Pilot Evidence Flow

The GSMA pilot uses the official NORC methodology/archive plus no more than two inspected
open-access research papers. Exact short passages, page or stable-section locators, and source
hashes feed the existing paper-knowledge-base, evidence-synthesis, citation-verification, and
theory-architecture gates. Metadata-only candidates may enter Zotero as `To Read`, but cannot
support Obsidian synthesis or Research OS claims.

The research question remains associational. The pilot must not promote causal or individual-level
claims from aggregate observational records.

## Safety and Privacy

- No Zotero credentials, personal library export, or absolute vault path enters Git.
- No deletion API is implemented.
- Paths must stay under the resolved vault root.
- Live mode refuses an empty source set, identity collision, missing inspected-content marker, or
  unavailable Zotero endpoint.
- Source passages remain short and are stored only when needed for claim verification.

## Acceptance

The bridge is accepted when automated tests prove dry-run purity, identity-based deduplication,
unchanged-source skipping, marker-bounded note updates, path containment, and clean blocking when
Zotero is unavailable. The live pilot is accepted when one Zotero collection contains the chosen
sources, corresponding notes exist in the active synchronized vault, the mapping state is saved,
and a second run produces no duplicates or rewritten unchanged notes.

## Deferred Improvements

After the pilot, review whether to register this adapter as a formal workflow sink, add Zotero Web
API fallback for runs while the desktop app is closed, generate literature Canvas files, or trigger
incremental sync automatically. None is required for the first proof.
