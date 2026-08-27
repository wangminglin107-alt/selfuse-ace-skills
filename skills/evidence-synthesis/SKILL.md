---
name: evidence-synthesis
description: Use when inspected communication or sociology sources must become claim-addressable evidence rows, synthesis groups, coverage limits, or a visible contradiction ledger.
---

# Evidence Synthesis

## Overview

Turn inspected source passages into bounded evidence without merging source language, translation,
analyst inference, null findings, or contradictions. `research-os` owns files and gates.

## Contract

Capability: `evidence-synthesis`

Inputs: `research_brief_metadata`, `novelty_audit`, `document_index`.

Outputs: `evidence_rows`, `synthesis_matrix`, `contradiction_ledger`, `coverage_report`.

Start and begin `evidence-synthesis` through `research-os`. Write JSONL rows from
`assets/evidence-row.template.json` and the ledger from
`assets/contradiction-ledger.template.json`; register all four declared outputs before completing
the target.

## Evidence-Row Recipe

Each row contains the exact original-language passage and its page or stable section, block ID,
passage SHA-256, source/artifact IDs, research-question dimension, context, method, population,
boundaries, evidence role, verifier note, and downstream claim IDs.

Keep `source_claim` and `author_inference` separate. A reviewed translation never replaces the
original passage. If full content or a stable locator is absent, record the gap in `coverage_report`
instead of producing a content-supported row.

## Contradiction Handling

Group rows only when they address the same construct or mechanism. If verified rows support and
contradict the same group, create a ledger entry naming both rows, competing claims, possible scope
explanations, unresolved issue, and materiality. Keep null results as `evidence_role=null`.

A material open contradiction is a blocker. A non-material open disagreement needs an explicit
boundary note. Never obtain coherence by deleting adverse rows.

## Quick Reference

| Evidence state | Action |
|---|---|
| Exact passage + locator | Create a verified-content row |
| Translation reviewed | Store beside the original |
| Analyst interpretation | Store only in `author_inference` |
| Opposing result | Preserve it and update the ledger |

## Common Mistakes

| Mistake | Correction |
|---|---|
| Summary used as source text | Return to the exact passage |
| Causal claim from association | Bound the downstream claim |
| Empty coverage dimension hidden | List it in `uncovered_dimensions` |

## User-Facing Status

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
