# Cathedral-Sentinel-Weaver Roadmap

Status: E1 SPEC / CONTINUITY ARTIFACT

## Phase 1: Strict Verifier Adapter

Build and test `verify_adapter.py`.

Required controls:

```text
signing_domain allowlist
payload_schema_version allowlist
ed25519 algorithm enforcement
base64url key encoding enforcement
scope enforcement
max authority duration enforcement
registry sequence rollback protection
replay-after-auth behavior
negative-path test matrix
```

## Phase 2: Key Registry

Implement active key custody semantics.

Required states:

```text
ACTIVE
ROTATED
SUSPENDED
REVOKED
```

Required controls:

```text
key rotation
key revocation
registry sequence monotonicity
issuer identity binding
scope binding
```

## Phase 3: Persistent Replay Cache

Move from development replay protection to production-grade persistence.

Target:

```text
SQLite WAL
atomic check-and-record
concurrent safety
no insertion before auth
```

## Phase 4: External Verifier Federation

Add witness and transparency infrastructure.

Required controls:

```text
WORM transparency log
independent witness receipts
fork detection
non-participating witness support
quorum separation
```

## Phase 5: Hardware and Crypto Custody

Move from software-only enforcement to final custody.

Targets:

```text
hardware veto path
HSM or equivalent key custody
physical latch integration
operator receipt capture
```

## Release Readiness Rule

A phase is not complete until receipts exist.

Local implementation alone is insufficient.
