# Operator-pinned Chronicle replay — research candidate

**Scope:** a bounded local comparison to a separately provided checkpoint. **Not** a witness service, operational authority gate, production authenticator, E3 promotion or closure of Issue #143.

## Inputs / trust separation

The operator must obtain these from a separately controlled evidence-custody channel, **not simply copy them from the same writable runtime folder**:

1. A UTF-8 JSONL Chronicle file from the system being assessed (up to 1,000,000 bytes).
2. A JSON checkpoint file (up to 16,384 bytes) containing exactly:

```json
{
  "schema_version": 1,
  "source_commit": "<40 lowercase hexadecimal characters>",
  "entry_count": 1,
  "terminal_hash": "<64 lowercase hexadecimal characters>",
  "chronicle_sha256": "<64 lowercase hexadecimal characters>"
}
```

3. The checkpoint's **raw-file SHA-256** obtained independently of the system supplying the file.
4. The **exact source commit** expected by the operator, also obtained independently.

A checkpoint minted by the same untrusted actor who controls the Chronicle has no independent trust value even if every byte and hash agrees. A GitHub-hosted regression test using fixture pins is **not independent custody**.

## Reproduce locally on the reviewed commit

```bash
python -m weaver_auth.bedrock.operator_pinned_replay \
  --chronicle /operator/input/chronicle.jsonl \
  --pin /operator/custody/checkpoint.json \
  --expected-pin-sha256 "$PIN_SHA256_FROM_INDEPENDENT_CHANNEL" \
  --expected-source-commit "$EXPECTED_SOURCE_COMMIT"
```

Exit 0 means **PIN_MATCH_LOCAL_CHAIN_PASS** and *only* that the provided bytes, entry count, terminal hash, and code-label reference matched the stated expected commitment. Exit 2 is **FAILURE**; no data or trust claim is promoted. There are no default fixture pins and no silent fallback.

## Negative controls

`pytest -q weaver_auth/bedrock/tests/test_operator_pinned_replay.py` covers missing inputs, mutated pin and digest, wrong code identity, modified/rehashed chronicle content, removal of an otherwise valid complete suffix, duplicate JSON keys, nonstandard numeric values, oversized input, and CLI failure exit behavior.

## Limitations and future gates

- No cryptographic signature on the checkpoint, key identity, authenticated witness service, external audit channel, protected custody store, recorded custody event, external operator reproduction, or runtime lineage proof is delivered by this candidate.
- Matching a hash with an operator-supplied value cannot prove the operator value came from an independent witness. Source `source_commit` is only a comparison label, not proof of the running binary or deployment.
- This verifier uses the **Gate 1 test harness's local JSONL hash-chain convention**, not the typed production Chronicle schema. Format mapping to actual operational receipts has **not** been shown.
- The verifier is intentionally **not wired to the protected commit or Gate 1 pass/fail path**. Integration would require a separately reviewed threat model, provenance controls, and witnessed operational replay.
- Bound verification does not stop an attacker with control over the operator's external pin from substituting both Chronicle and checkpoint.

**Status: E2 · W0 · O0 WITHHELD · PRODUCTION PROHIBITED. Keep Issue #143 OPEN.**
