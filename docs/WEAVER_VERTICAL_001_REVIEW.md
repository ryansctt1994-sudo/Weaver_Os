# WEAVER-VERTICAL-001 — Review-only SQLite protected-write candidate

**Base:** `7f839efad8c273b979678b0f94e5b1175136b0ab`
**Status:** DRAFT / DO NOT MERGE / HOLD
**Evidence:** Local/hosted tests only; **E2 ceiling, W0, O0_WITHHELD**; production prohibited.

## Purpose

Make one effect (`WRITE_KEY`) occur in the **same SQLite transaction** as
`EXECUTION_COMMITTED` on the Authority Root. The owner uses the existing
`ExecutionGate`, `ReceiptLedger`, canonical proposal contract, and read-only
ledger verifier. It pins a trusted Ed25519 public key at construction, checks a
domain-separated issuer-signed grant for the exact canonical proposal SHA-256,
audience, issuance interval, and grant identifier, and applies a fixed
allowlisted-key mutation inside the ledger's `BEGIN IMMEDIATE` transaction.

Requests are proposals + signed grants; neither can provide their own callback,
verifier trust root, effect handler or receipt through `submit()`.

The gate's optional `atomic_effect` constructor hook is for **trusted owner
composition only**; the caller cannot supply it through `execute()`. It runs
inside the ledger `admit` transaction, after the serialized veto/revocation
control guard, before receipt insertion. An exception rolls back both effect
and event. The legacy gate default is unchanged.

## Important: this is not full containment

**HOLD V008:** The owner currently lives in the same process/security principal
as a possible caller. A same-UID process can open the SQLite file directly.
The test is an explicit XFAIL counterexample, NOT an isolation pass. To close
V008, run the owner as a separately privileged process that alone owns the DB,
with a minimal authenticated IPC boundary and denied direct requester FS access;
then replace the XFAIL with a real negative-control test on a capable host.

**HOLD V012:** Kill-after-commit/acknowledgment-loss requires a subprocess crash
injector at the exact commit boundary. Normal restart testing does not prove
this. It is an explicit XFAIL until performed and receipted.

**HOLD mutation requirement:** The design decision requires three mutation
kills (bypassed gate, substituted verifier, bypassed effect); the current suite
contains direct negative cases but not a separately recorded mutant campaign.
The review gate remains HOLD until all are exercised and produce expected red.

**Other boundaries:** The trust root is constructor-injected; an untrusted
application caller able to instantiate an owner or replace its key defeats
the boundary. SQLite-file access/backup and WAL corruption are out of scope.
Ledger controls are NOT part of the verified hash chain. The in-memory veto is
not a physical interlock. Current replay verifies internal hashes and compares
derived effects to observed rows; without an **externally retained** anchor,
forward-recomputed history and truncation can remain undetectable.
Neither Ed25519 signatures nor SHA-256 receipts prove issuer legitimacy
without a separately governed trust anchor. No real-world effects are allowed.

## Cases

| ID | Target | Status until hosted run / external controls |
| --- | --- | --- |
| V001 | Signed exact-scope write, matching receipt | Test candidate |
| V002 | No grant denied with receipt | Test candidate |
| V003 | Untrusted signing key refused | Test candidate |
| V004 | Wrong audience, target key or operation refused | Test candidate |
| V005 | Expired / future grant refused | Test candidate |
| V006 | Pre-commit revocation serialized and blocks write | Test candidate |
| V007 | Proposal substitution rejected | Test candidate |
| V008 | Separate OS-identity bypass refused | **HOLD / XFAIL** |
| V009 | Duplicate proposal idempotent | Test candidate |
| V010 | Same-ID concurrent submissions | Test candidate |
| V011 | Pre-commit injected failure rolls back | Partial: exception, not SIGKILL |
| V012 | Kill after commit, replay after lost ACK | **HOLD / XFAIL** |
| V013 | Fresh-process read-only replay reconstructs state | Test candidate |
| V014 | Tamper and anchor mismatch rejected | Test candidate; external anchor HOLD |
| V015 | Recorded veto before commit blocks write | Test candidate |
| V016 | Ledger insert error rolls back resource effect | Test candidate |

## Reviewer instructions

1. Do **not merge** until all 16 IDs pass on a qualified host, not merely pytest green.
2. Compare PR to the exact base; inspect receipt/event digests and resource DB bytes.
3. Run `pytest -q tests/vertical/test_protected_write.py`, then `pytest -q`.
4. Run `ruff check .`, `mypy ...`, the trust-boundary checker, and wheel build.
5. Add OS isolation, crash injection and named negative-control mutants before
   considering the protected-write claim closed.
6. Carry E2 / W0 / O0; separate owner decision for merge or promotion.

This review branch does not change prior sealed receipts, historical audit
evidence, or any other repository.
