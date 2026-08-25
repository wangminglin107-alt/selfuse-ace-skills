# Run modes

The mode changes stopping behavior, not scholarly standards.

| Mode | Normal stop | Best use |
|---|---|---|
| `interactive` | After every capability checkpoint | Close supervision or one session at a time |
| `checkpointed` | At declared review nodes and material blockers | Several automatic steps with human gates |
| `autonomous` | Terminal node or any blocking gate | Full fixture runs for later human audit |

All modes retain provenance, uncertainty, decisions, gate results, and checkpoints. Autonomous mode
cannot relabel a candidate citation as verified content, cross a denied provider boundary, accept
hash drift, or soften a failed gate.

At a stop, the Skill reports one current goal, state, completed boundary, next action, and resume
point. This externalized state reduces context switching without compressing the underlying
artifacts or analysis.

