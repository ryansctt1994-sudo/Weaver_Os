# Weaver witness archive verification

The frozen RC1 archive is checked by `tools/verify_witness_archive.py` before extraction. The checker requires an expected Ed25519 public-key SHA-256 fingerprint and verifies the signature, exact ZIP file set, file hashes, and archive path safety. CI pins fingerprint `5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9` and then runs the extracted witness.

```sh
python tools/verify_witness_archive.py \
  releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip \
  --expected-key-sha256 5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9
```

The pinned fingerprint prevents an archive replacement that includes a newly generated key and matching signature from passing this check. A reviewer seeking publisher authentication must obtain the fingerprint from an independently trusted channel; the repository and its CI are controlled by the same publisher. Neither this check nor a passing CI run is an independent operator receipt. The witnessed claim remains the narrow constructed command scenario described in the RC1 README.
