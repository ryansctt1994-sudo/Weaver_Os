# Portable Agent Reliability Benchmark (candidate v0.2)

**Scope: OFFLINE SYNTHETIC REFERENCE ONLY.** This is an original, dependency-free Python reference evaluator and regression harness. It does **not** test or establish the reliability, security, efficiency, or deployment readiness of any actual LLM, ANGELA, Cathedral, ZOREL, or WEAVER runtime.

## Reproduce from the repository root

Requires Python 3.10+:

```bash
python -m benchmarks.agent_reliability.portable --out benchmark-report.json
python -m pytest -q tests/test_portable_agent_eval.py
```

The benchmark CLI uses only the standard library. Tests need pytest. No external credentials, network calls, privileged users, or effectful target filesystem access are needed. This is intentionally a **source-tree** benchmark, not part of the packaged \`weaver-os\` wheel.

## Test design

- 11 scenario families, four deterministically generated variations per family (44 cases; 48 attempts):
  authorized, wrong principal, wrong action, wrong resource, payload substitution, nonce binding, expiry, revocation epoch, replay, invalid test MAC, and evidence unavailability.
- Each generated grant is bound to a request using a **public test-only HMAC key**; it has no production security meaning.
- The oracle is the case's expected verdict array; the toy decision function does not read expected labels. Action attempt count is specified independently in \`attempts\`.
- 11 injected mutations disable individual gates or deny legitimate requests. A mutation is detected only if its results disagree with at least one oracle case.
- The deliberately permissive \`unguarded\` comparator always allows. It is a synthetic negative control, **not a representative agent baseline**.
- Each case receives a fresh simulated nonce store and volatile in-memory hash chain. The trace's head is held by the same process, so an attacker who can rewrite both log and head defeats the check.
- Missing simulated evidence causes the governed reference to halt, but **no execution receipt** is invented. The report counts those attempts as unreceipted.

## Local results (2026-10-29, Python 3.13)

| Measurement | Observation |
|---|---:|
| Unit tests | 16 passing |
| Reference scenarios matching oracle | 44 / 44 |
| Synthetic forbidden commits, reference | 0 |
| Synthetic forbidden commits, purposely permissive comparator | 40 |
| Injected mutations detected | 11 / 11 |
| Missing synthetic execution receipts in outage fixtures | 4 |
| Real runtime evaluations | 0 |
| Non-origin reproductions | 0 |

These are reference-model tests with a fixed, contrived corpus. They are not independent reproductions, system validation, security certification, proof of safety, or real-world efficacy metrics.

## Current exclusions and threats to validity

No actual agent, observed action effects, concurrency races, persistent replay database, crash recovery, real signing-key custody, OS namespace isolation, hardware latch, external witness, formal proof of all behaviors, latency or cost measurement. The noncanonical-path check is a **toy string filter**, not a secure path canonicalization mechanism for real filesystems. A real adapter must use an independently specified authorization contract and independently observe post-action effects.

## Next gate before any claim beyond synthetic reference

Implement a separate, non-destructive adapter against one fixed real \`Weaver_Os\` authorization/execution path, with exact recorded source revision, external effect witness, concurrency and crash injection. Do not reuse the reference decision function as the test subject.

**Governance status unchanged:** portfolio E2 ceiling / W0 / O0 — HOLD; production prohibited. This candidate stays in a draft PR pending code review and exact-commit CI evidence.
