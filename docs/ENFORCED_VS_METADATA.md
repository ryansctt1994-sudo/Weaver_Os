# Enforced vs Metadata Contract

This document binds the production JSON Schemas to the current `CryptoVerifier` runtime behavior.

Constitutional rule: if a schema field is required or constraining, the runtime must either enforce it or this document must explicitly classify it as schema-only or informational metadata. Silent gaps are policy drift.

## issuer_record.schema.json

| Field | Status | Runtime behavior |
| --- | --- | --- |
| `issuer_id` | Runtime enforced | Used to resolve issuer identity and distinguish `UNKNOWN_ISSUER` from `UNKNOWN_KEY`. Schema validation enforces UUID form when production schemas are supplied. |
| `key_id` | Runtime enforced | Used with `issuer_id` as the issuer/key lookup tuple. Schema validation enforces UUID form when production schemas are supplied. |
| `public_key_encoding` | Runtime enforced | Must be `base64url`; otherwise verifier returns `INVALID_KEY_ENCODING`. |
| `public_key` | Runtime enforced | Decoded as base64url Ed25519 public key and used for signature verification. Invalid material fails signature verification. |
| `key_type` | Runtime enforced | Must be `ed25519`; otherwise verifier returns `KEY_TYPE_MISMATCH`. |
| `status` | Runtime enforced | `ACTIVE` required. `REVOKED` returns `KEY_REVOKED`; other non-active states return `KEY_NOT_ACTIVE`. |
| `issued_at` | Runtime enforced | Signature `signed_at` must be on or after key issuance. |
| `expires_at` | Runtime enforced | Signature `signed_at` must be before key expiry. |
| `rotated_to_key_id` | Schema-only metadata | Declared by schema but not yet used for rollover resolution. Rotated keys currently fail through non-active status handling. |
| `revoked_at` | Schema-only metadata | Declared by schema but not used for revocation-time reasoning. |
| `revocation_reason` | Informational metadata | Audit/explanation field only. |
| `assigned_roles` | Runtime enforced | Iterated to find a role that authorizes grant/refusal and quorum participation. |

## role_policy.schema.json

| Field | Status | Runtime behavior |
| --- | --- | --- |
| `role_id` | Runtime enforced | Used as the lookup target from issuer `assigned_roles`. |
| `description` | Informational metadata | Human-readable only. |
| `separation_group` | Runtime enforced | Used for independent quorum counting. |
| `max_grant_level` | Runtime enforced | Requested authority level must not exceed this value. |
| `may_grant_authority` | Runtime enforced | Required for authority-token grant validation. |
| `may_revoke_or_refuse` | Runtime enforced | Required for refusal-signal validation. |
| `can_participate_in_quorum` | Runtime enforced | False roles cannot authorize or count toward quorum. |
| `allowed_scopes.systems` | Runtime enforced | Envelope `replay_domain.system_id` must be listed when the allowlist is non-empty. |
| `allowed_scopes.regions` | Runtime enforced | Inner payload `scope.region` must be listed when payload is supplied and allowlist is non-empty. |
| `allowed_scopes.tasks` | Runtime enforced | Inner payload `scope.task` must be listed when payload is supplied and allowlist is non-empty. |
| `allowed_scopes.max_authority_duration_sec` | Runtime enforced | Replay-domain validity window must not exceed this duration. |

## key_registry.schema.json

| Field | Status | Runtime behavior |
| --- | --- | --- |
| `registry_id` | Runtime enforced when a sequence store is supplied | Must be a non-empty string; names the trust domain whose sequence high-water mark is kept. Otherwise schema-validated only. |
| `registry_version` | Schema enforced | Validated by production schema, not otherwise used at runtime. |
| `registry_sequence` | Runtime enforced when a sequence store is supplied | Must be an integer in [0, 2^63-1]. A root-signed registry with a lower sequence than the store's mark for its `registry_id` is refused (`REGISTRY_ROLLBACK`); the same sequence with different signed content is refused (`REGISTRY_SEQUENCE_CONFLICT`). A store requires `root_public_key_b64url`. The mark moves only as the last step of construction: after the root signature verifies, after issuer and role state is built, and only if the registry is inside its validity window. A registry that fails any of these leaves the mark unchanged. Without a store, schema-validated only. |
| `valid_from` | Runtime enforced | Registry is rejected before this timestamp. |
| `valid_until` | Runtime enforced | Registry is rejected at or after this timestamp. |
| `last_updated` | Schema enforced | Validated by production schema, not otherwise used at runtime. |
| `registry_signature` | Runtime enforced when root key supplied | Registry signature is verified over canonical registry JSON without `registry_signature`. |
| `issuers` | Runtime enforced | Source of issuer/key records. |
| `roles` | Runtime enforced | Source of role policies. |

## signature_envelope.schema.json

| Field | Status | Runtime behavior |
| --- | --- | --- |
| `payload_type` | Runtime enforced | Must match `AUTHORITY_TOKEN` or `REFUSAL_SIGNAL` verifier entry point. |
| `payload_schema_version` | Runtime enforced | Signed, and must be allowlisted together with `signing_domain` for this `payload_type` (`weaver_contracts.signing_policy`). Unknown or mismatched versions are refused `UNSUPPORTED_PAYLOAD_SCHEMA_VERSION`; missing, non-string, or empty values are refused `MALFORMED_ENVELOPE`. |
| `payload_hash_alg` | Runtime enforced | Must be `sha256`. |
| `payload_hash` | Runtime enforced | Compared against canonical SHA-256 of supplied inner payload. |
| `signing_domain` | Runtime enforced | Signed, and must be allowlisted for this `payload_type` (`weaver_contracts.signing_policy`). A domain that is unknown, or allowed only for another payload type (cross-domain reuse), is refused `UNSUPPORTED_SIGNING_DOMAIN`; missing, non-string, or empty values are refused `MALFORMED_ENVELOPE`. The check runs before any signature is read. |
| `replay_domain.system_id` | Runtime enforced | Used in replay key and role `allowed_scopes.systems`. |
| `replay_domain.scope_hash` | Runtime enforced | Used in replay key and schema-validated when production schemas are supplied. |
| `replay_domain.valid_from` | Runtime enforced | Replay window must be active and used for duration policy. |
| `replay_domain.valid_until` | Runtime enforced | Replay window must be active, used for cache expiry, and used for duration policy. |
| `signatures[].issuer_id` | Runtime enforced | Used for issuer lookup and signature identity. |
| `signatures[].key_id` | Runtime enforced | Used for issuer/key lookup. |
| `signatures[].algorithm` | Runtime enforced | Must be `ed25519`. |
| `signatures[].signature_encoding` | Runtime enforced | Must be `base64url`. |
| `signatures[].signature` | Runtime enforced | Verified against signing object. |
| `signatures[].nonce_or_sequence` | Runtime enforced | Included in signing object and replay key. |
| `signatures[].signed_at` | Runtime enforced | Checked against issuer key lifecycle. |

### Signing-policy allowlist and compatibility choices (WVR-010)

`weaver_contracts.signing_policy` accepts exactly these triples:

| `payload_type` | `signing_domain` | `payload_schema_version` | Choice |
| --- | --- | --- | --- |
| `AUTHORITY_TOKEN` | `triadic-controls:v0.4.0:authority-token` | `0.4.0` | **Compatibility choice: retained.** Existing tests sign with it, and the envelope schema uses it as its example. Retiring it is a reviewed change to the allowlist and its exact-allowlist test. |
| `AUTHORITY_TOKEN` | `triadic-controls:v0.5.0:authority-token` | `0.5.0` | Current version. |
| `REFUSAL_SIGNAL` | `triadic-controls:v0.5.0:refusal-signal` | `0.5.0` | **Compatibility choice: adopted name.** It follows the authority-token pattern `triadic-controls:<version>:<payload>`. No in-repo producer signs refusal signals yet, so producers must use this exact string. |

Any other triple is refused, including the domains and versions of other payload types.

## verification_result.schema.json

| Field | Status | Runtime behavior |
| --- | --- | --- |
| `is_valid` | Runtime emitted | Final Boolean result. |
| `effective_max_authority_level` | Runtime emitted | Populated with requested level on success; null otherwise. |
| `ledger_event_type` | Runtime emitted | Deterministic event class for ledger behavior. |
| `failure_codes` | Runtime emitted | Deterministic list of failure classes. |
| `verified_issuers` | Runtime emitted | Issuers that fully verified and were recorded. |
| `verified_keys` | Runtime emitted | Keys that fully verified and were recorded. |
| `verification_time` | Runtime emitted | UTC verifier timestamp. |
| `failure_details` | Runtime emitted | Human-readable explanation where available. |

## Known intentional gaps

1. `registry_sequence` rollback protection is enforced only when the caller supplies a
   `registry_sequence_store` (`weaver_runtime.registry_sequence`). Callers that pass none keep the
   old behaviour, and an older root-signed registry inside its window still verifies
   (`test_known_limit_without_a_sequence_store_rollback_still_verifies`). The first registry a
   store sees for a `registry_id` is trusted on first use. Protection covers verifiers that share
   one store: `SQLiteRegistrySequenceStore` on one local file, or one in-memory store in one
   process (lost on restart).
2. The signing-domain and schema-version allowlist is a reviewed code constant. A version stays accepted until the code changes: there is no deprecation or expiry mechanism, and no runtime configuration can add or remove an entry. The allowlist is tested exactly (`test_allowlist_is_exactly_the_reviewed_pairs`), so any change to it is visible in review.
3. `rotated_to_key_id`, `revoked_at`, and `revocation_reason` are retained for audit and future lifecycle logic but are not active policy gates.
4. In-memory replay protection remains CI/local only. Production deployments require persistent atomic `check_and_record` semantics.
