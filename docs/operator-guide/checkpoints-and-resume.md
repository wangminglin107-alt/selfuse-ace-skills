# Checkpoints and resume

List and verify checkpoints before resuming:

```powershell
research-os checkpoint list --project 'C:\path with spaces\project'
research-os checkpoint verify --project 'C:\path with spaces\project' --id <checkpoint-id>
```

A verified workflow checkpoint resumes at the first incomplete node whose predecessors and mapped
artifacts are satisfied. It does not rerun completed work. In `idea-to-novelty`, an unchanged
framing checkpoint resumes at `literature-intelligence`; an unchanged literature checkpoint resumes
at `novelty-audit`.

Verification compares materialized state and every checkpoint artifact hash. Drift returns exit
code `4` and must be reported. Choose explicitly:

- `accept_drift`: record the decision and continue from the next legal boundary;
- `rerun`: return to the capability that produced the drifted boundary.

Never edit a checkpoint file, invent a resume token, or proceed after drift by merely describing
the edit in prose.

