---
name: paper-knowledge-base
description: Use when a communication or sociology project needs durable local paper records, stable source identities, file hashes, passage locators, version links, or corpus privacy declarations.
---

# Paper Knowledge Base

## Overview

Build a project-scoped corpus that later work can cite by stable source, artifact, and content
location. This Skill supplies scholarly records; `research-os` owns lifecycle and validation.

## Contract

Capability: `paper-knowledge-base`

Inputs: `source_registry`, `source_document`.

Outputs: `document_index`, `corpus_status`.

Use `assets/document-index.template.json`. Start and begin the capability through `research-os`,
write only the declared outputs, register them, then complete the target so the kernel recomputes
the corpus gates. Without an initialized project, return the artifacts inline and state that no
checkpoint exists.

## Corpus Recipe

For every included document:

1. Preserve the bibliographic identity, source ID, local artifact ID, project-relative path,
   import time, and current file SHA-256.
2. Declare document type, language, access state, privacy label, extraction method, and warnings.
3. Record each usable content block with a page or stable section, block ID, and content SHA-256.
4. Make duplicate, replacement, and superseded-version relationships explicit.
5. Keep metadata verification separate from full-content availability.

A metadata-only record may remain in the index, but it is not ready for passage-level evidence.
Do not send restricted text to a provider without a separate user authorization and provider
declaration.

## Quick Reference

| Situation | Record |
|---|---|
| Full text inspected | `content_availability=full_text` plus stable locators |
| Only metadata exists | `content_availability=metadata_only`; no content claim |
| New version replaces old | old `superseded_by_source_id`; new `supersedes_source_id` |
| Duplicate uncertain | retain both IDs in `unresolved_duplicate_groups` |

## Common Mistakes

| Mistake | Correction |
|---|---|
| Absolute or parent-traversing path | Use a project-relative artifact path |
| Reusing an old hash after file edits | Re-register and update the index |
| Omitting privacy because a file is local | Declare privacy for every document and corpus |

## User-Facing Status

```text
Current goal:
Current state:
Smallest meaningful action:
Result / blocker:
One recommended next action:
```
