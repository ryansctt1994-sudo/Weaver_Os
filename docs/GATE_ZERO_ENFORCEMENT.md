# Gate Zero — Repository Enforcement Handoff

**Audit date:** 2026-10-07  
**State:** readiness specification; server enforcement not established

> CODEOWNERS metadata, CI files, and written policy are not branch protection.
> Gate Zero is only enforced when the GitHub repository settings actually reject
> non-conforming writes and merges.

## Current flagship audit

| Repository | Default branch protected | CODEOWNERS on main | Candidate ownership PR |
| --- | --- | --- | --- |
| `Weaver_Os` | **NO** | yes | n/a |
| `Lumen-Nexus` | **NO** | yes | n/a |
| `cathedral-verified` | **NO** | no | draft PR #8 |
| `introspection-twin` | **NO** | no | draft PR #3 |
| `Alpha-OmegaLeanTeam` | **NO** | no | draft PR #23 |
| `Weaver-Governed-RSI` | **NO** | no | draft PR #7 |

The candidate PRs add metadata only. Until they are merged, the default branches
remain without those CODEOWNERS files. Even after merge, enforcement still requires
repository settings.

## Phase A — solo-safe enforcement

Use this when there is not yet a second trusted reviewer who can approve every
governance-sensitive change.

For the default branch:

1. require changes through a pull request;
2. require the repository's named status checks;
3. require the branch to be up to date before merge;
4. require all review conversations to be resolved;
5. require linear history;
6. block force pushes;
7. block branch deletion;
8. apply the rules to administrators / bypass actors where the repository plan supports it;
9. keep required approving reviews at **0** if requiring one would make a solo-owned
   repository impossible to merge lawfully.

This creates a server-side CI/PR gate without inventing an unavailable independent reviewer.

## Phase B — dual-control enforcement

Promote to this phase only after a second trusted reviewer has real repository permission
and is operationally available.

Add:

1. at least **1 approving review**;
2. require CODEOWNERS review for sensitive paths;
3. dismiss stale approvals after new commits;
4. require approval after the most recent push;
5. restrict bypass to an explicitly governed break-glass path, if any;
6. record reviewer identity and exact merged revision in the evidence receipt.

A single owner approving their own work is not independent witness evidence.

## Required-check rule

Do not hard-code a check name merely because it once appeared green. First list the
checks emitted by the default branch and active candidate workflows, then bind the
ruleset to stable, unambiguous job names.

A required check must:

- execute the intended test or verifier, not merely invoke a script path;
- fail closed when the test command is missing, skipped, or piped through a masking command;
- be bound to the exact revision GitHub merges;
- not share a generic name with unrelated jobs if that can satisfy the wrong requirement.

## Evidence boundary

```text
CODEOWNERS_PRESENT != CODEOWNER_REVIEW_ENFORCED
PR_OPEN != PR_ADMISSIBLE
CI_GREEN != INDEPENDENT_REPRODUCTION
BRANCH_PROTECTED != PRODUCTION_AUTHORITY
GATE_ZERO_ENFORCED != E4_EARNED
```

Turning on these controls is a governance improvement. It does not change the portfolio
state by itself:

```text
E2 | W0 | O0 WITHHELD | PRODUCTION PROHIBITED | E4 NOT EARNED
```
