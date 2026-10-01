# Durable request and transitive drift proofs

The durable model binds the full typed request (actor, action, resource, parameter list and nonce) to a stored approval. Authentication principal, time and trusted current policy are separate inputs. The model consumes approval IDs permanently; IDs must not be reset/reused or removed from retained durable state. It establishes immediate retry idempotence and denial after arbitrary modeled intervening attempts.

Effect records, consumed approvals and receipt records are updated in one abstract atomic transition. Recovery chooses the pre-commit state or the committed state. This is an explicit storage-atomicity assumption, not a verification of a storage engine, crash implementation, filesystem or external actuator. Effect/receipt equality is preserved when initially true. The model does not guarantee human approval authenticity, root validity or external request parsing; trustedPolicy must come from the actual authorization boundary.

The drift model proves that any recorded transitive path from a changed source prevents semantic Currentness. It proves propagation for any stale-set implementation closed under dependency edges. A separate executable fuel-bounded expansion has stale-preservation proofs and positive two-hop/insufficient-fuel examples. General correspondence between that bounded expansion and all reachable nodes is not proved. Unrecorded dependencies and too little fuel are coverage gaps; absence from the result must not be treated as proof of currentness.

Run lake build and lake env lean Audit.lean from formal/wns-kernel with the pinned Lean toolchain. Exact declaration and axiom audit logs are retained by CI. No Lean/Python runtime refinement proof or independent witness is claimed.
