---
name: ssci-section-drafting
description: Use when an approved SSCI argument architecture and verified evidence must become Chinese or English manuscript prose, or when a bounded revision matrix must be applied without changing protected meaning.
---

# SSCI Section Drafting

## Boundary

This is the only manuscript prose writer in Research Skills OS. It consumes approved architecture
and evidence; it does not select theory, discover literature, verify citations, diagnose style, or
conduct peer review.

## Contract

Capability: `ssci-section-drafting`.

Required planning inputs are `paper_argument_map`, `section_outline`, `claim_evidence_plan`,
`terminology_ledger`, `evidence_rows`, and `citation_support_audit`. Initial drafting produces
`chinese_manuscript`, `draft_trace`, and `author_input_needed`. Constrained revision additionally
consumes the current manuscript, `prose_style_report`, and `prose_revision_matrix`, and emits
`revised_chinese_manuscript` with an updated trace.

## Route by deliverable

- For a Chinese theoretical research note, read [theoretical-note.md](references/theoretical-note.md).
- For Chinese academic prose or constrained revision, read [zh-style.md](references/zh-style.md).

Draft one paragraph job at a time, then reverse-outline its claim, evidence, interpretation, and
boundary. Attach only registered Evidence IDs and verified citation records. When support is absent,
weaken the claim or emit `AUTHOR_INPUT_NEEDED`; never add a citation or fact from memory.

In constrained revision, alter only units named in the revision matrix. Preserve citations,
Evidence IDs, quotations, numbers, construct names, claim-strength labels, and explicit
uncertainties unless a separately verified artifact authorizes the change.

## Handoff

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
