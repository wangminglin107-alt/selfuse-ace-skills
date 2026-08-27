# Standalone capabilities

Use a capability directly when you need only that research operation. Set request target `kind` to
`capability` and use one exact ID:

- `research-framing`: idea or phenomenon to a bounded research brief;
- `literature-intelligence`: direct search question or existing brief to traceable literature
  artifacts;
- `novelty-audit`: existing brief plus literature artifacts to an evidence-bounded verdict.
- `paper-knowledge-base`: inspected local sources to a content-addressed document index and corpus
  status;
- `evidence-synthesis`: exact passages to claim-level rows, synthesis groups, contradictions, and
  coverage;
- `citation-verification`: separate bibliographic identity checks from passage-level claim support;
- `theory-architecture`: evidence rows and contradictions to constructs, theory candidates, and a
  user-owned decision packet.

Standalone invocation uses the same registered specification, schemas, gates, artifact envelopes,
and checkpoint service as a workflow node. A standalone capability cannot silently invoke the next
capability. Its `next_action` is a recommendation only.

If no authorized project root exists, the Skill may return artifacts inline, but it must disclose
that no durable state or checkpoint was created. If a required input is absent, pass it as an
explicit unknown or blocker; never reconstruct it from model memory.

`idea-to-novelty` and `literature-to-theory` are workflow presets, not capabilities. The latter
routes `paper-knowledge-base` → `evidence-synthesis` → `citation-verification` →
`theory-architecture`; it does not duplicate any node's scholarly method.
