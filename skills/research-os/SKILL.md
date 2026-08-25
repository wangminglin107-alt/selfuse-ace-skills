---
name: research-os
description: Use when research work must be routed, checkpointed, resumed, validated, or composed from independently registered capabilities in interactive, checkpointed, or autonomous mode.
---

# Research OS

## Overview

Coordinate lifecycle state; never perform or duplicate a capability's scholarly method. The
registry is authoritative for target identity and order, and the kernel is authoritative for run,
gate, checkpoint, and resume identifiers.

## Routing Contract

1. Resolve the requested target by exact registered ID and kind.
2. For a capability target, load only that capability Skill and contract.
3. For a workflow target, load its thin preset, then invoke each registered capability in graph
   order. Pass artifacts only through declared `artifact_mappings`.
4. Use kernel lifecycle operations for start, begin, complete, checkpoint, verify, and resume.
   Never invent a run ID, checkpoint ID, resume token, gate result, or completed node.
5. A workflow may select and sequence capabilities; it may not contain prompts, rubrics,
   templates, or scholarly rules.

Read [execution-protocol.md](references/execution-protocol.md) whenever starting, pausing, or
resuming a run.

## Mode Boundaries

| Mode | Boundary behavior |
|---|---|
| `interactive` | Stop after every completed capability checkpoint. |
| `checkpointed` | Continue until the next declared review node or blocking condition. |
| `autonomous` | Continue to a terminal node unless a gate blocks; autonomy cannot waive gates. |

At every stop, expose the smallest meaningful next action. Do not recap unrelated work or start a
later capability while paused.

## Resume Rule

Verify the checkpoint before reading its continuation. If verified, select the first incomplete
node whose predecessors and mapped artifacts are satisfied. If drifted, require the explicit
kernel decision `accept_drift` or `rerun`; `rerun` returns to the capability that produced the
drifted boundary. Never skip an intermediate registered node.

## Operational Handoff

End an orchestration response with exactly these five fields:

```text
Current goal:
Current state:
Completed:
Next action:
Resume from:
```

Use kernel-issued identifiers when available. If no project root was authorized, say persistence
and a durable resume token are unavailable instead of fabricating either.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Calling a workflow a capability | Name it a preset and name the active registered capability |
| Jumping from framing to novelty | Follow the graph through `literature-intelligence` |
| Treating prose as a checkpoint | Use the kernel-issued checkpoint/resume identifier |
| Continuing after a blocking gate | Persist the blocker and stop at that node |

