---
name: ssci-paper-writer
description: Use when an older request names SSCI Paper Writer or asks to continue the SSCI writing pipeline; routes the request into Research OS without owning a second workflow.
metadata:
  role: compatibility
  delegates_to: research-os
---

# SSCI Paper Writer Compatibility Route

Delegate lifecycle, mode, checkpoint, and resume handling to `research-os`. Preserve the user's
requested scope: a single scholarly operation routes to its canonical capability; an end-to-end
request routes to a registered workflow preset.

Do not create separate state or restate a scholarly method here. For the Chinese theoretical-note
path, use `evidence-to-chinese-note`. Report the canonical target selected so old invocations remain
understandable and resumable.
