---
name: ssci-peer-review
description: Use when a communication or sociology SSCI manuscript needs a traceable external-review simulation after internal revision, with calibrated concerns and concrete resolution tests.
---

# SSCI Peer Review

## Boundary

Evaluate as an external scholarly reader. Do not rewrite the manuscript, act as the journal editor,
manufacture multiple reviewers, or predict acceptance.

## Contract

Capability: `ssci-peer-review`.

Consume `revised_chinese_manuscript`, `revision_audit`, `citation_support_audit`, and
`paper_argument_map`. Produce `peer_review_report` and `reviewer_issue_ledger`.

## Review method

1. Record received materials and what cannot be assessed.
2. Reconstruct the research question, thesis, theoretical move, evidence base, contribution, and
   stated boundaries before judging them.
3. Review conceptual contribution, literature conversation, evidence and inference, alternative
   explanations, organization, ethics, and scope according to the manuscript type.
4. Separate central validity or contribution defects from repairable major issues and local minor
   issues. Do not inflate style preferences.
5. For every concern provide a stable ID, location, claim pointer, evidence pointer, consequence,
   and resolution test. Use `NOT_LOCATABLE` or `AUTHOR_INPUT_NEEDED` rather than inventing material.

A simulated recommendation may be `Reject`, `Major Revision`, `Minor Revision`, or `Accept`, but it
must be labeled a reviewer judgment rather than an editorial decision.

## Handoff

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
