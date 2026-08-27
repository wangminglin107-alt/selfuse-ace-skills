# V2B Foundation Acceptance

V2B adds two foundations without changing the no-delete or offline-default policies.

## Accepted behavior

- A declared local PDF is resolved inside the project root, signature-checked, SHA-256 verified,
  uploaded only after its Zotero parent exists, and persisted by attachment key and content hash.
- A repeated apply reuses the existing Zotero item and attachment and leaves the Obsidian note
  unchanged.
- Metadata-only records remain legal but cannot claim inspected full text.
- Registry loading rejects unreachable nodes, stranded nodes, terminal nodes with outgoing edges,
  invalid review flags, undeclared source outputs, and target inputs that do not accept a mapping.
- The stricter validator exposed and repaired a latent V1 contract omission: `literature-intelligence`
  now explicitly accepts the two research-brief artifacts mapped by `idea-to-novelty`.

## Verification evidence

- `pytest tests/acceptance/test_v2b_foundation.py -q`: 1 passed.
- Focused registry and workflow contracts: 15 passed.
- Zotero/Obsidian integration suite before this acceptance slice: 44 passed.
- Ruff and mypy passed for the changed registry modules.

Full-suite evidence is recorded again in the final V2C acceptance report so the result covers the
combined system rather than this slice in isolation.
