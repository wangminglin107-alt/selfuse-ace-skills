Verify the existing checkpoint and framing artifact hashes. If verified, resume the same run,
preserve `research-framing` as completed, map its declared artifacts into the `literature` node,
and begin `literature-intelligence`. In interactive mode, stop at its completed checkpoint; do not
begin `novelty-audit` yet.

If drift is detected, stop before continuation. Require an explicit kernel decision:
`accept_drift` records the drift and continues to `literature-intelligence`; `rerun` returns to
`research-framing`. Do not invent missing identifiers.

Current goal: Continue `idea-to-novelty` from the verified framing boundary.
Current state: The existing run is paused after unchanged `research-framing`.
Completed: `research-framing`.
Next action: Resume the run and begin `literature-intelligence` with the mapped framing artifacts.
Resume from: The existing kernel-issued checkpoint or resume identifier, which was not provided in the scenario.

## Evaluation

Pass: preserves the completed node, chooses the declared immediate successor, distinguishes drift
decisions, and does not invent a lifecycle identifier.

