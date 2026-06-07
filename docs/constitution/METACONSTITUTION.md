# Metaconstitution

Status: `CVP_FREEZE_2026_06_06`  
Layer: Above Constitution / Below Reality

## Purpose

The metaconstitution defines the bootstrap assumptions that precede ordinary constitutional and policy processes.

It exists because the first rulebook cannot be derived from a prior rulebook. The correct response is not to pretend genesis is verified. The correct response is to permanently label genesis as a bootstrap assumption.

## Core Principles

```text
GENESIS_IS_DECLARED_NOT_VERIFIED
GENESIS_MUST_REMAIN_VISIBLE
BOOTSTRAP_ASSUMPTIONS_MUST_NOT_BE_LAUNDERED_INTO_PROOF
```

## Genesis Receipt Requirement

The first constitutional artifact must be represented as a Genesis Receipt.

Minimum fields:

```json
{
  "receipt_type": "GENESIS_CONSTITUTION",
  "status": "BOOTSTRAP_ASSUMPTION",
  "derived_from_prior_policy": false,
  "replayable_from_prior_policy": false,
  "genesis_hash": "sha256(...)",
  "declared_at": "timestamp",
  "declared_by": ["founding_actor_or_process"],
  "limitations": ["not independently derived", "not verified by prior policy"]
}
```

## Constitutional Rule

The Genesis Receipt is admissible only as a declared starting condition.

It must never be relabeled as:

```text
VERIFIED_TRUTH
```

or:

```text
PROVEN_ORIGIN
```

## Rationale

A verification chain cannot extend before its first link. The metaconstitution preserves this fact rather than hiding it.

Every later policy, receipt, authority transition, rejection, quarantine, or adjudication must be justified through replayable evidence.

Genesis is the one explicitly marked exception, and the exception must remain visible forever.
