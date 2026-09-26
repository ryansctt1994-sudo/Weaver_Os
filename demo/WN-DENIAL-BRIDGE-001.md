# WN-DENIAL-BRIDGE-001 — bounded denial correspondence probe

Source: `demo/denial_bridge.py`; tests: `tests/test_denial_bridge.py`. This is a candidate relation between the abstract denial theorem in [Lean draft PR #39](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/39) and the local WN-E2E-001 fixture. It is **not** a Lean/Python refinement proof.

`project` checks the exact protected-state schema (`authority`, `artifact`, `revision`) and records its complete value in a `ModelState`-shaped object. Its `executed` field is used as an opaque observation of Python state; it does **not** equate a Python artifact commit with a Lean `execute` event. The actual Lean state instead has lists of grants, receipts, and executed bindings. Fixture receipts and Chronicle audit records are outside this protected-state projection.

For a runtime `REJECT` result, `check_denied_projection` compares the **actual Python state value** before and after, as well as the candidate model's identity step. It raises if any protected field changes, if the input mutates, or if the schema differs. The injection test deliberately mutates `revision` after a rejection and verifies that the bridge catches it. The replay test checks `fold(s, xs ++ ys) = fold(fold(s, xs), ys)` for all split points of one frozen accept/reject transaction sequence; it does not prove that identity for arbitrary transactions.

Run `pytest -q tests/test_denial_bridge.py` from the repository root. The existing pytest CI job executes this file on Python 3.10–3.12 after it is targeted by a main-based PR. The new draft branch is stacked on PR #40, which in turn depends on PR #38.

## Open proof obligations

1. Define a semantics-preserving mapping from Python's transaction and validator results to Lean's `Context`, `Receipt`, `Grant`, and `Event`. Presently WN-E2E-001 does not issue grants and its evidence checks are fixture presence checks.
2. Show that all runtime rejection paths preserve the protected state, including exceptions and malformed inputs, rather than the tested subset.
3. Prove the reducer correspondence under a typed set of admissible transactions. The current replay equality is a finite test.
4. State an independent audit of source and check results. No external reproduction or production authority follows from this bridge.
