# Witness policy freeze withheld

**Status:** discrepancy recorded, not adjudicated.
**Authorization:** E2 / W0 / O0 WITHHELD / PRODUCTION PROHIBITED.

Four declared identities are present and are not the same policy:

| Identity | Source | Declared status |
| --- | --- | --- |
| `e35-reproduction-kit-spec` | `E3.5_REPRODUCTION_KIT_SPEC.md` | Specification; implementation incomplete |
| `portfolio-e4-pending-witnessed-seal` | `PORTFOLIO_EVIDENCE_STATUS.md` | E4 not earned |
| `mathos-e4-runnable-computational-support` | MathOS claim-set key | Different ladder: runnable computational support |
| `rc1-three-tool-policy-suite-absent` | Witness RC1 README | Previously reported three-tool policy suite absent |

`tools/witness_policy_freeze.py` emits that record and sets `governing_policy` to null. `--freeze` exits 1. This does not decide which document governs, and it does not promote E3.5 or E4.

```bash
python -m tools.witness_policy_freeze
python -m tools.witness_policy_freeze --freeze
```
