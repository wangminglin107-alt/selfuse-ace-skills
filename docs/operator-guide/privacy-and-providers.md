# Privacy and providers

V1 defaults to `constraints.network: deny` and the `local-manual` provider. Local source content,
credentials, and sensitive artifacts are not sent anywhere by default.

V2A keeps this default. `paper-knowledge-base`, `evidence-synthesis`, `citation-verification`, and
`theory-architecture` operate on project-contained artifacts and perform no implicit provider call.
Each document declares `privacy_label` and content availability. Metadata-only records may be
catalogued, but cannot support content claims.

A network provider requires all of the following: a declared provider ID, user authorization in
the request, endpoint and privacy declarations, secret names without secret values, timeouts,
response validation, provenance, and explicit verification state. A provider response is not
automatically verified scholarly evidence.

The Qinyan source is audited only as `reference_only`: its upstream Bash script calls curl, reads
`QINYAN_API_KEY`, and sends query payloads to a remote endpoint. V1 does not install or invoke it.
SciPilot Figure is also `reference_only` for a later capability.

When a provider gate blocks, inspect stderr, state, and gate results; change authorization or use a
local source, then rerun the blocked capability. Never paste credentials into requests, artifacts,
logs, checkpoints, or source manifests.

The optional Zotero—Obsidian bridge talks only to Zotero's local API and the explicitly selected
Obsidian vault. Its default command is preview-only, its write mode has no delete operation, and its
SHA-256 state cache skips unchanged notes and attachments.

PDF archiving is opt-in per source. A `local_file` attachment must remain inside the project root,
start with a PDF signature, and match its declared SHA-256 before any Zotero or Obsidian mutation.
The bridge uploads it as a Zotero child attachment and records the returned key; a later run reuses
the same hash and never overwrites or deletes an attachment. `metadata_only` records preserve the
bibliographic item without pretending that a PDF was inspected. Obsidian uses `link_only` by
default, so Zotero remains the binary source of truth and the vault receives a durable note link.
