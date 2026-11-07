# wx-state-digest-1: runtime state reconstructed from the ReceiptLedger (WNS-S6-001)

**Status:** IMPLEMENTED (`weaver_verifier.state`)
**Evidence:** R2[self]
**Authority:** NONE / O0. **Witness:** W0. **E3.5:** HOLD. **C-GATE-001:** OPEN.
**Outline step:** 6

## Question it answers

Can Weaver rebuild its runtime state from the current ledger, detect manipulated history, and
refuse to vouch for a state it cannot verify? Within the limits below: yes. It **cannot** tell an
authentic history from a complete, self-consistent rewrite unless the anchor is held by someone
the ledger's operator does not control. It says so in every report.

## Projection `wx-runtime-state-1`

Rebuilt only from a snapshot that passes `verify_snapshot`. Every Authority Root event must be an
`EXECUTION_COMMITTED` event in exactly the gate's shape. Anything else refuses.

```json
{"projection": "wx-runtime-state-1",
 "executions": {"<proposal_id>": {"action", "actor_id", "policy_version", "payload_sha256",
                                   "decision_id", "revalidation_decision_id", "result_sha256",
                                   "sequence", "receipt_digest"}}}
```

- Rejected and quarantined attempts are **not** state (`FAILED_ACTIONS_ARE_NOT_STATE`). They still
  change the digest, through the Rejection Root head and length.
- A proposal committed twice refuses. That is possible in a ledger written without `unique_key`.

## Digest

```text
"wx-state-digest-1:" + hex(SHA-256(b"wx-state-digest-1\x00" + WX-CJSON-1({
    schema: "wx-state-digest-1", projection: "wx-runtime-state-1", canonicalization: "WX-CJSON-1",
    source: {kind: "reducer_module_sha256", value: SHA-256 of weaver_verifier/state.py},
    ledger: {ledger_id, chronicle_root, roots: {AUTHORITY, REJECTION}: {length, head}},
    state:  <projection>
})))
```

- **Versioned and self-describing.** The digest string carries its schema. An expected digest under
  any other schema is refused, never reinterpreted.
- **Nothing comes from the caller.** The state is reconstructed, the heads and Chronicle Root are
  recomputed by the verifier, and the source hash is read from the reducer's own file. An
  `expected_digest` or `claimed_state` is only ever *compared*.
- **Source binding is the reducer's file hash,** not a git commit. The verifier domain may not run
  processes (UADR-0001), and a file hash also works from an installed wheel. Any edit to the reducer
  changes every digest. That is deliberate: a digest means "this code, this history".

## Statuses

| Status | Meaning |
|---|---|
| `REFUSED` | History or claim not supported; the reason is given |
| `UNANCHORED` | Chains consistent. **Authenticity not established:** a full rewrite looks the same |
| `ANCHOR_MATCHED` | Also matches the supplied anchor. **Custody not established:** an anchor from the same party proves nothing more |

Every report carries `authenticity: NOT_ESTABLISHED`, `custody: NOT_ESTABLISHED` and `witness: W0`.
No code path can report "witnessed" or "authentic".

## Independent verification

`python -m tools.export_ledger …` writes the snapshot and anchor files.
`python -S -m weaver_verifier.state --snapshot s.json --anchor a.json [--expect D] [--claim C]`
recomputes in a **fresh process** with no site-packages and only `packages/contracts` and
`packages/verifier` on the path. A test checks that runtime code is not importable there, and that
the fresh process reproduces the in-process digest on repeated runs.

A fresh process on the same machine from the same checkout is **not independent witnessing.** It
is also **not implementation-independent**: it runs the same `weaver_contracts.canonical` and
`weaver_verifier.ledger` code. A bug shared by both runs would be reproduced, not caught. This is
process-separated reproduction only. An independent check would need a second implementation of
the canonicalizer, the chain verifier and the reducer (step 10 since GD-0005 D13; outline step 9 before, R5).

## Relationship to the existing digests

This is a new, separately named projection, as `docs/RUNTIME_STATE_DIGEST_CONTRACT.md` requires.
It does **not** replace or reinterpret `authority-transition-reducer-v1` (the
`LOCAL_REDUCER_COMPUTED` digest over `authority_ledger.json` in `published_manifest.json`) or the
Witness RC1 adapter. Neither of those files changes. `kernel/reducer.py` keeps its RC1 deferral,
because its RC1 semantics are a different projection. So E3.5 stays HOLD (`verify_attestations.py`
still requires `COMPUTED_FROM_RUNTIME`, and a test checks that it still fails).

## Negative controls (`tools/state_controls.py`)

| # | Corruption | Expected | Observed |
|---|---|---|---|
| C1 | event altered, hash not updated | reject | REFUSED (event digest mismatch) |
| C2 | two entries reordered | reject | REFUSED (sequence mismatch) |
| C3 | truncated, checked against a trusted anchor | reject | REFUSED (truncation) |
| C4 | whole chain recomputed, no external reference | expose limitation | UNANCHORED, authenticity NOT_ESTABLISHED; REFUSED against the honest anchor |
| C5 | canonical serialization changed | digest mismatch | REFUSED (non-canonical bytes); a legacy-serializer digest differs; an other-schema digest is refused |
| C6 | committed outcome changed and resealed | reject or mismatch | REFUSED against the anchor and against the honest digest |
| C7 | uncommitted action presented as committed | reject | REFUSED (claim unsupported; a moved rejection entry is refused) |
| C8 | forged anchor **and** digest from the same attacker | expose custody limit | ANCHOR_MATCHED with custody NOT_ESTABLISHED, W0 |
| C9 | same ledger replayed twice, and rebuilt | identical digest | identical |

Mutations in `tools/check_verifier_mutations.py` remove chain validation, reconstruction, source
binding, digest comparison, duplicate-commit refusal and claim comparison. Each is caught by a
named test.

## Limits

- **Custody:** the verifier cannot know who holds an anchor. Closing that is Step 7.
- **Scope:** the projection covers gate executions only. Other Authority Root event types refuse.
- **C-GATE-001 is untouched:** a commit that slipped through the commit-boundary race is a valid
  ledger entry, and this digest will faithfully include it.
