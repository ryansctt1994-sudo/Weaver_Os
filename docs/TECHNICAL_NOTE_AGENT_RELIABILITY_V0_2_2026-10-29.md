# WEAVER NEXUS — Technical Note TN-001
## A Deterministic Synthetic Benchmark for Agent Authorization and Evidence Failure

**Date:** 2026-10-29  
**Artifact:** Portable Agent Reliability Benchmark, candidate v0.2  
**Repository:** [Weaver_Os](https://github.com/ryansctt1994-sudo/Weaver_Os)  
**Review:** [Draft PR #93](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/93)  
**Evidence scope:** Offline synthetic reference only — **no tested live agent runtime**.  
**Frozen benchmark-head reference before this note:** `d72737d7fa51704e2af3d222ecc321e4839770c6`

### Abstract

Autonomous agents can propose operations whose apparent correctness does not establish their authorization or their observed effects. This engineering note presents a narrow, reproducible **synthetic reference evaluator** for authorization and evidence-failure handling. It checks whether a toy policy's verdicts match predetermined outcomes across fixed scenario families, whether deliberately broken policy variants are detectable, and whether reports remain deterministic across Python environments.

The experiment is deliberately **not** a demonstration of model capability, actual sandbox containment, system-level security, independent witness custody, or production readiness. Its value is in making a small evaluation harness testable, inspectable, and extendable before attaching any real execution path.

### Research question and hypothesis

**Question:** Can a deterministic evaluation harness expose policy-gate regressions, replay errors, and missing-evidence handling without conflating decisions with real-world execution effects?

**Narrow hypothesis:** A reference policy with exact grant–request binding and fail-closed evidence handling will match a fixed synthetic oracle; targeted defects in the reference gates will produce detectable deviations.

**Not hypothesized here:** That an actual WEAVER/ANGELA/Cathedral/ZOREL agent will behave like the reference; that the reference policy is secure against arbitrary attackers; or that a real execution's side effects can be verified by this harness.

### Artifact and experiment

- **Source:** [portable.py](../benchmarks/agent_reliability/portable.py) — standard-library reference scorer, fixture generator, mutation injection, and JSON report writer.
- **Tests:** [test_portable_agent_eval.py](../tests/test_portable_agent_eval.py).
- **Reproduction instructions:** [benchmark README](../benchmarks/agent_reliability/README.md).
- **CI:** [Python 3.10–3.13 candidate workflow](../.github/workflows/weaver-agent-eval.yml); reports retained as GitHub Actions artifacts.
- **Corpus:** 44 deterministic cases in 11 families, comprising 48 simulated attempts. Families: authorized, wrong principal, wrong action, wrong resource, substituted payload, wrong nonce, expired grant, revoked epoch, replay, invalid MAC, and evidence loss.
- **Decision boundary:** A grant is compared to an attempted operation and a simulated replay/evidence state. A **public test-only HMAC key** protects fixture consistency within the toy example; it has no production authentication meaning.
- **Controls:** (a) the toy guarded reference; (b) an intentionally all-allow comparator, used only as a negative control; (c) 11 deliberate single-gate mutations, including a false-denial mutation.
- **Traces:** A volatile in-process hash chain detects some local modifications while its head remains unchanged; the process also holds the head. No external witness or tamper-resistant custody is claimed.

Case expectations are defined by the scenario generator and are not read by the policy decision function; tests specifically check an expectation-label alteration does not change the authorization decision. However, generator and policy share design assumptions, so an independently specified oracle is still needed for stronger validation.

### Reproduce

From the **source-tree checkout** (Python 3.10+; pytest required for tests):

```bash
python -m benchmarks.agent_reliability.portable --out agent-reliability-report.json
python -m pytest -q tests/test_portable_agent_eval.py
```

The CLI does not invoke a model, access external networks, request privileged execution, or modify a protected target. The benchmark is **not** included in the distributed `weaver-os` wheel.

### Results (synthetic only)

| Measurement | Observed result | Interpretation |
| --- | ---: | --- |
| Reference scenario verdicts matching oracle | 44 / 44 | Agreement with this constructed corpus, **not** general security |
| Simulated forbidden allow decisions, reference | 0 | Synthetic score; **not physical commit observation** |
| Simulated forbidden allow decisions, intentionally all-allow comparator | 40 | Sanity-check negative control; **not representative of real agents** |
| Deliberate regressions detected | 11 / 11 | Detection of these specific injected defects only |
| Evidence-outage attempts without execution receipts | 4 | Missing receipts stay missing, even though the reference halts |
| Local test suite | 16 passing | Python 3.13 local scope |
| CI | 8/8 workflows reported success for the pre-note PR head | CI is not non-origin independent reproduction |
| Actual agent/runtime evaluations | 0 | No live path exercised |
| Admitted independent reproductions | 0 | External validation pending |

For PR head `d72737d7fa51704e2af3d222ecc321e4839770c6`, the GitHub workflows reported success, including the synthetic benchmark's Python 3.10–3.13 matrix. A Python 3.10 report was compared exactly to an originating Python 3.13 report (reported artifact SHA-256: `59841f8206222e65011550406be0cc6319a0b294a12976c4af28e08c3bdf6872`). This is cross-environment determinism **within the authored harness**; it does not demonstrate external review or independent implementation.

### Threats to validity

1. **Synthetic circularity:** Oracle and reference derive from one design; tests may miss shared misconceptions. Regression kill rate is not a security probability.
2. **Unrealistic comparator:** An all-allow baseline makes authorization improvements easy to show. Compare against an established real execution policy before drawing practical conclusions.
3. **No effect observation:** An `allow` decision is not a committed write; a `deny` result is not proof that no side effect occurred.
4. **No custody independence:** Hash chaining without independently controlled head anchoring cannot defeat coordinated history rewrites or truncation.
5. **No adversarial concurrency or recovery:** Races, multi-process replay, crashes, stale data, and time-of-check/time-of-use exposure remain untested.
6. **Toy namespace handling:** String filtering is not safe filesystem canonicalization; path traversal, links, mount behavior, and platform differences require independent checks.
7. **No performance measurement:** No latency, throughput, token usage, false-denial rates on real tasks, or operational costs are established.

### Next experiment: non-destructive real-runtime adapter (proposed, not executed)

Use one fixed, harmless, already reviewed authorization/execution operation in `Weaver_Os`. Keep the **benchmarked policy decision separate** from the evaluator; reuse neither the toy authorizer nor its generated expected verdicts as the implementation under test.

Before running, freeze a commit and test matrix, record host capabilities, establish an independently readable observer channel, choose an effect-safe destination, and set explicit abort rules. Include authorized success, unauthorized principal/action/payload, expired and replayed authorization, concurrent reuse, interruption/restart, unavailable observation, and evidence corruption.

**Minimum admission conditions:** (i) effect observed separately from the executor's own claim; (ii) success and denial each independently checked; (iii) false denial and latency/cost measured; (iv) raw traces, hashes, environment and commands retained; (v) uncertain or unobserved effects classified `UNKNOWN` rather than promoted to `SAFE`; (vi) a non-origin reviewer can reproduce on a supported host. Passing toy benchmarks does **not** waive any of these gates.

### Status and availability

This note describes a **candidate on an open draft PR**, not a merged release. It cannot confer enforcement or production authority. The canonical portfolio ceiling remains **E2 / W0 / O0 — HOLD; production prohibited**. This note does not amend the portfolio registry, ratify architecture changes, imply original authorship of forks, or substitute for an independently witnessed reproduction.

**Engineering principle:** Proposal is not authority. A claimed success is not an independently observed effect.
