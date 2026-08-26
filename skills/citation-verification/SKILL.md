---
name: citation-verification
description: Use when a communication or sociology citation, DOI, Chinese source, book, thesis, report, policy, dataset, or manuscript claim needs independent identity and content-support checking.
---

# Citation Verification

## Overview

Audit whether a source is the claimed work and, separately, whether its exact passage supports the
downstream statement. Metadata validity never substitutes for content support.

## Contract

Capability: `citation-verification`

Inputs: `source_registry`, `document_index`, `evidence_rows`.

Outputs: `citation_identity_audit`, `citation_support_audit`, `citation_blockers`.

Start and begin `citation-verification` through `research-os`. Use
`assets/citation-audit.template.json` to create the three declared artifacts, register them, and
complete the target so the kernel performs the authoritative audit.

## Identity Route

Choose the route by source type and available identifiers:

| Source | Preferred trace |
|---|---|
| DOI article | DOI plus title, authors, container, year |
| Article without DOI | title, authors, journal, year, authorized official record |
| Book or chapter | ISBN/catalog record plus edition and contributors |
| Thesis, report, policy, dataset | issuing institution or repository record |

Record claimed and verified fields separately. Normalize harmless formatting only; title, author,
year, identifier, correction, retraction, or expression-of-concern differences remain visible.
Use `manual_needed` when an authorized authoritative record cannot settle identity.

## Content-Support Route

For every manuscript or research claim, link a `citation_support_audit` record to an
`evidence_rows` row ID and exact locator hash. Compare claim strength with passage strength.
Descriptive or associational text cannot establish a stronger causal statement. Use `partial`,
`misaligned`, `contradicted`, or `unavailable` rather than stretching the passage.

Every unresolved mismatch has a corresponding open item in `citation_blockers`. A metadata-only
audit may verify identity, but content support remains unavailable or not applicable.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Treating missing DOI as false source | Use a source-type-appropriate official route |
| Verifying only title | Compare authors, venue, year, identifier, and publication status |
| Citing a whole paper for one claim | Link the exact evidence row and locator hash |

## User-Facing Status

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
