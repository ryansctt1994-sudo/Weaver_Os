# Receipts: governance.claim_audit

Each run produces a report whose `report_hash` is the SHA-256 of the report (minus the hash itself) under RFC 8785 JCS (`hash_profile: jcs.rfc8785`). The report records what the result depends on:

- `git_commit`: the target revision
- `config` and `config_sha256`: the claims config used
- `terms_source`, `blocked_terms`, `watch_terms`: the rule applied
- `skill_version`

The report has no timestamps, so re-running the audit on the same commit with the same config reproduces the same `report_hash`. CI publishes the report as a build artifact. Store the hash with whatever decision the report informed.

Waivers are debt. `waiver_debt` counts them, so a growing number is visible over time instead of silently accepted.
