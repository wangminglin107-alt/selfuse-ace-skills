---
name: idea-to-novelty
description: Use when a communication studies or sociology idea should be developed through research framing, traceable literature intelligence, and an evidence-bounded novelty audit as one resumable preset.
---

# Idea to Novelty

## Overview

Select the `idea-to-novelty` workflow preset. This Skill owns no scholarly prompt, rubric, or
template: those remain in the three independently callable capability Skills.

**REQUIRED SUB-SKILL:** Use `research-os` for lifecycle, mode, checkpoint, gate, and resume
behavior.

## Registered Graph

| Node | Capability | Declared handoff |
|---|---|---|
| `frame` | `research-framing` | research brief Markdown + metadata |
| `literature` | `literature-intelligence` | search ledger + source registry + evidence map |
| `novelty` | `novelty-audit` | novelty matrix + bounded audit |

Invoke these capabilities in this order. Load each capability Skill only when its node becomes
active. Never jump directly from framing to novelty.

## Execution

1. Resolve the workflow and begin `research-framing`.
2. Complete its gates and checkpoint. In `interactive`, stop. In `checkpointed`, stop at the
   declared framing review boundary. In `autonomous`, continue only if no gate blocks.
3. Map both framing artifacts into `literature-intelligence`; preserve source verification states.
4. Map all three literature artifacts into `novelty-audit`. Candidate or missing sources cannot
   become verified-content evidence merely because the workflow is autonomous.
5. Complete only after the terminal novelty checkpoint. A blocked gate is a valid workflow
   outcome, not permission to soften or skip it.

## Resume

Use the kernel checkpoint, never a prose label. An unchanged framing boundary resumes at
`literature-intelligence`; an unchanged literature boundary resumes at `novelty-audit`. Drift
requires explicit `accept_drift` or `rerun` according to `research-os`.

## Handoff

After capability artifacts, end with the five `research-os` operational fields. Name the active
node and distinguish work produced inline from a kernel-recorded completion. Recommend exactly one
next action.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Embedding research instructions in the preset | Load the active capability Skill |
| Treating an unverified citation as inspected evidence | Block at literature/provenance gates |
| Calling `idea-to-novelty` a capability | Call it a workflow preset |
| Re-running completed framing after verified resume | Begin `literature-intelligence` |

