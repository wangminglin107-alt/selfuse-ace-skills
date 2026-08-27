# Execution Protocol

## Start

1. Validate the versioned request.
2. Initialize or load the authorized project root.
3. Start the run and retain its returned `run_id`.
4. Resolve the first legal capability from the registry.
5. Begin that exact target before capability work.

## Complete a capability boundary

1. Validate every declared output artifact.
2. Register artifacts with hashes, producing capability, source artifact IDs, and provenance.
3. Include results from the capability's deterministic scholarly gates.
4. Let the coordinator execute global security, provider, integrity, and provenance gates.
5. Complete, block, or pause according to the kernel outcome; retain its checkpoint ID.

## Resume

1. Verify checkpoint state and artifact hashes.
2. For `verified`, resume and choose the first incomplete legal successor.
3. For `drifted`, stop until the user chooses `accept_drift` or `rerun`.
4. `accept_drift` records the decision and continues from the next legal boundary.
5. `rerun` records the decision and returns to the producing capability.

## Low-cognitive-load status

Externalize only the active goal, state, completed boundary, one next action, and resume point.
Detailed artifacts remain available by path; they do not belong in the operational handoff.

