# Dual Ledger Model

Status: `CVP_FREEZE_2026_06_06`  
Layer: Chronicle / Replay / Evidence

## Purpose

The Dual Ledger Model separates admitted state transitions from denied or quarantined authority attempts while binding both histories under a common Chronicle Root.

A failed action is not state. A failed action is evidence.

## Structure

```text
[ Chronicle Root ]
      │
      ├── [ Authority Root ]
      │     ├── State Transition
      │     ├── Promotion
      │     └── Admitted Receipt
      │
      └── [ Rejection Root ]
            ├── P12 Failure
            ├── Fork Quarantine
            ├── Policy Rejection
            └── Denied Promotion
```

## Authority Ledger

Contains only admitted events:

```text
Admitted proposals
Valid decisions
Promotions
State transitions
Authority receipts
```

Rule:

```text
Only successful admissible transitions appear in the Authority Ledger.
```

## Rejection Ledger

Contains denied or quarantined events:

```text
Tampered event hash rejections
Invalid signature rejections
Broken predecessor rejections
Fork quarantine receipts
Sovereign decree rejections
Policy mutation rejections
Authority expansion quarantines
Constitutional override rejections
```

Rule:

```text
Every failed gate must produce a rejection or quarantine receipt.
```

## Chronicle Root

The Chronicle Root binds the Authority Root and Rejection Root.

Purpose:

```text
Preserve what happened.
Preserve what was prevented.
```

## Core Invariants

```text
FAILED_ACTIONS_ARE_NOT_STATE
FAILED_ACTIONS_ARE_EVIDENCE
REJECTIONS_MUST_BE_CHRONICLED
```

## Replay Semantics

Authority replay asks:

```text
What state transitions occurred?
```

Rejection replay asks:

```text
What authority attempts were denied, quarantined, or blocked?
```

Chronicle replay asks:

```text
Are both histories cryptographically bound and consistent with the declared root?
```

## Rationale

Writing rejection receipts directly into the Authority Ledger pollutes state replay and lets attack volume inflate state replay cost.

Writing rejection receipts into an unbound shadow log makes defensive history optional.

The Dual Ledger Model avoids both failures by separating state from rejection evidence while binding both under the Chronicle Root.
