Load the verified checkpoint, reuse the unchanged framing artifact, and invoke the next incomplete novelty-analysis capability. Do not rerun research framing.

If artifact drift is detected, stop the resume, record the mismatch, and invalidate dependent state. Either restore the checkpointed artifact or accept the revision and rerun framing plus any downstream work before creating a new verified checkpoint.

Current goal: Advance the framed idea through novelty analysis.
Current state: Checkpoint verified; framing artifact unchanged.
Completed: Research framing.
Next action: Run the first unfinished novelty-analysis capability.
Resume from: Immediately after research framing.

## Baseline observation

The response skipped the registered `literature-intelligence` node and jumped from framing toward
novelty analysis. It also did not distinguish explicit `accept_drift` from `rerun`.

