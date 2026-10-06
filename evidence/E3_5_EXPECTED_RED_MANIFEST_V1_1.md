# E3.5 expected-red oracle — manifest v1.1

**Status:** EXPECTED ORACLE · NOT AN EXECUTION RECEIPT  
**Date:** 2026-10-06

This file freezes the expected behavior after the manifest-binding repair and before the verifier repair.

## Precondition

The candidate manifest binds the actual local chain head:

```text
e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85
```

and explicitly records that no runtime-derived state digest is qualified.

The legacy verifier still computes the head/state values from pinned constants.

## Expected result

`make verify-e35` is expected to return non-zero.

The failure is desirable because:

```text
ManifestCorrected != VerifierCorrected
PinnedConstant != DerivedRuntimeValue
```

The expected-red run must be archived separately with exact commit, stdout, stderr, exit code, and environment identity before the verifier implementation is changed.

Do not treat this oracle document as evidence that the run occurred.
