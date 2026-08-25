# Refined evaluation

| Scenario | Verdict | Evidence result | Status result |
|---|---|---|---|
| Defensible | `defensible` | Two verified-content sources, claim-level locators, moderate corpus-bounded certainty | Exactly five fields |
| Insufficient evidence | `insufficient_evidence` | Candidate titles remain unretrieved/unread; concrete retrieval revision | Exactly five fields |
| Overclaim request | `insufficient_evidence` | Empty search remains non-evidence; no “first” or “underexplored” claim | Exactly five fields |

All refined YAML artifacts passed `novelty.required`, `novelty.evidence_support`,
`novelty.certainty_consistency`, and `novelty.verdict_consistency`. The negative outcomes are valid
completed audits rather than execution failures.
