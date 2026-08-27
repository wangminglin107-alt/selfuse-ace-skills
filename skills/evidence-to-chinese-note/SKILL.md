---
name: evidence-to-chinese-note
description: Use when an approved communication or sociology theory decision and verified evidence should run through the registered Chinese theoretical-note drafting, citation, style, revision, and peer-review workflow.
---

# Evidence to Chinese Note

## Preset boundary

This is a workflow preset, not a scholarly capability. Load `research-os`, resolve the registered
`evidence-to-chinese-note` workflow, and execute its seven nodes in graph order. Do not embed or
replace any node's method here.

Required upstream material includes an approved theory decision, evidence rows, synthesis and
contradiction artifacts, citation-support state, and the research brief. Missing theory approval or
durable claim support is a blocker, not permission to infer it.

Use the selected run mode exactly:

- `interactive`: stop at every node checkpoint;
- `checkpointed`: stop after citation regression and constrained revision;
- `autonomous`: continue through peer review unless a gate blocks.

English drafting is outside this preset. Invoke `ssci-bilingual-writing` independently for the
abstract smoke test or a later English manuscript.

## Handoff

Return the five Research OS operational fields with kernel-issued identifiers. Name the active
capability and the smallest meaningful next action; do not summarize unrelated prior nodes.
