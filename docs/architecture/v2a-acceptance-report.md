# V2A acceptance report

Date: 2026-08-26  
Status: accepted locally on Windows

## Scope accepted

- Four independently callable capabilities: `paper-knowledge-base`, `evidence-synthesis`,
  `citation-verification`, and `theory-architecture`.
- One thin preset: `literature-to-theory`.
- Existing V1 capabilities and `idea-to-novelty` remain available.
- Ten Research Skills OS Skills are installed; the seven pre-existing SSCI Skills are outside the
  installer target list and retain their recorded content hashes.

## Verification evidence

Fresh full-suite command:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=research_skills_os --cov-report=term-missing --cov-fail-under=90 -q
```

Result: `366 passed, 1 skipped in 78.23s`; total coverage `93.81%` (required minimum `90%`).

Focused V2A command completed with `148 passed in 15.10s`. `ruff check .`, strict mypy over
`src/research_skills_os`, and `git diff --check` completed without errors before this report was
written; they are repeated after the report update as the final clean gate.

## Installed Skill directory hashes

| Skill | SHA-256 |
|---|---|
| `citation-verification` | `08c3a219b707385b2c04b334971826b2363a1949695053090d9630e0cfc6feb1` |
| `evidence-synthesis` | `ca2539ba8e14407facd81a25c578300dfb177ae1567944ae547ad3eeaac4b112` |
| `idea-to-novelty` | `dad5749d7b0962f94396a4c3daef0ac64f7d174e32e9931d7a7bf8c9867675fd` |
| `literature-intelligence` | `3ceba432e1c1ca11926adde7d80bb5e3700b0b34cb42c5f12c8939d8fabf11f5` |
| `literature-to-theory` | `3a08e5efe5a34c64f9f43f4718d6df020995b2ae8fd001be548e51416453bf3e` |
| `novelty-audit` | `dee1e91ceb19801b4e02837f3bf2e490a11ff142eb50c7c7fdb0b3dd4d581b05` |
| `paper-knowledge-base` | `6a9f18d4e1f17fe9ea72295fabb2f73394614d28c124a9597c0d27436fc9b0ab` |
| `research-framing` | `67dc0328ae502abef5d96f8ce76370a3332c05a2a54240e357768e396b6df862` |
| `research-os` | `0f2f8a518e418ddc146708545c300af44ebe74c468af65db112a1c42d8ff3d5d` |
| `theory-architecture` | `98bffffa38d60d88f065043ff7683dd69ee6e3e5486a61d86720bace098fc628` |

The prior `research-os` directory was backed up before replacement at
`C:\Users\10710\.codex\skills\.research-skills-os-backups\20260826T163608Z-819a94fdb1f6439d99633e3fc0abf537\research-os`.

## Preserved local SSCI Skill hashes

| Skill | SHA-256 |
|---|---|
| `ssci-argument-architecture` | `75a806b44409fc614449363370533831985454c80bfc61423a8bc95d13b9405c` |
| `ssci-bilingual-writing` | `6606cc7a84fb2b626814dfad57b1bd6090e4b923b26e61d0523b1a03a44b9ae0` |
| `ssci-paper-writer` | `186db7e52e43a0c06a1e68660f4935d3ee1f126f68d553390374b9c6c649b367` |
| `ssci-peer-review` | `1c64e3322521189f949291850fb59712083707043fc6b7b9e2c483f59a9d78c6` |
| `ssci-research-framing` | `4bcb2d328a5c0e16b17dbc8947340f8232380f7c27304d8156d42e6b1fcac6c1` |
| `ssci-revision-audit` | `cdf01018f0d416d985852bd6066b3a86e28e8bab43743243a82a41f8d1f060d3` |
| `ssci-section-drafting` | `1d49b6db5018907c68b6c16d9c35b7d6c205de0fbb3261d99e6178f57125048e` |

## Real GSMA checkpoint

- Run ID: `run-20260826T164356Z-558539e3`.
- Current checkpoint: `20260826T164357Z_71304d7a`.
- Completed sequence: knowledge base → synthesis → citation verification → theory architecture.
- Kernel outcome: `pause` at `theory-architecture` with no failed gates.
- Resume verification: `verified`, state hash matched, all 13 checkpoint inputs/outputs matched.
- Theory decision: `authorization_state: proposed`; no theory was selected for the user.

The pilot also verified one Zotero collection containing three records, three generated Obsidian
source notes, one editable project overview, and a second-run no-op with stable note hashes and
timestamps.

## Known limitations

- This is a three-source tracer bullet, not a systematic review or a completed statistical study.
- The current Obsidian writer may show nested YAML frontmatter from a source note, and an existing
  note's top managed properties are not yet refreshed when metadata changes.
- PDF attachment ingestion is intentionally deferred to a separate capability with explicit
  licensing and storage checks.
- The theory checkpoint is intentionally paused until the user reviews real data-analysis results.
