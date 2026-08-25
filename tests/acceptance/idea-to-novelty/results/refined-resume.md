The verified framing checkpoint remains authoritative: do not rerun `research-framing`. Resume the
existing run, map `research_brief_markdown` and `research_brief_metadata` into
`literature-intelligence`, and begin that exact capability. After validating and registering its
search ledger, source registry, and evidence map, stop at the literature checkpoint because the
run is interactive; do not begin `novelty-audit`.

If verification detects artifact drift, stop before continuation. Require an explicit kernel
decision: `accept_drift` records the drift and proceeds to `literature-intelligence`; `rerun`
returns to `research-framing`.

Current goal: Continue the `idea-to-novelty` preset at `literature-intelligence`.
Current state: The framing boundary is verified and unchanged; `literature-intelligence` is the first incomplete legal successor.
Completed: `research-framing`, recorded by the kernel; no work is rerun.
Next action: Begin `literature-intelligence` with the two mapped framing artifacts.
Resume from: The verified framing checkpoint; its kernel identifier was not provided and must not be invented.

## Evaluation

Pass: resumes at the immediate successor, preserves mappings, and distinguishes drift decisions.

