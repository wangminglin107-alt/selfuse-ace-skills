# Refined transcript: local sources

## Search ledger

```yaml
schema_version: "1.0"
search_question: "How do creator withdrawal narratives represent platform obligations?"
searches:
  - search_id: "local-screen-1"
    query: "Screen the supplied local fixture corpus for representations of platform obligations in creator withdrawal narratives."
    searched_at: "2026-08-25T07:25:41-05:00"
    provider: "local-manual"
    status: "executed"
    result_count: 2
inclusion_criteria:
  - "The inspected local content directly describes how creator withdrawal accounts represent or negotiate platform-related obligations."
exclusion_criteria:
  - "The inspected local content mentions creator burnout or withdrawal but does not describe platform-related obligations."
coverage_limits:
  - "Only the two synthetic records and their local Markdown files supplied in tests/fixtures/literature were screened."
  - "No external database or real publication corpus was searched, so the artifacts cannot establish prevalence, causality, a literature gap, or general findings beyond the fixture corpus."
blockers: []
```

## Source registry

```yaml
schema_version: "1.0"
sources:
  - source_id: "fixture-creator-exit-1"
    title: "Negotiating Exit from Platform Work"
    status: "verified_content"
    decision: "include"
    decision_reason: "The local body text directly describes creator withdrawal accounts as negotiations involving audiences, sponsors, and platform visibility systems."
    provenance:
      provider: "local-manual"
      locator: "tests/fixtures/literature/fixture-creator-exit-1.md"
      retrieved_at: "2026-08-25T07:25:41-05:00"
      content_sha256: "fae5752a1cc99c4b7008d8955bc83f69e52abd3053ebd70a5b9537dcf97d92af"
    metadata_verification: "verified"
    content_verification: "verified"
  - source_id: "fixture-creator-exit-2"
    title: "Burnout Narratives in Creator Careers"
    status: "excluded"
    decision: "exclude"
    decision_reason: "The inspected text describes creator-career burnout but does not represent or discuss platform obligations, so it does not answer the search question."
    provenance:
      provider: "local-manual"
      locator: "tests/fixtures/literature/fixture-creator-exit-2.md"
      retrieved_at: "2026-08-25T07:25:41-05:00"
      content_sha256: "2f245b7cfff306f3d8c5b6f28b649b023e529341a45c65bde8422800346f4992"
    metadata_verification: "verified"
    content_verification: "verified"
```

## Evidence map

```yaml
schema_version: "1.0"
claims:
  - claim_id: "claim-1"
    statement: "Within the included synthetic fixture, creator withdrawal accounts represent platform-related obligation as one part of a negotiation spanning audiences, sponsors, and platform visibility systems."
    links:
      - source_id: "fixture-creator-exit-1"
        relation: "supports"
        evidence_note: "In tests/fixtures/literature/fixture-creator-exit-1.md, the first body paragraph states that creator withdrawal accounts negotiate obligations to audiences, sponsors, and platform visibility systems."
coverage_limits:
  - "This claim is limited to the included synthetic fixture and is not a claim about real publications, creator populations, frequency, or causality."
  - "The second fixture was inspected but excluded because it discusses burnout without describing platform obligations."
unsupported_claims:
  - "Platform obligations cause creator withdrawal."
  - "This representation is common among creators."
  - "The fixture corpus establishes a verified gap in the literature."
```

Current goal: Answer the search question with traceable evidence from only the supplied local fixture corpus.
Current state: Complete with corpus-bounded uncertainty; one source is included and one is excluded with a source-specific reason.
Smallest meaningful action: Independently re-check both SHA-256 hashes and validate the three YAML artifacts with `evaluate_literature_artifacts`.
Result / blocker: The three artifacts validate, all four literature gates pass, both hashes match the fixture manifest, and verification states remain separate and accurate; no blocker remains, and no checkpoint was created because no project root was authorized.
One recommended next action: Supply an authorized real-publication corpus if findings beyond these synthetic fixtures are required.
