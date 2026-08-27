# Local SSCI Research Skills OS installation record

Installed at: `2026-08-27T05:56:12.8619669Z`

Last idempotent `-WhatIf` verification: `2026-08-27` (all twelve actions: `unchanged`)

Source commit at installation: `e3aa451639ed36246e3789ecf04d3659327184ed`

Skill home: `C:\Users\10710\.codex\skills`

Machine record: `C:\Users\10710\.codex\skills\.research-skills-os-install.json`

Runtime installed at: `2026-08-26T02:57:45.3539377Z`

Runtime root: `C:\Users\10710\.codex\research-skills-os-runtime`

PATH launcher: `C:\Users\10710\bin\research-os.cmd`

Runtime installation ID: `50ffee2de0634c1680e70cbc6a53665e`

## Installed Skills

| Skill | Installed SHA-256 |
|---|---|
| `citation-verification` | `e9f411bd298698e1bc1168a9b6b6149c437f9d4cf0b29a54ba56099ed152817c` |
| `evidence-synthesis` | `ca2539ba8e14407facd81a25c578300dfb177ae1567944ae547ad3eeaac4b112` |
| `research-os` | `83465593708c0a89c71e767f2bc6990ae1da02c396052d3e3c27cc318fb8b25b` |
| `research-framing` | `67dc0328ae502abef5d96f8ce76370a3332c05a2a54240e357768e396b6df862` |
| `literature-intelligence` | `3ceba432e1c1ca11926adde7d80bb5e3700b0b34cb42c5f12c8939d8fabf11f5` |
| `literature-to-theory` | `3a08e5efe5a34c64f9f43f4718d6df020995b2ae8fd001be548e51416453bf3e` |
| `novelty-audit` | `dee1e91ceb19801b4e02837f3bf2e490a11ff142eb50c7c7fdb0b3dd4d581b05` |
| `idea-to-novelty` | `dad5749d7b0962f94396a4c3daef0ac64f7d174e32e9931d7a7bf8c9867675fd` |
| `paper-knowledge-base` | `6a9f18d4e1f17fe9ea72295fabb2f73394614d28c124a9597c0d27436fc9b0ab` |
| `theory-architecture` | `98bffffa38d60d88f065043ff7683dd69ee6e3e5486a61d86720bace098fc628` |
| `academic-prose-style-audit` | `368ddd822e0d2910e9ea0d521ab9aaee3d8b39b520c8b44eb26a14dff4b6b419` |
| `evidence-to-chinese-note` | `2aa92d9095664d41b2aca78ee19f54a69998a586555304520b802f601312d9bc` |

The installer independently calculated each source and installed tree digest and refused to write
the record until all twelve pairs matched.

## Preserved existing SSCI Skills

The installer target list contains only the twelve names above. The seven existing `ssci-*` Skills
remain outside that list and are protected by installer regression tests.

## Verification evidence

- Native Windows PowerShell 5.1 `-WhatIf`: twelve `unchanged` actions, zero collisions.
- Temporary skill-home integration suite covers installation, replacement, preservation,
  idempotence and record-scoped uninstall.
- Native Windows PowerShell 5.1 install, idempotent reinstall, and uninstall smoke: PASS.
- Runtime installer contract suite: `8 passed`; the combined installation suite is `13 passed`.
  Its seven runtime distributions are exact pins with SHA-256 hashes. Malformed backup-root,
  runtime-junction, backup-root-junction, and launcher-only collision regressions are included.
- Fresh ordinary PowerShell resolved `research-os` from `C:\Users\10710\bin\research-os.cmd`;
  `research-os --help` and a real `project init` smoke both passed. A second runtime install
  returned `status: unchanged`.
- An actual record-scoped runtime uninstall removed both runtime and launcher; reinstall restored
  both, and another fresh PowerShell command passed.
- Actual `-WhatIf`: twelve `unchanged` actions; zero collisions; zero `ssci-*` targets.
- The original V1 ephemeral discovery smoke covered its five-Skill slice. Current Codex discovery
  exposes the complete twelve-Skill bundle, including both V2C entries.
- The fresh CLI emitted an unrelated failed recommended-plugin catalog request during startup.
  No Research Skills OS provider ran, no fixture data was transmitted, and the scholarly smoke
  test itself stayed local/read-only.

## Rollback

Run:

```powershell
& 'C:\Users\10710\Documents\Codex\2026-08-25\referenced-chatgpt-conversation-this-is-an\work\research-skills-os-v1-implementation\scripts\uninstall-skills.ps1' -SkillHome 'C:\Users\10710\.codex\skills'
```

The uninstaller acts only on destinations in the machine install record, refuses to remove a
modified installed tree, and restores any recorded pre-install backup.

To remove the isolated Python runtime and PATH launcher, run:

```powershell
& 'C:\Users\10710\Documents\Codex\2026-08-25\referenced-chatgpt-conversation-this-is-an\work\research-skills-os-v1-implementation\scripts\uninstall-runtime.ps1'
```

The runtime uninstaller verifies the exact recorded runtime and launcher paths plus the launcher
hash before removal. It does not modify the user's global Python installation or PATH value.
