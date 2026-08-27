# Verdict rules

| Verdict | Evidence condition | Required action |
|---|---|---|
| `defensible` | Verified-content nearest work supports every material difference | State corpus boundary; recommendation may be null |
| `conditional` | At least one supported difference and at least one unresolved material comparison | Name the unresolved comparison and how to test it |
| `insufficient_evidence` | No inspected nearest work or evidence too weak/narrow | Retrieve/read the closest candidates or broaden the documented search |
| `contradicted` | Verified content already makes the candidate contribution claim | Withdraw, reframe, or narrow based on the demonstrated overlap |

## Certainty ceiling

- Candidate/unretrieved evidence: no positive novelty certainty.
- Verified metadata only: identity is known; substantive certainty remains low.
- Verified content: moderate certainty is possible within the audited corpus.
- High certainty requires all material links to verified content plus adequate coverage; it never
  means universal proof that no work exists.

The verdict is lowercase and machine-stable. Do not substitute `not defensible`, `novel`, `probably
novel`, or uppercase display variants. Search absence remains a coverage limitation and must keep
`search_absence_as_evidence: false`.
