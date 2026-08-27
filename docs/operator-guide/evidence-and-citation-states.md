# Evidence and citation states

V2A deliberately separates “这篇文献是真的” from “这篇文献支持这句话”。They are independent
checks and live in different artifacts.

## Source access and evidence

`content_availability` may be `full_text`, `abstract_only`, `metadata_only`, or `unavailable`.
Only inspected content with an exact passage, stable locator, and matching SHA-256 may become a
verified evidence row. An evidence row records one of `supports`, `qualifies`, `contradicts`,
`null`, or `background`; adverse and null evidence must not be deleted merely to simplify a claim.

## Citation identity

`identity_state` records whether title, authors, year, identifier, route, and publication status
identify the claimed work. Its values include `verified`, `mismatch`, `not_found`, `suspicious`, and
`manual_needed`. A DOI match is identity evidence, not passage evidence.

## Content support

`support_state` records whether one exact passage supports one downstream claim: `supports`,
`partial`, `misaligned`, `contradicted`, `unavailable`, or `manual_needed`. The claim strength may
not exceed passage strength. For example, an associational passage cannot validate a causal claim.

A `metadata_only` candidate can remain in a source registry or Zotero reading queue, but it cannot
enter the support audit as verified content. Any unresolved identity, support, route, or publication
problem remains visible in `citation-blockers.json`.
