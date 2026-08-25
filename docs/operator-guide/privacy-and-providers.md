# Privacy and providers

V1 defaults to `constraints.network: deny` and the `local-manual` provider. Local source content,
credentials, and sensitive artifacts are not sent anywhere by default.

A network provider requires all of the following: a declared provider ID, user authorization in
the request, endpoint and privacy declarations, secret names without secret values, timeouts,
response validation, provenance, and explicit verification state. A provider response is not
automatically verified scholarly evidence.

The Qinyan source is audited only as `reference_only`: its upstream Bash script calls curl, reads
`QINYAN_API_KEY`, and sends query payloads to a remote endpoint. V1 does not install or invoke it.
SciPilot Figure is also `reference_only` for a later capability.

When a provider gate blocks, inspect stderr, state, and gate results; change authorization or use a
local source, then rerun the blocked capability. Never paste credentials into requests, artifacts,
logs, checkpoints, or source manifests.

