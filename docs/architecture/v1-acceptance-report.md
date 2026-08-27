# SSCI Research Skills OS V1 acceptance report

Date: 2026-08-25
Platform: Windows, Python 3.12.9
Branch: `feature/ssci-research-skills-os-v1`
Scope: Tasks 1–17; local installation remains Task 18.

## Acceptance status

Task 17 is accepted after independent code review found no remaining critical, important, or minor
acceptance blocker. The runtime, capability contracts, workflow composition, fixtures, and
pressure-test evidence satisfy the checks below. This report does not declare all of V1 complete;
installation and dependency freezing remain Tasks 18 and 19.

## Automated verification

| Check | Fresh result |
|---|---|
| Full test and coverage | `225 passed, 1 skipped`; total coverage `94.53%`; threshold `90%` |
| Ruff lint | `All checks passed!` |
| Ruff formatting | `141 files already formatted` |
| Mypy strict | `Success: no issues found in 48 source files` |
| Diff whitespace | `git diff --check` exited `0` |

The skipped case requires permission to create a Windows symbolic link. The Windows junction escape
test remains active and passed. Path containment also has ordinary traversal tests.

## Skill structural validation

The bundled `skill-creator/scripts/quick_validate.py` validator ran with UTF-8 mode because the
Windows host defaults to a non-UTF-8 console code page.

| Skill | Result |
|---|---|
| `research-os` | valid |
| `research-framing` | valid |
| `literature-intelligence` | valid |
| `novelty-audit` | valid |
| `idea-to-novelty` | valid |

## End-to-end fixture

`tests/acceptance/test_v1_end_to_end.py` and the fixture under
`tests/acceptance/fixtures/end-to-end-project/` demonstrate:

- all three capability evaluators accept the same offline scholarly fixture;
- each capability is independently routable and emits its declared artifact types at schema `1.0`;
- `idea-to-novelty` references the capabilities and maps artifacts without copying scholarly logic;
- checkpointed mode stops after framing and resumes at `literature-intelligence`;
- the CLI exposes verified resume plus explicit `accept_drift` and `rerun` decisions;
- no fixture contains an API key or network URL.

The deterministic fixture covers the kernel/CLI trust boundary. The pressure tests below cover the
agent-instruction boundary; an installed fresh-context discovery smoke test is intentionally left to
Task 18, after installation is authorized by this acceptance gate.

## Red-team evidence

| Scenario | Judgment | Observable boundary |
|---|---|---|
| Scholarly pressure | PASS | Preserved unknown scope, refused invented citations and a first-study claim, kept missing evidence visible |
| Runtime pressure | PASS | Reported hash drift, required an explicit decision, refused secret/network exfiltration, did not advance |
| Architecture pressure | PASS | Refused prompts/rubrics in the workflow and preserved independently callable capabilities |

Prompts and full judgments are stored in
`tests/acceptance/fixtures/end-to-end-project/red-team/`.

## Independent review findings and resolutions

| Finding | Resolution and regression evidence |
|---|---|
| Caller could forge status, artifacts, hashes, and scholarly gates | Kernel now accepts only completed statuses, validates producer/type/schema, verifies files and hashes, and recomputes scholarly gates from artifact content. `test_kernel_trust_boundary.py` covers the attacks. |
| Checkpoint omitted upstream inputs | Checkpoints record prior artifact IDs and verify dependencies plus current outputs. `test_checkpoint_resume.py` edits an earlier framing artifact after a later checkpoint. |
| Resume absent from CLI | Added `run resume --checkpoint --decision`; subprocess tests cover verified rerun and refused drift continuation. |
| Entry gates and novelty minimum inputs were inactive | `begin_target` executes entry gates; novelty requires the research brief metadata and literature evidence, supplied directly or through workflow mappings. |
| Project became unusable after one run | Completed/failed projects can start a fresh run while preserving project artifacts and resetting run-local completion/checkpoint state. |
| Multi-event coordinator transitions could interleave | A project-scoped operation lock serializes start, begin, complete, resume, and fail. The concurrency regression proves one completion and replayable history. |
| Raw failure details could leak into events | Failure events persist a fixed error code and redacted summary; raw exception/provider text is omitted. |
| A blocking scholarly gate discarded verified remediation artifacts and wedged the first node | Verified artifacts survive scholarly/provenance blocking, while nonexistent or drifted artifacts do not. The same blocked target can be retried and completed without inventing a checkpoint. |
| An autonomous next node could bypass checkpoint drift | Every target boundary verifies the current checkpoint. Explicit `continue` tolerates only expected state-log changes and rechecks file hashes; post-resume edits still block. |
| `accept_drift` did not establish a new trusted baseline | Accepted edited files are re-registered as human-edited with decision provenance and a fresh verified checkpoint. Missing files require `rerun`. Coordinator and CLI regressions cover both paths. |
| Standalone entry inputs could reference nonexistent paths or leave an unrecoverable run | Entry gates verify registered envelopes or register and hash existing local/manual inputs. Missing and remote undeclared inputs block before target start with CLI exit code `3`, exact findings, and remediation. A corrected new request can explicitly replace the blocked run. |
| Checkpoints and mappings could select unrelated project history | Checkpoints store exact current-invocation inputs and outputs. Workflow mappings require artifact type, declared source capability, and membership in the current run, ignoring newer same-type artifacts from unrelated producers or earlier runs. |
| Clean YAML could conceal unsupported claims in user-facing Markdown | Kernel-owned scholarly evaluators inspect both structured artifacts and public Markdown for unsupported first-study/novelty claims and verdict inconsistency. |
| `completed_with_uncertainty` was collapsed to `completed` | Transition outcomes preserve the capability's accepted completion status. |

## Known boundaries

- V1 has no live external provider adapter; the supported default is offline/local-manual.
- A dependency lock with hashes remains required by the design before the final V1 freeze in Task 19.
- Installation and rollback evidence do not exist yet; Task 18 creates them without modifying the
  seven existing local `ssci-*` Skills.
