# Upstream source audit

`SOURCE_MANIFEST.yaml` is the acceptance record for every external or pre-existing local source
that materially influenced V1. It is not a bibliography and it does not grant runtime authority.

## Acceptance rules

Each record identifies the affected capability, repository, exact Git commit or local content
hash, source file, reuse mode, modifications, license source, security surface, and upstream/local
tests. Git records require a full 40-character commit. Local Skills use SHA-256 because they have
no independent Git provenance.

`verbatim`, `extracted`, and `adapted` records require a local target. `adapted` additionally
requires a modification description and a local regression test. A networked source must name its
endpoint, secrets, subprocess behavior, filesystem scope, and why its security review is accepted.
An uncertain license or non-approved security review blocks manifest validation.

## V1 decisions

- AI Research Writing, Spark-to-Paper, and AcademicSkills influenced contracts and gates at a
  conceptual level; their source code is neither copied nor executed.
- SciPilot Figure is `reference_only` for a later figure-quality capability.
- Qinyan is `reference_only` as a possible declared provider. Its Bash/curl path, bearer token,
  and remote API are not installed or invoked; provider output would remain unverified until
  independently checked.
- Seven existing local SSCI Skills remain untouched. Each is content-addressed; only
  `ssci-research-framing` has a declared conceptual relationship to a V1 Skill.

## Verification

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract\test_source_manifest.py -q
```

The test loads the strict Pydantic contract, checks locked commits, verifies every recorded source
file hash and local target, and exercises invalid-license and untested-adaptation fixtures.

