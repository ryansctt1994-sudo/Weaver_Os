# Failure and Counterexample Log

## Purpose

This file preserves rejected claims, failed tests, and counterexamples.

## Logged items

| ID | Type | Description | Effect on Claims |
|---|---|---|---|
| F-001 | Failed replay condition | A replay step required classification before authority could be assessed. | Confirms replay is bounded. |
| F-002 | Traceability gap | At least one claim lacked direct runtime trace. | Indicates partial support only. |
| F-003 | Witness ambiguity | Independence was not fully established for all witness categories. | Blocks E4+ claims. |
| F-004 | Side-effect uncertainty | Some actions were not classified as replay-safe or replay-prohibited. | Requires stricter replay semantics. |
| F-005 | External validation absent | No independent replication or external audit evidence available. | Prevents authority escalation. |

## Preservation rule

Failures must be retained even when inconvenient.

## Why this matters

Challenge lineage must survive even when approval lineage is favorable.
