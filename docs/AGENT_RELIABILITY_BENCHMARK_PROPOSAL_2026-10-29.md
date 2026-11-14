# Agent Reliability Benchmark — Integration Proposal (2026-10-29)

**Status:** DRAFT / CANDIDATE ONLY. This is an engineering integration proposal, **not evidence of runtime qualification**.

## Why

The portfolio already contains authorization verification, replay controls, Chronicle-style history, provenance, and local tests. Its public presentation would benefit from a concise, reproducible, adversarial benchmark that other engineers can run and critique. This effort is intended to improve engineering visibility without promoting any security, witness, or operational status.

## Local candidate developed

A standalone synthetic Python 3.10+-compatible benchmark package has been prepared outside this repository, with:

- 44 static JSON cases across 11 families, 48 synthetic attempts;
- a **toy reference policy**, a deliberately permissive comparator, and 11 injected policy regressions;
- fixed fixture digests, bounded local hash-chain traces, machine-readable reports, and explicitly missing receipts for simulated evidence outages;
- a candidate GitHub Actions matrix for Python 3.10 and 3.11;
- 18 passing tests on local Python 3.13 (not GitHub CI).

**Observed local toy results:** 44/44 oracle-matching scenarios, 0 synthetic forbidden commits in the reference, 40 in the purposely weak comparator, and detection of 11/11 injected mutations. These figures measure **only synthetic reference behavior**, not the security of WEAVER, ANGELA, Cathedral, ZOREL, or any real model. No real filesystem or network effects were exercised.

## Requirements before this proposal may be merged as a completed benchmark

1. Copy the actual reviewed source, all 44 fixtures, test code, and machine-readable report schema into a dedicated `benchmarks/agent_reliability/` directory.
2. Verify the benchmark scorer never exposes its expected labels to the tested policy adapter, and that malformed inputs fail closed.
3. Complete CI on the exact candidate commit for Python 3.10 and 3.11; retain stdout and result artifacts.
4. Review risk of artificial baselines, fixture leakage, missing witness custody, TOCTOU, and parallel nonce reuse.
5. Keep the canonical `PORTFOLIO_STATUS.md` unchanged until an explicitly authorized, independently evidenced promotion.

## External-runtime upgrade path

Only after the above: implement a separate adapter against one non-destructive WEAVER authorization/execution path. Test actual effect observations, false denials, race conditions, crashes, trace recovery, and external custody. The reference evaluator must **not** be reused as the candidate's enforcement logic.

## Non-negotiable evidence boundary

```text
SIMULATED_PASS != REAL_RUNTIME_PASS
HASH_CHAIN != INDEPENDENT_WITNESS
LOCAL_TEST != INDEPENDENT_REPRODUCTION
DESIGN_PROPOSAL != MERGED_IMPLEMENTATION
CAPABILITY != AUTHORITY
```

The portfolio status remains **E2 / W0 / O0 — HOLD, production prohibited**, in accordance with the canonical status register. Fork provenance and existing qualification holds remain unchanged.

**Disposition:** hold as a draft until the source and tests are committed and independently reviewed.
