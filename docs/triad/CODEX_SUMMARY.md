# Weaver / Triad Codex Summary

Status: frozen conceptual and implementation handoff for the Triad replay kernel.

Evidence posture: mixed. Repository claims must remain bounded by committed code, deterministic validation, and reproducible receipts.

## One-Line Positioning

We make it hard for powerful systems to quietly become illegitimate by forcing their history, authority, and evidence claims to remain replayable, receipted, and falsifiable.

## Core Purpose

Weaver / Triad is a narrow replay-verified execution substrate for bounded proposals. It separates possibility from admissibility from continuity, then requires replay and receipts before authority claims may be trusted.

## Locked Roles

### Elpis

Creative possibility engine. Elpis generates proposals, simulations, designs, and ideas.

Invariant: `ELPIS_IS_GENERATION_NOT_AUTHORITY`.

### Lumen

Admissibility engine. Lumen performs replay-based admissibility checks and fail-closed authorization.

Invariant: `LUMEN_IS_ADMISSIBILITY_NOT_SOVEREIGNTY`.

### Witness

Continuity engine. Witness is a non-sovereign observer that annotates, preserves dissent, and prevents erasure.

Invariant: `WITNESS_IS_ATTESTATION_NOT_AUTHORITY`.

## Core Mechanisms

- Chronicle: immutable append-only hash-chained ledger.
- Receipts: cryptographically bound evidence packets.
- Replay: legitimacy is recomputed, never assumed.
- Evidence labels: claims cannot promote themselves.
- P12: safeguards must demonstrate correct failure before verification.

## Non-Negotiable Invariants

- No mechanism may silently convert uncertainty into authority.
- `P12_GATE_SELF_FALSIFICATION`.
- History is only authoritative if replay under current policy reproduces an admissible state.
- `ELPIS_IS_GENERATION_NOT_AUTHORITY`.
- `LUMEN_IS_ADMISSIBILITY_NOT_SOVEREIGNTY`.
- `WITNESS_IS_ATTESTATION_NOT_AUTHORITY`.
- `TRIAD_ROLE_COLLAPSE_IS_AUTHORITY_LEAKAGE`.
- `NO_RECEIPT_NO_AUTHORITY`.
- `FAIL_CLOSED`.
- `REPLAY_SUPERSEDES_NARRATION`.
- `REALITY_RETAINS_VETO`.

## Honest Scope

The current target is a bounded prototype ledger and replay-verification kernel. It is not a full AGI governance system, not a distributed constitutional runtime, not production-hardened, and not a safety guarantee.

## Reconstruction Minimum

If everything else is lost, preserve:

1. Prime invariant plus P12.
2. Immutable ledger plus replay verification.
3. Evidence label discipline.
