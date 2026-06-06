# P12 Gate: Self-Falsification

`P12_GATE_SELF_FALSIFICATION`

A protective mechanism that has never been observed failing correctly remains a hypothesis, not a verified safeguard.

## Purpose

The P12 gate prevents ceremonial safety claims. A safeguard is not treated as verified merely because it exists, is documented, or succeeds on compliant inputs.

A safeguard must demonstrate correct refusal, rejection, downgrade, or abort behavior under an intentionally invalid or adversarial condition.

## Minimum Verification Standard

A safeguard may be promoted only after evidence shows:

1. The invalid condition was deliberately constructed.
2. The safeguard detected the condition.
3. The safeguard failed closed.
4. The failure was recorded as a receipt-bearing event.
5. Replay reproduces the same admissibility result under the declared policy version.

## Evidence Status

Until the above exists, the mechanism must be labeled `HYPOTHESIS` or `REPORTED`, not `VERIFIED-REPO`.

## Non-Claim

P12 does not prove a safeguard is complete. It proves only that the safeguard has at least one observed correct-failure path and is no longer purely ceremonial.
