# JSON numeric overflow repair — review candidate

Base: PR #91, `df2934f344119a4d7d971eafcb81a16b65918c43`.

Both strict intake functions rejected NaN/Infinity literals through
`parse_constant`, but Python parses valid JSON exponent tokens such as `1e999`
as floating-point infinity without calling that hook. The functions therefore
returned nonfinite values despite their declared intake contract. This finding
is an intake defect, not evidence that a complete production authorization was
bypassed.

Each verifier now independently supplies a finite-checking `parse_float` hook.
Finite floats and arbitrary-precision integers retain the prior behavior.
The byte verifier remains independent of the evidence producer.

Local Python 3.12 validation on 2026-10-09:

- New tests against base: **6 failed, 1 passed**.
- Focused intake/bundle/integration suite: **37 passed**.
- Full repository suite: **283 passed**.
- Repository Ruff: PASS.
- Real E3.5 hold checker: positive local-spine control and expected withheld
  control both passed the semantic classification.

Reproduce with `python -m pytest -q tests/test_json_numeric_overflow.py`.
Run the new test file against the exact base to reproduce RED.

These are assistant-managed local results; hosted CI must be inspected at the
published head separately. No historical manifest, ledger, signed release,
policy identity, authority, or witness state changed. E2 / W0 / O0 WITHHELD /
PRODUCTION PROHIBITED / E4 NOT EARNED. This is a repair of the existing candidate,
not a merge or release. It does not impose a new number precision/range profile,
handle general resource exhaustion, or authenticate input origin.
