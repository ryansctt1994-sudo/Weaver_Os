# CLAIMS split — review-only source custody

**From combined reference:** `f65fa54c56341a8d5508af728fc773055afa1cd2` (PR #135).  **Base:** `de15972b4fc29ec0a21f521ccf641946270ffcbf` (PR #134). **Source files copied by exact Git blob SHA.**

**Limit:** Claim inspection only: bounded file reads, symlinked-path refusal, declaration/waiver reports, legacy JCS profile. Never execution authorization.

This branch intentionally omits unrelated combined integration assets and eight donor ZIPs. Licenses and original donor revisions are retained in the upstream source manifest of PR #135; source-file attribution is shown below. No independent witness is established.

## Selected files and source metadata

| Path | Donor/source revision | Expected SHA-256 (or integration identity) |
| --- | --- | --- |
| `tests/consolidation/__init__.py` | #135 integration-only | Git blob pinned to `f65fa54c5634` |
| `tests/consolidation/test_claim_audit.py` | `912a388d47a9` | `958b1000d857895fc0eea033bfec566413e26dff11baf7a14c70f7116c076df8` |
| `tools/claim_audit/__init__.py` | #135 integration-only | Git blob pinned to `f65fa54c5634` |
| `tools/claim_audit/__main__.py` | #135 integration-only | Git blob pinned to `f65fa54c5634` |
| `tools/claim_audit/claim_audit.py` | `912a388d47a9` | `8cd7978d52c4898217909ea957657a780b3b16765bc9bc1b48353c8aad103ac6` |
| `tools/claim_audit/inputs.schema.json` | `912a388d47a9` | `b7362780ac6469d94452c24743ad2573a18af9412578b5656bea2e3efcc7b6eb` |
| `tools/claim_audit/legacy_canonical.py` | `912a388d47a9` | `3fb7284fc62dd15adef50277beb7b439b57c87b5598dca09a18a293d74d106ce` |
| `tools/claim_audit/manifest.json` | `912a388d47a9` | `c0e109aa4042ed39e5248476b977b6131e0177fc3e3b1379bbf545d94d800b6b` |
| `tools/claim_audit/outputs.schema.json` | `912a388d47a9` | `81a541aa23a632730d97fa4f1ff0a392784ba47eca100cf5f50e00962ca2c983` |
| `tools/claim_audit/receipts.md` | `912a388d47a9` | `629351e6a05012fae196b6c30d79d6c59a27b0f74bd2e48f5a0e12049a0db79a` |
| `tools/claim_audit/risk.md` | `912a388d47a9` | `ddbbbf5e5b20ecb541736c93f741cf5de032b97626a56b7d9dc0e7c2b183515a` |

## Execution required before any acceptance

```sh
python -m pytest -q tests/consolidation/test_claim_audit.py
python -m tools.verify_all
```

Check exact-head logs and negative-control results. Source copy is not equivalent to executed tests. No production/authority promotion or merger is implied.

**E2 / W0 / O0 · V008 HOLD · DO NOT MERGE.**
