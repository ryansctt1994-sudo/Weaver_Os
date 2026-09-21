# verify_adapter.py Phase 1 Specification

Status: E1 SPEC / IMPLEMENTED-PENDING-RECEIPT

## Purpose

`verify_adapter.py` is the trusted boundary that converts verifier output into a ledger-admissible `verify_pass` or `verify_fail` event.

A proposer can only create `propose`.

A verifier may create `verify_*`, but only when cryptographic, schema, scope, signing-domain, duration, replay, and reducer-state checks pass.

## Integration Matrix

```text
signing_domain = weaver.verify.v1
payload_schema_version = verification-payload/1
algorithm = ed25519
public_key_encoding = base64url
```

Standard `base64`, `hex`, `pem`, `raw`, unknown, and missing encodings are rejected.

## Core Rule

No `verify_pass` is admissible unless all of the following hold:

1. Signature is valid.
2. Verifier key is known and active.
3. Key type matches expected algorithm.
4. Public key encoding is `base64url`.
5. Signing domain is allowlisted.
6. Payload schema version is allowlisted.
7. Payload digest matches canonical payload bytes.
8. Scope is allowed: system, region, task.
9. Authority duration is within bound.
10. Registry sequence is monotonic.
11. Replay key has not already been consumed.
12. Reducer state is `PROPOSED`.
13. Replay key is recorded only after all checks pass.

## Required Inputs

```text
adapt_verifier_output(verifier_output, reducer, key_registry, replay_cache)
```

Required verifier fields:

```text
verdict
verifier_id
key_id
key_type
public_key_encoding
signing_domain
payload_schema_version
payload_digest
signature
issued_at
expires_at
registry_sequence
allowed_scopes
```

## Allowed Verdicts

```text
PASS
FAIL
```

All other verdicts fail closed.

## Ledger Event Output

If verdict is `PASS`, emit:

```text
event_type = verify_pass
fsm.to_state = VERIFIED
verifier.verdict = PASS
```

If verdict is `FAIL`, emit:

```text
event_type = verify_fail
fsm.to_state = REJECTED
verifier.verdict = FAIL
```

The adapter synthesizes trusted ledger fields from reducer state:

```text
seq
prev_hash
fsm.from_state
post_state_root
```

It must never trust those fields from verifier input.

## Failure Codes

```text
INVALID_SIGNATURE
UNKNOWN_KEY_ID
KEY_REVOKED
KEY_SUSPENDED
INVALID_KEY_ENCODING
KEY_TYPE_MISMATCH
SIGNING_DOMAIN_NOT_ALLOWED
PAYLOAD_SCHEMA_VERSION_NOT_ALLOWED
PAYLOAD_DIGEST_MISMATCH
SCOPE_NOT_ALLOWED
AUTHORITY_DURATION_EXCEEDED
REGISTRY_SEQUENCE_ROLLBACK
REPLAY_DETECTED
VERDICT_NOT_ALLOWED
REDUCER_STATE_NOT_PROPOSED
```

## Validation Order

```text
parse
validate schema
validate key
validate signature
validate domain
validate payload schema version
validate scope
validate duration
validate registry sequence
validate reducer state
synthesize event
verify event against reducer rules
record replay key
return event
```

Replay cache insertion happens last.

## Minimum Test Matrix

1. Unknown key rejected.
2. Invalid signature rejected.
3. Revoked key rejected.
4. Suspended key rejected.
5. Wrong key type rejected.
6. Wrong public key encoding rejected.
7. Wrong signing domain rejected.
8. Wrong payload schema version rejected.
9. Payload digest mismatch rejected.
10. Scope system mismatch rejected.
11. Scope region mismatch rejected.
12. Scope task mismatch rejected.
13. Authority duration exceeded rejected.
14. Registry sequence rollback rejected.
15. Replay attempt rejected.
16. Verdict other than PASS/FAIL rejected.
17. Verifier cannot author commit.
18. Verifier cannot author genesis.
19. Replay cache is not poisoned by failed verification.
20. Valid PASS emits only verify_pass.
21. Valid FAIL emits only verify_fail.

## Acceptance Criteria

Phase 1 reaches E2 only when implementation and tests exist and pytest passes.

It reaches E3 only when local pytest, build, CLI smoke, and CI receipts exist.

## Non-Claims

Until receipts exist, do not claim production readiness, release candidate status, or forged-verification immunity.
