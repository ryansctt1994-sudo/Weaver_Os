# Weaver OS Repository Contract

## Role

This repository is the canonical control plane for the three-repository Weaver Nexus master build.
It owns constitutional policy, authority verification, release provenance, promotion rules, portfolio manifests, and cross-repository conformance contracts.

It does not absorb arbitrary donor frameworks, experimental model code, domain research, or formal proofs merely because those artifacts are useful.

## Permanent laws

- Capability is not authority.
- Verification is not authorization.
- Architecture is not execution evidence.
- A local run is not independent reproduction.
- No receipt, no promotion.
- Missing or ambiguous evidence fails closed.
- Failed validation is evidence and must be preserved.
- Historical artifacts are superseded, never silently rewritten.

## Allowed changes

- Narrow verification and release-guard primitives.
- Canonical schemas and deterministic serialization rules.
- Replay, receipt, Chronicle, authority, and promotion interfaces.
- Cross-repository manifests and conformance checks.
- Evidence-bounded documentation and migration ledgers.

## Prohibited changes

- Unpinned third-party source dumps.
- Autonomous execution authority.
- Physical actuation enabled by default.
- Mythos or symbolic artifacts on an execution path.
- Production, safety, medical, legal, AGI, or hardware claims without scope-bound evidence.
- Copying code across incompatible licenses without an explicit provenance and license review.

## Completion gate

A change is incomplete until it states:

1. the bounded claim;
2. the source revision and dependency identity;
3. the exact validation command;
4. the positive and negative-path result;
5. the resulting evidence level;
6. what remains unproved;
7. whether authority or deployment posture changed.

Default authority remains `NONE`. Default promotion remains `HOLD`.