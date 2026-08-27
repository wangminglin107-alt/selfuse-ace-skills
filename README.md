# Research Skills OS

Research Skills OS is a contract-first local runtime for SSCI research capabilities. V1 keeps
capabilities independently callable while allowing a lightweight workflow to compose them with
durable state, checkpoints, and quality gates.

The implementation target is Python 3.12 on Windows. The default acceptance path is offline.

For the frozen V1 development environment, install [requirements.lock](requirements.lock) with
`python -m pip install --require-hashes -r requirements.lock`, then install this project with
`python -m pip install --no-deps -e .`.

For normal local use on Windows, install the twelve Skills and the isolated command runtime from a
PowerShell prompt in this repository:

```powershell
& '.\scripts\install-skills.ps1'
& '.\scripts\install-runtime.ps1'
research-os --help
```

The runtime uses [requirements-runtime.lock](requirements-runtime.lock), lives under
`%USERPROFILE%\.codex\research-skills-os-runtime`, and exposes `research-os` through the existing
`%USERPROFILE%\bin` PATH directory. It does not alter the user's global Python packages or PATH
value. Both installers have matching record-scoped uninstall scripts.

The install bundle contains twelve Skills. V1 provides `research-os`, `research-framing`,
`literature-intelligence`, `novelty-audit`, and `idea-to-novelty`. V2A adds
`paper-knowledge-base`, `evidence-synthesis`, `citation-verification`, `theory-architecture`, and
the lightweight `literature-to-theory` workflow. V2C adds `academic-prose-style-audit` and the
`evidence-to-chinese-note` workflow. Every capability remains independently callable;
workflow Skills only select and sequence capabilities.

## Start here

- [Quickstart](docs/operator-guide/quickstart.md)
- [Standalone capabilities](docs/operator-guide/standalone-capabilities.md)
- [Run modes](docs/operator-guide/run-modes.md)
- [Checkpoints and resume](docs/operator-guide/checkpoints-and-resume.md)
- [Privacy and providers](docs/operator-guide/privacy-and-providers.md)
- [Evidence and citation states](docs/operator-guide/evidence-and-citation-states.md)
- [Contradictions and theory decisions](docs/operator-guide/contradictions-and-theory-decisions.md)
- [V2A acceptance report](docs/architecture/v2a-acceptance-report.md)
- [V2C Chinese writing acceptance report](docs/architecture/v2c-acceptance-report.md)
- [Local installation record](docs/architecture/local-install-record.md)
- [Changelog](CHANGELOG.md)

The command interface emits JSON on stdout and diagnostics on stderr. Exit codes are `0` success,
`2` validation, `3` blocked gate, `4` integrity/security, and `5` execution failure. No shell is
used internally and already-tokenized Windows arguments are never reparsed.
