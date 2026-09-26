# WN-XPROC-AUTH-001 — local cross-process authority boundary

This fixture follows the distinction identified in the Elpis × Weaver crosswalk: a reproducible semantic decision need not carry reproducible permission. It is an independent implementation, not an import of Elpis code.

## Claim and witness

For identical frozen inputs, `semantic_result` returns identical bytes across two fresh Python processes. Each process creates a different random issuer identity and Ed25519 key. A grant signed in one process is rejected by another. Within an issuer, a signed grant binds actor, action, artifact, policy, epoch, nonce and half-open validity interval. A successful consume is single-use; a denied consume leaves the protected state digest unchanged. A lock makes concurrent duplicate consumes single-use within one process.

Run `pytest -q tests/test_xproc_authority.py`. The test covers valid use, repeat use, foreign issuer, tampered body/signature, malformed fields, each scope dimension, stale epoch, revocation, time bounds, concurrent duplicate use, and fresh subprocess separation. The pytest job in `.github/workflows/tests.yml` runs this suite on Python 3.10–3.12.

The signing key is created by the fixture itself and the public key is trusted by that same local instance. This establishes cryptographic binding within the fixture only. It does **not** authenticate a human approver, attest external evidence, provide a persistent trust anchor, handle crashes or cross-host concurrency, prove independent reproduction, or authorize real-world side effects. Revocation, used nonces, and state are in memory. The semantic result is a digest of fixed input fields, not an actual Weaver policy adjudication. This is a compositional test target for a future real issuer/verifier and transactional store.

WN-E2E-001 remains a separate bounded transaction demo. Its evidence-presence checks should not be construed as signed authority; this fixture does not silently upgrade those checks.
