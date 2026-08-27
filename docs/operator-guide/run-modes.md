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

In `literature-to-theory`, the theory node is a declared review boundary in every mode. Autonomous
execution may prepare a theory decision packet, but it stops with `authorization_state: proposed`;
it cannot select a theory on the user's behalf. A material unresolved contradiction pauses or
blocks according to the gate and mode rather than being averaged away.

At a stop, the Skill reports exactly five operational fields: `Current goal`, `Current state`,
`Completed`, `Next action`, and `Resume from`. This externalized state reduces context switching
without compressing the underlying artifacts or analysis.
