---
name: literature-to-theory
description: Use when an initialized communication or sociology project should route a registered corpus through evidence synthesis, citation verification, and a resumable theory-review checkpoint.
---

# Literature to Theory

## Overview

Select the `literature-to-theory` workflow preset. It owns routing only. Load each capability Skill
when its registered node becomes active; that Skill remains the authority for scholarly work.

**REQUIRED SUB-SKILL:** Use `research-os` for lifecycle, mode, checkpoint, gate, and resume
behavior.

## Registered Graph

| Node | Capability | Mapped outputs |
|---|---|---|
| `knowledge-base` | `paper-knowledge-base` | `document_index` |
| `synthesis` | `evidence-synthesis` | `evidence_rows`, `synthesis_matrix`, `contradiction_ledger` |
| `verification` | `citation-verification` | `citation_support_audit` |
| `theory` | `theory-architecture` | terminal decision artifacts |

The graph runs `knowledge-base` → `synthesis` → `verification` → `theory`. The synthesis and
verification handoffs also feed the terminal node through declared artifact mappings.

## Execution

1. Resolve the workflow and begin `paper-knowledge-base`.
2. After each successful completion, use the kernel-provided next target and mapped artifacts.
3. Load only that node's capability Skill; do not restate its method in this preset.
4. Persist every declared checkpoint. A blocking result ends the current run boundary.
5. Stop at `theory-architecture` in all modes for the declared review decision.

## Resume

Verify the current checkpoint through `research-os`. Continue at the first incomplete node whose
predecessors and mappings are satisfied. If an artifact drifted, use only the explicit kernel
decision `accept_drift` or `rerun`.

## Handoff

Return the five operational fields required by `research-os`, name the active node, and recommend
one next action. Do not claim that a later node ran merely because its inputs appear available.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Putting a capability method in this preset | Load the registered capability Skill |
| Skipping verification | Follow the graph and mappings |
| Treating a proposed theory packet as selected | Stop at the terminal review boundary |
