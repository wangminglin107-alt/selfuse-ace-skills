---
name: research-framing
description: Use when a communication studies or sociology topic, observation, early memo, or draft question needs a bounded SSCI research problem before literature search, novelty assessment, theory selection, or study design.
---

# Research Framing

## Overview

Produce a traceable research brief without turning missing information into plausible-looking
facts. A complete framing artifact may contain explicit unknowns; it never claims novelty.

## Invocation

1. Read direct material and registered input artifacts. If an OS request is supplied, verify that
   its target is `research-framing`.
2. In an initialized OS project, call `research-os run start`, then `research-os target begin`
   before scholarly work. Use the returned `run_id`; never invent lifecycle identifiers.
3. Fill `assets/research-brief.template.yaml` first. Render the aligned Markdown artifact from
   `assets/research-brief.template.md` and apply `references/framing-rubric.md`.
4. Validate metadata with `evaluate_research_brief`. Correct failures; do not weaken fields or
   gates. Register both artifacts, then call `research-os target complete`.
5. Without a user-authorized project root, return both artifacts inline and state that persistence
   and checkpoint creation are unavailable.

## Scope Rule

Use `known` only when a value is traceable to `user_input`, `source_artifact`, or
`user_decision`. Otherwise use `unknown`, a null value, and `explicit_unknown`. Calling a choice
“provisional” does not authorize inventing a country, population, period, platform, theory,
sample size, or method.

## Claim Rule

- Separate phenomenon from research problem.
- Treat constructs as working definitions.
- Contribution type and statement remain `provisional`.
- Do not add citations from memory or unsupported literature summaries.
- Do not make “first study,” “unstudied,” uniqueness, gap, or novelty claims. Route those to
  `literature-intelligence` and `novelty-audit`.
- Do not expand framing into a full research design unless separately requested.

## Run Modes

- `interactive`: complete this capability, checkpoint, show status, and stop.
- `checkpointed`: obey the kernel review stop; do not continue past it.
- `autonomous`: the standalone capability may recommend another capability but cannot invoke it;
  only an authorized workflow may continue.

## User-Facing Status

After the detailed artifacts, return exactly these five fields:

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
| Inventing a polished “provisional” design | Record unknowns and request one smallest decision |
| Hiding uncertainty to look complete | Externalize it in metadata and status |
| Treating a motivating observation as evidence | Label its evidentiary status |
| Drafting literature or novelty claims | Leave claims empty and route to later capabilities |
