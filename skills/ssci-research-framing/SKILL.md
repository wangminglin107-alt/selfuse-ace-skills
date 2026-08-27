---
name: ssci-research-framing
description: Use when an older request names SSCI Research Framing; preserves that invocation name while delegating all framing work to the canonical research-framing capability.
metadata:
  role: compatibility
  delegates_to: research-framing
---

# SSCI Research Framing Compatibility Route

Load and execute `research-framing` with the user's existing inputs and constraints. Return its
canonical artifacts and checkpoint; do not create an alternative brief, schema, rubric, or state.

Identify the canonical capability in the handoff so later workflow nodes resume from
`research-framing`, not this alias.
