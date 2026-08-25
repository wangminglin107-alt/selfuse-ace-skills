---
name: literature-intelligence
description: Use when a communication studies or sociology research brief, search question, local source collection, citation list, or literature claim needs traceable discovery, screening, provenance, verification status, and claim-to-source mapping.
---

# Literature Intelligence

## Overview

Produce three auditable artifacts—search ledger, source registry, and evidence map—without
converting absent, partial, or unverified sources into literature findings.

## Invocation

1. Accept either a research brief or a direct search question. In an initialized OS project,
   start and begin `literature-intelligence` through `research-os` before scholarly work.
2. Read registered sources through `local-manual` by default. Do not use network or secrets unless
   the request authorizes a declared provider; V1 has no live provider fallback.
3. Fill all three YAML assets. Apply `references/search-protocol.md` and
   `references/evidence-status.md`, then run `evaluate_literature_artifacts`.
4. Register the three artifacts and complete the target. Without an authorized project root,
   return them inline and disclose that no checkpoint was created.

## Missing-Source Recipe

When no source content is available, still return:

- a ledger containing planned/blocked searches, timestamp, provider, criteria, limits, and blocker;
- an empty source registry;
- an empty evidence map whose coverage limit states that no findings were established.

The run is honestly blocked or completed with uncertainty. Never fill the gap with remembered
citations, plausible titles, database-like results, or substantive synthesis.

## Verification and Claim Lock

- `candidate` is a lead; `retrieved` means bytes exist; `screened` records an inclusion decision.
- `verified_metadata` verifies bibliographic identity only. It is not content support.
- `verified_content` requires inspected content, current SHA-256, verified metadata, and a
  passage-level evidence note.
- If content or the proposed claim changes, lower the status and re-check the link. Never carry a
  stale verification label forward.
- Every material claim links to a registered source; otherwise list it in `unsupported_claims`.
- Abstract-only records cannot support detailed findings or causal conclusions.

## Run Modes

`interactive` stops after this capability. `checkpointed` obeys provider/review stops.
`autonomous` may continue only inside an authorized workflow and never bypasses source blockers.

## User-Facing Status

After the three artifacts, return exactly:

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```

## Common Mistakes

| Mistake | Correction |
|---|---|
| Treating search absence as evidence | Record a coverage limit, not a finding |
| Marking an abstract content-verified | Keep metadata and content states separate |
| Listing a source without a decision reason | Record include/exclude/pending rationale |
| Inventing citations under deadline pressure | Return the blocker artifacts unchanged |
