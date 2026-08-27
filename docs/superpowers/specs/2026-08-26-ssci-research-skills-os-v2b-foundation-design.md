# SSCI Research Skills OS V2B Foundation Design

## Purpose

V2B hardens two boundaries needed before manuscript production: lawful, idempotent PDF attachment
archiving in Zotero and fail-closed semantic validation of registry YAML. Zotero remains the source
of truth for bibliographic records and original attachments; Obsidian receives notes and optional
links, not an uncontrolled second library.

## PDF attachment contract

Each `SyncSource` may declare one attachment with a project-relative local path, a source URL,
media type, SHA-256, access status, and mirror policy. V2B accepts only an already acquired local
file; network acquisition remains a separate provider decision and no access control is bypassed.
The bridge verifies the file hash and PDF signature before any write.

The Zotero adapter exposes attachment discovery and upload operations. Attachment identity is the
SHA-256 first and the parent item key second. Reapplying the same spec reuses the existing
attachment. A different hash never overwrites an existing file: it is reported as a version
conflict for human resolution. `metadata_only` sources remain valid library records but cannot be
promoted as inspected full-text evidence.

The sync state records attachment key, SHA-256, status, and optional Obsidian mirror path. The
default mirror policy is `link_only`. `copy_core` is opt-in and writes only beneath the declared
Obsidian project directory.

## Registry semantic validation

`RegistryLoader` remains the single registry authority. In addition to schema parsing, uniqueness,
declared source outputs, and acyclicity, it validates:

- every non-entry node is reachable from the entry node;
- every terminal is reachable and has no outgoing edge;
- every non-terminal reaches at least one terminal;
- every artifact mapping follows graph direction and names a target input type;
- every mapped artifact is declared by the source and accepted by the target;
- capability IDs and node IDs remain distinct concepts;
- autonomous review nodes are also human review nodes;
- writing workflows containing bilingual output retain a Chinese manuscript path and cannot make
  English output the only terminal artifact;
- workflows contain orchestration metadata only, never embedded prompts or scholarly rubrics.

Validation errors identify workflow, node or mapping and the failed invariant. Invalid registries
cannot start a run.

## Security and recovery

No deletes, attachment replacement, credential persistence, or arbitrary-path writes are added.
Hash mismatch, invalid PDF, Zotero denial, or semantic registry failure stops before mutation.
Every accepted attachment operation is represented in the durable sync audit and can be retried.

## Acceptance

- duplicate attachment application is idempotent;
- invalid or drifted files are rejected before Zotero writes;
- metadata-only sources remain explicit;
- all new semantic invariants have failing fixtures and deterministic tests;
- existing V1/V2A registries remain valid;
- existing bridge behavior and seven SSCI skills remain recoverable.

