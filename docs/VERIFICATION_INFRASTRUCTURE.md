# Verification infrastructure

The canonical acceptance entry point is:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-verification.lock
make verify
```

`make verify` is now the complete fail-closed gate. It runs exactly six required
verifiers and emits one aggregate `verification-output/verification-report.json`:

1. `unit_and_integration`
2. `bound_witness`
3. `mutation_suite`
4. `adversarial_corpus`
5. `installed_wheel`
6. `formal_tlc`

A required verifier cannot be skipped, unavailable, or missing and still produce
PASS. Missing executables, timeouts, failed downloads, digest mismatches, missing
artifacts, failed wheel installation, and nonzero exit codes are recorded as FAIL.
The overall verdict is derived mechanically from the complete required verifier
set, the structured adversarial results, and the built-wheel digest.

The report binds the result to the source-head SHA, the commit actually checked
out and verified, the base SHA, dependency-lock digest, wheel digest, environment,
GitHub run identity when present, exact verifier commands and exit codes, evidence
log hashes, source/artifact hashes, and the evidence-manifest digest. On pull
requests the source-head SHA and verified merge SHA are intentionally distinct.

## Adversarial evidence

`verification-output/adversarial-results.json` records one attributable result for
each currently implemented required adversarial case:

- `ADV-001` byte tamper
- `ADV-002` ledger truncation
- `ADV-003` key substitution
- `ADV-004` empty ledger
- `ADV-005` duplicate JSON key
- `ADV-006` malformed receipt

The runner also requires the frozen valid-ledger baseline to verify successfully.
The corpus is intentionally limited to cases that really execute; future cases
must be added to the corpus, report schema, and closure predicate together.

## Installed-wheel boundary

The wheel verifier deletes prior build output, builds exactly one wheel without
dependency re-resolution, creates a separate virtual environment, installs the
locked dependencies and wheel, and runs the smoke verifier from a temporary
directory outside the repository checkout. The report records the resulting
wheel SHA-256.

## Formal boundary

The aggregate gate downloads the official TLC 1.7.4 JAR, verifies its pinned
SHA-256 before execution, and runs the configured bounded invariants. A missing
Java runtime, download failure, hash mismatch, timeout, or model-check failure is
a verification failure. The separate `Witness TLA model` workflow may remain as
redundant CI evidence, but the aggregate report no longer depends on manually
combining that workflow with another PASS.

A bounded TLA+ model check is not proof that Python implements the specification.

## Deferred source-tree modules

`chronicle`, `kernel`, and `receipt` now expose an explicit
`DEFERRED_TO_BOUND_WITNESS` status and fail loudly if an implementation symbol is
requested. They are not silently presented as completed runtime code. The current
behavioral claim remains bound to:

`releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip`

This PR does not claim a local implementation of those modules.

## Claim boundary

A successful report is reproducible local/CI evidence, not an independent
attestation, authority grant, production authorization, or bit-for-bit hermetic
build claim. The dependency lock pins versions but not distribution hashes, and
the Ubuntu runner image is not digest-pinned.

Independent E4 reproduction still requires a separate operator/environment to
obtain the trust pins through an appropriate channel, run the canonical gate, and
return the report plus referenced evidence.
