# Weaver witness archive verification

The frozen RC1 archive is checked by `tools/verify_witness_archive.py` before extraction. The checker requires an expected Ed25519 public-key SHA-256 fingerprint and verifies the signature, exact ZIP file set, file hashes, and archive path safety. CI pins fingerprint `5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9` and then runs the extracted witness.

```sh
python tools/verify_witness_archive.py \
  releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip \
  --expected-key-sha256 5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9
```

The pinned fingerprint prevents an archive replacement that includes a newly generated key and matching signature from passing this check. A reviewer seeking publisher authentication must obtain the fingerprint from an independently trusted channel; the repository and its CI are controlled by the same publisher. Neither this check nor a passing CI run is an independent operator receipt. The witnessed claim remains the narrow constructed command scenario described in the RC1 README.

The verifier reads the archive once and parses, verifies, and hashes that byte snapshot. Tests cover replacement at capture and replacement after capture. Its result describes the captured archive, not later contents at the same path. Extraction and execution performed afterwards must use that verified artifact; this read-only verifier does not make a separate extraction step atomic.

For execution, use the bound runner from the repository root:

```sh
python -m tools.run_verified_witness \
  releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip \
  --expected-key-sha256 5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9
```

The runner captures the archive once, verifies that snapshot, extracts those same bytes into a new temporary directory, and launches its witness. It reports the verified archive/manifest/key hashes, child exit code, stdout, stderr, and timeout status as JSON. Nonzero child exits and timeouts cause a nonzero runner exit. Temporary files are removed after execution. This binds archive bytes to extraction; it does not sandbox the signed program or establish operator independence. CI now uses this runner instead of reopening the ZIP for a separate extraction.

Run `python -m tools.check_verifier_mutations` to check six targeted removals: archive key pin, archive signature, archive payload hashes, ledger key pin, ledger head pin, and ledger chain integrity. The checker requires a passing unmodified baseline, makes each mutation in a separate temporary copy, and requires the relevant adversarial test to fail. A collection error or surviving mutant fails the checker. These six checks measure the selected verification gates, not exhaustive mutation coverage.
