# Research Skills OS

Research Skills OS is a contract-first local runtime for SSCI research capabilities. V1 keeps
capabilities independently callable while allowing a lightweight workflow to compose them with
durable state, checkpoints, and quality gates.

The implementation target is Python 3.12 on Windows. The default acceptance path is offline.

For the frozen V1 development environment, install [requirements.lock](requirements.lock) with
`python -m pip install --require-hashes -r requirements.lock`, then install this project with
`python -m pip install --no-deps -e .`.

For normal local use on Windows, install the five Skills and the isolated command runtime from a
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

V1 contains five installable Skills: `research-os`, `research-framing`,
`literature-intelligence`, `novelty-audit`, and `idea-to-novelty`. The three scholarly
capabilities are independently callable. The workflow preset only selects and sequences them.

## Start here

- [Quickstart](docs/operator-guide/quickstart.md)
- [Standalone capabilities](docs/operator-guide/standalone-capabilities.md)
- [Run modes](docs/operator-guide/run-modes.md)
- [Checkpoints and resume](docs/operator-guide/checkpoints-and-resume.md)
- [Privacy and providers](docs/operator-guide/privacy-and-providers.md)
- [Local installation record](docs/architecture/local-install-record.md)
- [Changelog](CHANGELOG.md)

The command interface emits JSON on stdout and diagnostics on stderr. Exit codes are `0` success,
`2` validation, `3` blocked gate, `4` integrity/security, and `5` execution failure. No shell is
used internally and already-tokenized Windows arguments are never reparsed.
