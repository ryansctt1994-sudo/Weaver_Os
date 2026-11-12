# PROOF — bounded review-only extraction

**Parent**: #134 `de15972b4fc29ec0a21f521ccf641946270ffcbf`. **Combined source**: #135 `f65fa54c56341a8d5508af728fc773055afa1cd2`. All extracted source files are exact Git blobs from #135.

**Non-claims**: Pure offline log inclusion, SET and checkpoint verification using a pinned test log key. Verification of publication bytes does not authenticate publisher identity, correctness, or a physical board. The CLI handles local file loading; no network fetching is included.

## Exact source/target provenance

| Path | Source commit | Target SHA-256 or source identity |
|---|---|---|
| `packages/verifier/weaver_verifier/public_log.py` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `78c003809be60822575c42c834ed6fcced6903ed008ee9731da3149e3dbe8118` |
| `tests/consolidation/__init__.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |
| `tests/consolidation/test_public_log.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |
| `tests/fixtures/consolidation/rekor/checkpoint.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `cfbc72137d476a7c89817ba5e12f0104aa3e3b5be35079f8be295743a83fbd78` |
| `tests/fixtures/consolidation/rekor/rekor-entry.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `7feae658065d177c73d9a45924a4295238390f1096bd83944a56e9363c6774bc` |
| `tests/fixtures/consolidation/rekor/rekor-public-key.pem` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `dce5ef715502ec9f3cdfd11f8cc384b31a6141023d3e7595e9908a81cb6241bd` |
| `tests/integration/wheel_smoke.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |
| `tools/consolidation/__init__.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |
| `tools/consolidation/verify_publication.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |

## Required verification

```sh
python -m pytest -q tests/consolidation/test_public_log.py
python -m tools.verify_all
```

Acceptance requires actual logs for this exact head, negative controls, and review of all active imports and license files. This branch intentionally does not carry unrelated tools or eight archival ZIP snapshots, which remain frozen in #135. Recheck on the final integrated tree; no source's previous CI results transfer to this SHA.

**E2 · W0 · O0 WITHHELD · V008 HOLD · DO NOT MERGE · PRODUCTION PROHIBITED.**

## Exact-scope canonicalizer compatibility exception

The historical Rekor SET/checkpoint signature input is not encoded as WX-CJSON-1. The existing repository-wide `tools.check_trust_domains` rule therefore needs a **single named exception** for `verifier/weaver_verifier/public_log.py`, matching the already-tested combined #135 candidate. This exception is restricted to the retained Rekor signature-byte profile; no other verifier or authority module may opt into legacy `json.dumps(sort_keys=True)` hashing. The checker continues to reject new legacy canonicalizers and stale allowlist entries.

The first extracted candidate `cc8212a171cad9130c84d1e4073005c9ab1da2fd` failed hosted `unit_and_integration` because this exception was missing. Its original red reports must be retained. The follow-up is a compatibility check fix, not an authority relaxation or a new cryptographic proof.
