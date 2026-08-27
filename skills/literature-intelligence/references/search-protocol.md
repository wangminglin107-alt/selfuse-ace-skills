# Search protocol

## Search ledger

Record every executed, planned, or blocked search separately. Preserve the exact query,
timezone-aware execution timestamp, provider/source, status, and result count when known. Search
criteria and coverage limits describe what the process can and cannot establish; they are not
boilerplate.

If only local material is supplied, the query records the screening operation and provider is
`local-manual`. Do not imply Scopus, Web of Science, Google Scholar, CNKI, or another database was
searched unless it was actually queried through an authorized provider.

## Screening

Every source receives one decision (`include`, `exclude`, or `pending`) and a source-specific
reason. Do not use generic reasons that merely repeat the decision. Preserve negative and
contradictory evidence.

## Blocker handoff

A source shortage is a valid structured handoff. Put the concrete missing condition in
`blockers`, keep all planned searches visible, and populate coverage limits in both the ledger and
evidence map. A later run should resume these records rather than silently restart discovery.

## Claim mapping

State only what the inspected material supports. Each evidence note identifies the relevant
passage, section, page, or explicit local excerpt. `supports`, `contradicts`, `context`, and
`partial` describe the relationship; they do not upgrade verification status.
