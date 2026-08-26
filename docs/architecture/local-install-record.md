# Local SSCI Research Skills OS installation record

Installed at: `2026-08-25T14:40:42.6098483Z`

Last idempotent reinstall verification: `2026-08-25T14:46:44.5199512Z` (`status: unchanged`)

Source commit at installation: `a47c35895b1877e13bdfced85b295bebe5c567df`

Skill home: `C:\Users\10710\.codex\skills`

Machine record: `C:\Users\10710\.codex\skills\.research-skills-os-install.json`

Runtime installed at: `2026-08-26T02:54:16.6454153Z`

Runtime root: `C:\Users\10710\.codex\research-skills-os-runtime`

PATH launcher: `C:\Users\10710\bin\research-os.cmd`

Runtime installation ID: `3f9cbebf516b421285f5dca9fa9aeee1`

## Installed Skills

| Skill | Installed SHA-256 |
|---|---|
| `research-os` | `ef3b0be80f2e8ab29537cbf35d9d96d08cceb898584efb53536a133834c8923b` |
| `research-framing` | `67dc0328ae502abef5d96f8ce76370a3332c05a2a54240e357768e396b6df862` |
| `literature-intelligence` | `3ceba432e1c1ca11926adde7d80bb5e3700b0b34cb42c5f12c8939d8fabf11f5` |
| `novelty-audit` | `dee1e91ceb19801b4e02837f3bf2e490a11ff142eb50c7c7fdb0b3dd4d581b05` |
| `idea-to-novelty` | `dad5749d7b0962f94396a4c3daef0ac64f7d174e32e9931d7a7bf8c9867675fd` |

The installer independently calculated each source and installed tree digest and refused to write
the record until all five pairs matched.

## Preserved existing SSCI Skills

The dry run targeted only the five names above. Pre/post installation tree hashes matched for all
seven existing Skills:

| Skill | Preserved SHA-256 |
|---|---|
| `ssci-argument-architecture` | `148e80598d5fbed2fa51c28c7ea4276b3f740629401c8c0e4fd5ffc3bc123ebf` |
| `ssci-bilingual-writing` | `86ce3d15c38c122bbf49c7cbc0867ef7429a86abad8ebc2630a660a9803c208e` |
| `ssci-paper-writer` | `0b38c5c01729f619f0acefa2c66edfcecfd6ec9006886e4226c6deae491170f1` |
| `ssci-peer-review` | `aa4b380b2ac7ef02d3747a050f5228b48d39e0de3baf4767f0cb69670b2c5756` |
| `ssci-research-framing` | `3c70b78879af4de7e57b59c74433d9aababd522dd6f8a19f3e2c54e717481b8f` |
| `ssci-revision-audit` | `5b2959addabf0fa5028445a68809b0494f447f68b0dc6fd57624484331e03b23` |
| `ssci-section-drafting` | `b6a8725743a6f02dd219da3c72755714d809cbf8a37784fe344282c934a5c1b9` |

## Verification evidence

- Temporary skill-home integration suite: `5 passed`.
- Native Windows PowerShell 5.1 install, idempotent reinstall, and uninstall smoke: PASS.
- Runtime installer contract suite: `6 passed`; the combined installation suite is `11 passed`.
  Its seven runtime distributions are exact pins with SHA-256 hashes. Malformed backup-root and
  runtime-junction regressions are included.
- Fresh ordinary PowerShell resolved `research-os` from `C:\Users\10710\bin\research-os.cmd`;
  `research-os --help` and a real `project init` smoke both passed. A second runtime install
  returned `status: unchanged`.
- An actual record-scoped runtime uninstall removed both runtime and launcher; reinstall restored
  both, and another fresh PowerShell command passed.
- Actual `-WhatIf`: five `install` actions; zero collisions; zero `ssci-*` targets.
- Fresh ephemeral Codex context: opened all five installed `SKILL.md` files, inspected the offline
  fixture, preserved standalone/workflow separation, and returned `SMOKE_STATUS: PASS` with no
  missing Skills.
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
