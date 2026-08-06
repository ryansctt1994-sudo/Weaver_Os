# Weaver OS Evidence Registry

Status: PRE-PRODUCTION
Evidence ceiling: L3 until independent replay.

## Evidence Labels

| Label | Definition |
|---|---|
| VERIFIED-HERE | Executed or replayed in the originating review session. |
| REPORTED | Claimed from repository or prior report; not re-executed in the review session. |
| DRAFTED | Designed or written; not replay-confirmed. |
| ROADMAP | Future layer; not yet built. |
| CONCEPTUAL | Organizing principle; no implementation claimed. |

## Maturity Levels

| Level | Meaning |
|---|---|
| L0 | Concept |
| L1 | Drafted |
| L2 | Executable |
| L3 | Tested in session or CI |
| L4 | Independently replay verified |
| L5 | Production observed |

## Current Public Repository Nucleus

| Area | Artifacts | Evidence | Maturity Ceiling |
|---|---|---|---|
| Crypto verifier | `triadic_controls/crypto/verifier.py`, schemas, tests | REPORTED | L3 pending current CI receipt |
| Replay protection | `triadic_controls/crypto/replay.py` | REPORTED | L3 pending current CI receipt |
| Release guard | `src/weaver_release_guard/` | REPORTED | L3 pending current CI receipt |
| Repository README | `README.md` | REPORTED | L1 documentation |

## Handoff Candidate Nucleus

| Area | Artifacts | Evidence | Notes |
|---|---|---|---|
| Public Value Ledger | `pvl/` reducer, schema, tests | DRAFTED until present in repo and CI-run | Must not be upgraded without green tests. |
| Docs CI / perf claims | `docs-ci/` lint, receipts, workflow, tests | DRAFTED until present in repo and CI-run | No unbacked performance claims. |
| MVP-0 replay | Proposal -> Gate -> Chronicle -> Receipt -> Replay -> negative test | ROADMAP | Next authority upgrade target. |
| Governance debt | deferred queue and debt schemas | DRAFTED | Requires tests and receipt lifecycle. |
| Outcome intelligence | `outcome/` | DRAFTED | Must remain advisory until PVL-attested. |
| Frontier signal stack | `frontier/`, signal schemas | DRAFTED | Signals are not authority. |
| Formal verification | Lean, TLA+, Z3 files | DRAFTED | Needs proof/model-check receipts. |
| Hardware sovereignty | RTL files | DRAFTED | Needs synthesis, simulation, and fault-injection receipts. |
| UI / explainability | `ui/`, dashboards | CONCEPTUAL / AW0 | Must not wire to execution path. |
| Research / mythos | `research/`, symbolic archives | CONCEPTUAL / AW0 | Archive only; not semantics. |

## Promotion Rules

- REPORTED -> VERIFIED requires local execution and receipt capture.
- L3 -> L4 requires independent replay outside the originating environment.
- Any production-readiness claim requires L4 plus L5 operational observation.
- Mythic, symbolic, or UI artifacts cannot promote above Authority Weight 0 unless rewritten as neutral operational specs and independently verified.

## Current Verdict

Weaver OS is a pre-production verification and replay substrate. It has a public cryptographic/release-governance spine, but the broader Cathedral Mesh remains evidence-dependent. The next legitimate authority upgrade is MVP-0 replay.
