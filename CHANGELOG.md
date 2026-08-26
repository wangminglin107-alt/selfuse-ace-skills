# Changelog

All notable changes to SSCI Research Skills OS are recorded here.

## 0.1.0 - 2026-08-25

### Added

- Core Research OS runtime with strict contracts, registry/router, event-sourced state, atomic
  checkpoints, drift-aware resume, named gates, provider policy, and Windows CLI.
- Independently callable `research-framing`, `literature-intelligence`, and `novelty-audit`
  capabilities.
- Thin `idea-to-novelty` workflow preset with interactive, checkpointed, and autonomous modes.
- Offline acceptance fixture, scholarly/runtime/architecture pressure tests, source provenance
  manifest, operator guides, and 90% minimum coverage gate.
- Reversible installer for the five V1 Skills with collision protection, backups, install hashes,
  and preservation checks for existing local Skills.
- Isolated CPython 3.12 command runtime with an already-on-PATH user launcher, collision-safe
  installation, idempotence, and record-scoped rollback.
- Separate development and minimal runtime dependency locks with exact versions and wheel SHA-256
  hashes.

### Compatibility guarantees

- Contract, event, checkpoint, capability, and workflow specifications use version `1.0`.
- Installed Skill IDs are `research-os`, `research-framing`, `literature-intelligence`,
  `novelty-audit`, and `idea-to-novelty`.
- Capability IDs remain independently routable; a workflow may compose but never absorb their
  scholarly prompts, rubrics, templates, or gates.
- Project state remains under `.research-os/`: append-only `events.jsonl`, immutable run requests
  under `runs/<run-id>/request.json`, checkpoint JSON under `checkpoints/`, the
  `current-checkpoint` pointer, registry specifications, and the project operation lock.
- Compatible V1 updates may add optional fields or gates but will not silently reinterpret stored
  `1.0` data. Any incompatible contract or state change requires a new version and documented
  migration before old projects are opened for mutation.

### Known limitations

- V1 has no live literature-provider adapter; `local-manual` and offline artifacts are the
  supported default.
- V1 stops at novelty audit. Theory, design, analysis, manuscript drafting, figures, review, and
  submission packaging belong to later vertical slices.
- The lock targets CPython 3.12 on Windows x86-64; another platform requires a separately verified
  lock rather than silently substituting artifacts.
- Initial runtime provisioning requires the locked wheels to be available from pip's cache, an
  explicit wheelhouse, or the configured package index. Scholarly execution remains offline by
  default and does not require a secret.
