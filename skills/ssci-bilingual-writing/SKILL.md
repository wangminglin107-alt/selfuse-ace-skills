---
name: ssci-bilingual-writing
description: Use when an approved Chinese communication or sociology manuscript needs English conceptual translation, abstract alignment, terminology control, or a bilingual meaning-regression audit.
---

# SSCI Bilingual Writing

## Boundary

Align concepts and rhetoric across Chinese and English. Do not add evidence, strengthen claims,
redesign the argument, or replace the canonical drafting capability.

## Contract

Capability: `ssci-bilingual-writing`.

Consume `chinese_manuscript` or `revised_chinese_manuscript`, `terminology_ledger`, and
`protected_anchors`. Produce `english_manuscript`, `translated_abstract`, and
`bilingual_alignment_report` according to the requested scope. The Chinese manuscript remains the
source of truth unless the user explicitly changes that decision.

## Alignment method

1. Classify each unit as definition, claim, evidence, interpretation, limitation, or transition.
2. Preserve actor, modality, causal status, population, time, scope, citations, numbers, quotations,
   Evidence IDs, and uncertainty.
3. Split Chinese clause chains and reorder information only when English rhetoric requires it;
   record material structural choices.
4. Use the terminology ledger. Add a proposed term only when no approved equivalent exists, and
   return the choice for review.
5. Compare source and target proposition by proposition. Any missing protected anchor blocks the
   handoff.

For an abstract smoke test, translate only the abstract and report meaning drift; do not infer that
the whole manuscript is English-ready.

## Handoff

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
