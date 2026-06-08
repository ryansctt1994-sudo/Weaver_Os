# Promotion Rules

Weaver OS separates implementation from authority.

## Non-Negotiable Boundary

```text
architecture != authority
specification != implementation
declared_success != replay_verified_success
capability != authorization
```

## Promotion Requirements

A component may only be promoted when it has:

1. passing automated tests,
2. reproducible local execution instructions,
3. explicit evidence of expected behavior,
4. no failing security or schema checks,
5. a receipt or release note identifying the commit, test command, and result.

## Current Status

```text
ARCHITECTURE_FROZEN
EVIDENCE_NOT_FROZEN
AUTHORITY_NOT_EARNED
```

## Release Receipt Minimum

A release receipt should include:

```text
commit_sha:
test_command:
exit_code:
stdout_summary:
artifact_hashes:
known_limitations:
```

Narrative success is not sufficient.
