# V2 decision inputs

V2 planning begins only after the owner answers the items below. Defaults are deliberately not
embedded in the runtime because they change scholarly scope, evidence authority, privacy, or
maintenance cost.

## Required before the next design amendment

1. Confirm that the next vertical slice is evidence synthesis plus theory architecture.
2. Name the first real project and its smallest end-to-end acceptance example.
3. Define the source of truth for literature: local files, Zotero, CNKI, international databases,
   or a declared combination.
4. Decide whether V2 remains fully offline by default and which data classifications may leave the
   machine through an optional provider.
5. Choose the minimum content-verification standard: full text, passage locator, page locator,
   metadata-only exceptions, and treatment of inaccessible candidates.
6. Select the contradiction representation and whether unresolved conflicts always force a human
   checkpoint.
7. Define theory-selection expectations for communication studies and sociology, including when a
   paper may remain descriptive rather than forcing a named theory.
8. Decide the bilingual terminology authority and whether Chinese/English alignment belongs in the
   same artifact or a later writing slice.
9. Identify the human review gates that autonomous mode may never cross.
10. Approve any new upstream repository only after license, locked commit, source-file, security,
    reuse-mode, modification, and local-test fields are ready for `SOURCE_MANIFEST.yaml`.

## Migration questions

- Can the next slice fit additive contract `1.0` artifact types, or does it require contract `1.1`?
- Does current-run artifact lineage remain sufficient for branching synthesis, or is an explicit
  artifact-edge graph required?
- Must older V1 projects be opened read-only until migration, or can the new runtime safely append
  additive events?
- Which checkpoint fields become mandatory for multi-branch theory comparison?

## Go/no-go evidence

Start implementation only when there is one approved fixture containing inspected source content,
at least one contradiction or null finding, an expected synthesis artifact, an expected theory
decision, privacy labels, and an explicit failing/blocked case. The next plan should implement that
single tracer-bullet slice before adding methods, drafting, figures, or publication packaging.
