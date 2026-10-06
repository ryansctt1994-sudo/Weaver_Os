# Promotion Rules

Weaver OS separates implementation from authority.

## Non-Negotiable Boundary

```text
architecture != authority
specification != implementation
declared_success != replay_verified_success
capability != authorization
candidate_pr_state != canonical_main_state
declared_governance != server_enforced_governance
```

## Promotion Requirements

A component may only be promoted when it has:

1. passing automated tests,
2. reproducible local execution instructions,
3. explicit evidence of expected behavior,
4. no failing security or schema checks,
5. a receipt or release note identifying the commit, test command, and result.

Open or draft pull requests remain candidate state. A green pull request can support merge review, but it does not become canonical portfolio state until it is merged to the canonical branch.

## Gate Zero

Repository governance expectations are declared in `governance/gate-zero.json` and checked by `tools/check_gate_zero.py`.

That check validates the repository's declaration and required files. It does not configure or prove GitHub server-side branch protection.

Server-side Gate Zero is expected to enforce:

1. pull-request-only changes to `main`,
2. blocked force pushes,
3. blocked branch deletion,
4. linear history,
5. required status checks before merge.

Until those settings are independently inspected on GitHub, the correct status is:

```text
GATE_ZERO_DECLARED
SERVER_ENFORCEMENT_NOT_PROVEN
```

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
