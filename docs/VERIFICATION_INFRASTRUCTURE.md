# Verification infrastructure

Use Python 3.12 and a clean checkout of the exact commit under review:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-verification.lock
make verify
```

`make verify` requires the test suite, verified signed witness archive execution,
and all six verifier mutations to pass. It retains logs and a strict JSON report
in `verification-output/`. Missing executables, timeouts, and nonzero exit codes
fail. The report records the commit, dirty flag, source/artifact hashes, Python
and platform, commands, and log hashes. This is local execution evidence; it is
not an independent attestation or an authority grant.

The witness is the implemented runtime in the signed RC1 archive, not the TODO
root `kernel/`, `chronicle/`, or `receipt/` modules. Existing witness checks cover
fresh-process replay, rejected-command state preservation, single-use commands,
and receipt/Chronicle tampering. New static fixtures exercise the signed Triad
ledger CLI and report schema. Synthetic report fixtures are not real receipts.

The new verification workflow also builds without dependency re-resolution and
installs the wheel into a separate virtual environment, then tests ledger/schema
loading with isolated Python outside the checkout. Its workflow conclusion,
build log, and wheel log must be checked alongside report.json: the report's PASS
covers only its three named local checks. Evidence uploads run even after failure.
The lock pins exact versions, but does not pin package distribution hashes or the
OS image digest; it is not a claim of bit-for-bit hermetic reproduction.

The TLC workflow separately verifies the SHA-256 of the official versioned
TLC 1.7.4 JAR and records bounded-model output. A model check is not proof that
Python implements the specification. Deadlock checking remains disabled as in
the original workflow; the configured invariants are checked.

The packaged Triad event schema mirrors the root schema; a test prevents drift.
Public deterministic fixture keys must never be trusted for production signing.
For an independent reproduction, a separate operator must obtain the source,
archive trust pin and expected ledger head through a trusted channel, run these
checks in their environment, and return the report and all referenced logs.
Neither a successful CI run nor a fresh process establishes operator independence.

This change does not promote the legacy audit diagnostic scripts into acceptance
gates or claim implementation of the placeholder runtime modules.
