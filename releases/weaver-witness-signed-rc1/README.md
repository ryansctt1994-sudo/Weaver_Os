# Weaver witness reproduction candidate 1

Claim: this small Python implementation rejects an unauthorized command without changing protected state, reconstructs an authorized result in a fresh process, and detects the included receipt/Chronicle mutations. This packet is a local implementation witness, not an independent reproduction or a production security assessment.

Source: `WEAVER_NEXUS_CONSOLIDATED_RC1.zip`, saved 2026-09-29, `weaver/witness_packet/`. The three Python files are copied byte for byte. The package signature is self-issued by this packaging run. The public key is shipped here for integrity checking, but authenticity requires comparing its fingerprint with a value obtained independently from the owner. A bundled key alone cannot establish publisher identity.

Requirements: Python 3.10+ for the witness; `cryptography` for signature verification. Extract in a fresh directory and run:

```sh
python tools/verify_release.py
cd src && python witness.py
```

The verifier checks an Ed25519 signature over the exact `MANIFEST.json` bytes and SHA-256 hashes of the listed files. It rejects missing or extra regular files (excluding Python bytecode caches). Run verification before the witness. Capture both commands, exit codes, Python/OS versions, archive SHA-256, and public key fingerprint in `OPERATOR_RECEIPT_TEMPLATE.md`. Publish the receipt separately, signed with the independent operator's own key if available. A third party should obtain the archive and trusted fingerprint through separate channels.

The witness uses constructed commands and expected outcomes. Its nine checks are not evidence that other tools, deployments, or real-world actions follow this policy. The previously reported three-tool policy suite is not included because its source and terminal transcript were not present in this RC1 source packet.
