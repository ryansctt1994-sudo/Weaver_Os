# Receipts

Receipts are replay evidence, not narrative status notes.

A Chronicle comment may record that an artifact exists or that a test should be
run.  It does not promote an artifact to a higher evidence class.  Promotion
requires preserved command output, hashes, CI logs, or equivalent replayable
material.

## MVP-0 Cathedral Core receipt target

The first planned Cathedral Core receipt is:

```text
receipts/mvp0_cathedral_core_tests_001.txt
```

Generate it locally with:

```bash
python -m pytest tests/cathedral_core -v 2>&1 | tee receipts/mvp0_cathedral_core_tests_001.txt

sha256sum \
  cathedral_core/lumen/authority_fsm.py \
  cathedral_core/lumen/scope_sovereignty.py \
  cathedral_core/witness/qgs.py \
  cathedral_core/witness/governance_debt.py \
  cathedral_core/witness/receipt.py \
  cathedral_core/constitution_loader.py \
  constitution/negative_invariants.yaml \
  >> receipts/mvp0_cathedral_core_tests_001.txt
```

If the test output shows all Cathedral Core tests passing, the tested MVP-0
artifacts may be promoted from `E2_IMPLEMENTED` to `E3_RECEIPTED` for the exact
behavior covered by those tests.

No mechanism may silently convert uncertainty into authority.
