# SSCI Research Skills OS V2C Chinese Writing Design

## Purpose

V2C integrates the seven existing SSCI writing skills without duplicating their scholarly method,
adds one missing prose-style audit capability, and proves the composition by producing a real
4,000–6,000 Chinese-character theoretical research note from 8–12 verified sources.

## Canonical ownership

`research-os` is the only lifecycle orchestrator. `ssci-paper-writer` becomes a compatibility
entry point and does not own separate state. `research-framing` is canonical;
`ssci-research-framing` remains a compatibility entry point.

The remaining canonical capabilities are:

- `ssci-argument-architecture`: manuscript thesis, argument spine, section/paragraph map and
  claim-to-evidence plan; it consumes synthesis and theory outputs rather than recreating them;
- `ssci-section-drafting`: the only capability allowed to draft or rewrite manuscript prose;
- `academic-prose-style-audit`: diagnostic only; it finds formulaic prose, repetitive structures,
  generic abstraction and rhythm problems and emits constrained revision tasks;
- `ssci-bilingual-writing`: optional Chinese-English conceptual and rhetorical alignment;
- `ssci-revision-audit`: internal argument and regression audit, not citation re-verification or
  prose rewriting;
- `ssci-peer-review`: independent external-review simulation.

Section drafting stays one capability but uses small on-demand references for theoretical notes,
introductions, literature conversations, theoretical analysis, discussion, Chinese prose and
English prose.

## Workflow

The thin `evidence-to-chinese-note` preset sequences:

1. `ssci-argument-architecture`;
2. `ssci-section-drafting` for the Chinese draft;
3. `citation-verification` for post-draft support regression;
4. `academic-prose-style-audit`;
5. `ssci-section-drafting` in constrained-revision mode;
6. `ssci-revision-audit`;
7. `ssci-peer-review`.

Because V1 workflows are acyclic, initial drafting and constrained revision are separate nodes
using the same capability. Every node checkpoints. Theory selection remains an upstream mandatory
human decision. English alignment is not in the default preset; it is independently callable and
is smoke-tested on the abstract.

## Style audit

The audit borrows source-level mechanisms from PaperSpine, Spark-to-Paper, Nature Skills,
AI Research Writing, Humanities Thesis and Qinyan after license and security review. Deterministic
metrics cover high-precision filler phrases, repeated paragraph openings, connector density,
sentence-length variation and repeated n-grams. Metrics are advisory except for missing audit
coverage or meaning-lock drift. No detector score is fabricated and no platform-pass promise is
made.

The audit saves `prose-style-report.json` and `prose-revision-matrix.md`. Each requested revision
points to a manuscript unit, diagnosis, protected anchors and allowed edit. Protected anchors
include citations, numbers, Evidence IDs, named constructs and claim-strength labels.

## Pilot acceptance

The GSMA project is expanded to 8–12 identity-verified sources. Durable claims require inspected
full text or a source type strong enough for the claim; metadata-only and abstract-only records stay
visible but cannot support durable claims. The main deliverable is a 4,000–6,000 Chinese-character
research note excluding references and appendices.

Acceptance requires complete claim-to-evidence coverage for major claims, no fabricated citations,
numbers or findings, preserved contradictions, unchanged protected anchors after style revision,
a revision audit, an independent peer-review report, an abstract bilingual smoke test, durable
checkpoints, Zotero records and Obsidian project notes. Scholarly limitations may remain, but the
system must report them rather than silently calling the note submission-ready.

## Upstream provenance

`SOURCE_MANIFEST.yaml` records exact repository commit, source file, hash, reuse mode, modifications,
license, security decision and tests. Unlicensed or incompatible code is reference-only. Upstream
routers are not imported wholesale; accepted mechanisms are adapted behind local contracts.

