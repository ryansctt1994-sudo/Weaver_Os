# Cathedral Kernel Status

Version: 1.0.0-rc1

STATUS: RELEASE_CANDIDATE

MATURITY: P5 Release Candidate — DSSE / Observability-Projected Governance Kernel

## Current Evidence

- Python unit test suite passed in the build environment.
- CLI version command passed.
- CLI demo emitted the expected governance receipt path.
- TLC execution attempt was recorded, but TLC was unavailable in the build environment.
- Hardware artifacts were included in the generated package but not physically verified.

## Validation Summary

```text
86 unit tests passed
python -m cathedral.cli version → 1.0.0-rc1
python -m cathedral.cli demo → completed with expected receipt
```

## Release-Candidate Goal

Stabilize the public API, CLI, receipt formats, and claim-boundary documentation without expanding authority claims beyond evidence.

## Release Artifact

```text
cathedral-kernel-v1.0-rc1.zip
sha256: 5d283548cea999c18be699672a884a05c1b0c2a8cf4c101d01b0c31097f1e2ed
```
