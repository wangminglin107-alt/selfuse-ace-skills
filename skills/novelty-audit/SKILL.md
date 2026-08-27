---
name: novelty-audit
description: Use when a communication studies or sociology research question and proposed contribution need comparison with nearest literature, claim-level novelty support, contribution classification, calibrated certainty, or a defensibility verdict.
---

# Novelty Audit

## Overview

Test a candidate contribution against inspected nearest work. The objective is an accurate verdict,
not a positive verdict; `contradicted` and `insufficient_evidence` are successful audit outcomes.

## Invocation

1. Read the research brief plus literature search ledger, source registry, and evidence map. In an
   initialized OS project, start and begin `novelty-audit` before analysis.
2. Build the Markdown matrix from `assets/novelty-matrix.template.md` and aligned metadata from
   `assets/novelty-audit.template.yaml`. Apply both references.
3. Run `evaluate_novelty_audit`, correct unsupported claims or lower the verdict, register both
   artifacts, and complete the target. With no authorized project root, return both inline and
   disclose that no checkpoint was created.

## Comparison Recipe

Select the genuinely nearest available work; do not force a count. Compare only relevant
dimensions such as phenomenon, population/context, construct, mechanism, theory, data, method, or
level of analysis. Each material difference needs a source ID plus passage/section locator.

Absence of results, a new combination of familiar words, candidate titles, metadata-only records,
or embedding distance is not novelty proof. Never write “first study,” “unstudied,” “unique,” or
“underexplored” from those signals.

## Verdicts

- `defensible`: every material claim is supported by verified-content nearest work and bounded to
  the searched corpus.
- `conditional`: some distinction is supported, but a material comparison remains unresolved.
- `insufficient_evidence`: nearest work is absent, candidate, unretrieved, metadata-only, or too
  narrow for the requested claim.
- `contradicted`: verified nearest work already establishes the material contribution claim.

Every non-`defensible` verdict requires one concrete revision recommendation. Certainty follows the
weakest material source; `high` requires exclusively verified content and should be rare.

## Run Modes

`interactive` stops after the audit. `checkpointed` stops for contribution review. `autonomous`
continues only through an authorized workflow and cannot upgrade a failed evidence gate.

## User-Facing Status

After both artifacts, return exactly:

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
| Treating zero hits as novelty | Use `insufficient_evidence` |
| Calling candidate titles nearest-work evidence | Preserve their nonterminal status |
| Forcing a positive verdict | Report the evidence-bounded outcome |
| Using fixed scores or similarity thresholds | Compare explicit dimensions and evidence |
