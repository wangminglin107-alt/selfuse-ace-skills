# Baseline transcript: local sources

## Baseline response

### Literature search ledger

| Field | Record |
|---|---|
| Research question | How do creator withdrawal narratives represent platform obligations? |
| Search scope | `tests/fixtures/literature/sample-source-records.yaml` only |
| Corpus type | Two synthetic records; not real publications |
| Retrieval method | Local fixture enumeration |
| Query terms | “creator withdrawal,” “platform obligations,” “exit,” “burnout,” “visibility systems” |
| Records screened | 2 |
| Records retained | 2: one substantive source and one boundary-setting source |
| External generalization | Prohibited; findings apply only to this fixture corpus |

| Source ID | Decision | Reason |
|---|---|---|
| `fixture-creator-exit-1` | Include | Directly describes withdrawal accounts negotiating obligations involving platform visibility systems. |
| `fixture-creator-exit-2` | Include as limitation evidence | Addresses burnout narratives but explicitly does not establish platform causality or population prevalence. |

### Source registry

| Source ID | Title | Evidence available | Local path | SHA-256 | Role |
|---|---|---|---|---|---|
| `fixture-creator-exit-1` | *Negotiating Exit from Platform Work* | Abstract-level record | `tests/fixtures/literature/fixture-creator-exit-1.md` | `1111111111111111111111111111111111111111111111111111111111111111` | Primary evidence |
| `fixture-creator-exit-2` | *Burnout Narratives in Creator Careers* | Abstract-level record | `tests/fixtures/literature/fixture-creator-exit-2.md` | `2222222222222222222222222222222222222222222222222222222222222222` | Boundary/limitation evidence |

### Claim-to-source evidence map

| Claim ID | Corpus-bounded claim | Source | Support | Limits |
|---|---|---|---|---|
| C1 | In this corpus, creator withdrawal accounts represent platform obligations through negotiations with platform visibility systems, alongside obligations to audiences and sponsors. | `fixture-creator-exit-1` | Direct abstract-level support | The record does not specify the mechanisms, direction, or consequences of those obligations. |
| C2 | The corpus does not support treating creator burnout as proof that platforms caused withdrawal. | `fixture-creator-exit-2` | Direct negative/boundary support | The record describes burnout narratives but explicitly withholds causal attribution. |
| C3 | The corpus does not support claims about how prevalent these representations are among creators. | `fixture-creator-exit-2` | Direct negative/boundary support | No population data or prevalence estimate is supplied. |

Operational status: complete for the two-record synthetic fixture. The answer is abstract-level and corpus-bounded. Within this material, platform obligation is represented mainly as negotiation with visibility systems embedded among audience and sponsor obligations; neither platform causality nor population prevalence is established.

## Missing expected artifacts or traceability fields

- No authors, publication years, venues, DOI/URL, or publication types.
- No full-text evidence, quotations, page numbers, section locators, or passage-level anchors.
- No database/search-engine name, execution timestamp, raw search output, or deduplication record.
- No explicit quality appraisal or study-method metadata.
- The referenced local Markdown files were not inspected, so their hashes were recorded but not independently verified.
- No files were created; all three requested artifacts exist only in the response.
