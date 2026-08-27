---
name: ssci-revision-audit
description: Use when a revised communication or sociology SSCI manuscript needs an internal regression audit for argument, evidence, terminology, scope, or protected-anchor drift before external review.
---

# SSCI Revision Audit

## Boundary

Audit the author's revised manuscript and report defects. Do not rewrite prose, rerun citation
identity checks, select theory, simulate an external reviewer, or predict journal acceptance.

## Contract

Capability: `ssci-revision-audit`.

Consume `revised_chinese_manuscript`, `paper_argument_map`, `claim_evidence_plan`,
`terminology_ledger`, `citation_support_audit`, `prose_style_report`, and `draft_trace`. Produce
`revision_audit` and `revision_blockers`.

## Audit order

1. Reconstruct the thesis and verify that each section still performs its assigned job.
2. Compare major claims with the claim-evidence plan and current citation-support status.
3. Check selected theory, construct definitions, levels of analysis, scope conditions, and material
   contradictions for drift.
4. Compare citations, numbers, quotations, Evidence IDs, named constructs, claim-strength labels,
   and uncertainties with the draft trace.
5. Check terminology and abstract-body-conclusion alignment.

Use stable issue IDs. For every issue give location, observed regression, consequence, owning
capability, and a concrete closure test. A style preference is not a blocker unless it obscures
meaning or violates a declared contract.

## Handoff

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
