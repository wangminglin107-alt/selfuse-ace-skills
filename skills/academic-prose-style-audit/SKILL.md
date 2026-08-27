---
name: academic-prose-style-audit
description: Use when Chinese communication or sociology manuscript prose needs an explainable audit for formulaic language, repetitive structure, connector stacking, rhythm, or meaning-lock drift before bounded revision.
---

# Academic Prose Style Audit

## Boundary

Diagnose prose and create revision tasks; never rewrite the manuscript. Do not claim to detect AI
authorship or promise a detector score. Citation support, argument validity, and peer review remain
owned by their specialist capabilities.

## Contract

Capability: `academic-prose-style-audit`.

Consume `chinese_manuscript` and its `protected_anchors`. Produce `prose_style_report` and
`prose_revision_matrix`. Read [zh-patterns.md](references/zh-patterns.md) when classifying findings.

Run deterministic checks for high-precision filler, repeated paragraph openings, connector density,
sentence-length variation, and repeated character n-grams. Treat them as prompts for judgment, not
proof of authorship. Missing citations, numbers, quotations, Evidence IDs, named constructs,
claim-strength labels, or uncertainty statements is blocking.

For each retained finding, name the manuscript unit, excerpt, diagnosis, protected anchors, allowed
edit, and resolution test. Request no more than three bounded revision passes; persistent evidence or
argument problems return to their canonical owner.

## Handoff

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
