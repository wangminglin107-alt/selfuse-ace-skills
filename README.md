# Research Skills OS

Research Skills OS is a contract-first local runtime for SSCI research capabilities. V1 keeps
capabilities independently callable while allowing a lightweight workflow to compose them with
durable state, checkpoints, and quality gates.

The implementation target is Python 3.12 on Windows. The default acceptance path is offline.

V1 contains five installable Skills: `research-os`, `research-framing`,
`literature-intelligence`, `novelty-audit`, and `idea-to-novelty`. The three scholarly
capabilities are independently callable. The workflow preset only selects and sequences them.

## Start here

- [Quickstart](docs/operator-guide/quickstart.md)
- [Standalone capabilities](docs/operator-guide/standalone-capabilities.md)
- [Run modes](docs/operator-guide/run-modes.md)
- [Checkpoints and resume](docs/operator-guide/checkpoints-and-resume.md)
- [Privacy and providers](docs/operator-guide/privacy-and-providers.md)

The command interface emits JSON on stdout and diagnostics on stderr. Exit codes are `0` success,
`2` validation, `3` blocked gate, `4` integrity/security, and `5` execution failure. No shell is
used internally and already-tokenized Windows arguments are never reparsed.
