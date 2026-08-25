# Checkpoints and resume

List and verify checkpoints before resuming:

```powershell
research-os checkpoint list --project 'C:\path with spaces\project'
research-os checkpoint verify --project 'C:\path with spaces\project' --id <checkpoint-id>
research-os run resume --project 'C:\path with spaces\project' --checkpoint <checkpoint-id> --decision continue
```

A verified workflow checkpoint resumes at the first incomplete node whose predecessors and mapped
artifacts are satisfied. It does not rerun completed work. In `idea-to-novelty`, an unchanged
framing checkpoint resumes at `literature-intelligence`; an unchanged literature checkpoint resumes
at `novelty-audit`.

Verification compares materialized state and every checkpoint artifact hash. Drift returns exit
code `4` and must be reported. Choose explicitly:

- `accept_drift`: record the decision, mark edited files as human-edited, and publish a fresh
  verified checkpoint before continuing from the next legal boundary;
- `rerun`: return to the capability that produced the drifted boundary.

`accept_drift` applies only to files that still exist. A missing checkpoint artifact cannot be
re-baselined and requires `rerun`.

```powershell
research-os run resume --project 'C:\path with spaces\project' --checkpoint <checkpoint-id> --decision accept_drift
research-os run resume --project 'C:\path with spaces\project' --checkpoint <checkpoint-id> --decision rerun
```

Never edit a checkpoint file, invent a resume token, or proceed after drift by merely describing
the edit in prose.
