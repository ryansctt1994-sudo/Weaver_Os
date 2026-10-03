# WNS Security Adversarial Closure v0.1

A bounded execution-boundary research harness, not a production security service.

The trusted setup provisions a root and leaf grant. The trusted approval adapter stores a random approval token bound to the complete request digest (actor, action, resource, amount, nonce). The trusted authentication adapter supplies the principal. Agent/retrieved content cannot invoke setup or approval through the actuator. All ancestor grants are checked against the current database on each execution.

One SQLite transaction serializes policy evaluation, the counter effect, approval consumption and the outcome receipt. Pre-commit exception injection rolls all of them back. A post-commit exception leaves one effect and a consumed approval; retry rejects. These are injected exceptions and connection reopenings, not process-kill or power-loss tests. A concurrency test requires one acceptance and one effect for four concurrent submissions of the same approval.

## Reproduce

From the repository root:

```sh
python -m pytest tests/test_security_closure.py -q
python -m security_closure.run
python -m security_closure.mutations
```

The frozen JSON corpus contains eleven scenarios. The runner records expected/observed verdicts, exact resource snapshots, and the final database receipt. It fails on verdict mismatch, an effect on rejection, a missing/mismatched receipt, or incorrect crash recovery. Seven in-memory source mutations disable identity, request binding, approval replay, lineage, ancestor revocation, action scope or transaction atomicity. Every mutant must be detected by its designated attack. Mutants never modify the production source.

## Boundaries

The actuator is a SQLite counter, not an arbitrary tool dispatcher. Approval tokens are trusted-store bearer objects, not signed human intent. Authentication, human approval, root provisioning, clock integrity, database integrity, and protection of the host are assumed. The nonce is digest-bound; replay prevention applies to the approval token, not global nonce reuse across separately issued approvals. The grant model has one root path and one resource; it does not implement the full Lean bounded-delegation schema.

The poisoned-memory case is a synthetic authority-claim substitution. It establishes rejection by this boundary, not resilience of an LLM/retriever to natural-language injection. Receipts are local database audit records, not cryptographically sealed or independently witnessed records. External effects require an idempotent actuator/reconciliation protocol; the SQLite transaction alone cannot make them atomic. Cross-tenant memory, dependency compromise, OS isolation, receipt tampering, abrupt process termination and recovery from damaged storage remain outside this slice. No implementation-refinement theorem connects this harness to the Lean model.

CI retains corpus outcomes, mutation outcomes and SHA-256 digests of the corpus and harness files. Independent reproduction and a signed outside outcome remain outstanding.
