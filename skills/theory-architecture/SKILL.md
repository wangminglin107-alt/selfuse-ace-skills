---
name: theory-architecture
description: Use when a communication or sociology synthesis needs constructs, mechanisms, levels of analysis, bounded theory candidates, or a human-reviewed theory decision.
---

# Theory Architecture

## Overview

Develop theory only to the level supported by verified evidence. A descriptive recommendation is
valid; theory selection remains a human decision.

## Contract

Capability: `theory-architecture`

Inputs: `research_brief_metadata`, `novelty_audit`, `synthesis_matrix`,
`contradiction_ledger`, `citation_support_audit`.

Outputs: `theory_candidates`, `construct_map`, `theory_rationale`,
`theory_decision_packet`.

Start and begin `theory-architecture` through `research-os`. Create the artifacts from
`assets/theory-decision.template.json`, register them, and complete the target. Stop after the
proposed decision packet for user review.

## Theory Recipe

1. Define each construct, level of analysis, and supporting evidence-row IDs.
2. Express each proposed relation as a mechanism, not as an unexplained arrow.
3. List assumptions, boundary conditions, limitations, and every material contradiction.
4. Compare candidates using evidence fit, construct compatibility, level consistency, and
   explanatory necessity.
5. Recommend `single_theory`, `bounded_integration`, `mechanism_framework`, or `descriptive`.

Multiple theories require a compatibility rationale. Cross-level relations require an explicit
cross-level rationale. Unknown evidence references, hidden assumptions, and omitted material
contradictions are blockers.

Use `authorization_state=proposed` for every model-generated packet. Record
`authorization_state=selected` only when the kernel supplies a user decision ID. Do not infer
selection from silence, autonomous mode, or a plausible best candidate.

## Quick Reference

| Evidence condition | Recommendation |
|---|---|
| One mechanism has direct bounded support | Consider `single_theory` |
| Compatible mechanisms add distinct value | Consider `bounded_integration` |
| Mechanism is clearer than named theory fit | Use `mechanism_framework` |
| Mechanism support is insufficient | Use `descriptive` |

## Common Mistakes

| Mistake | Correction |
|---|---|
| Choosing a famous theory first | Begin with constructs, mechanism, and evidence |
| Hiding a level mismatch | State and justify the cross-level link |
| Treating a proposal as approval | Keep it proposed until a user decision is recorded |

## User-Facing Status

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
