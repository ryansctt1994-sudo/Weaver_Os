# Witness Attestations

## Purpose

This file records witness statements and the limits of witness independence.

## Attestation format

Each witness entry should include witness identifier, role, environment relation, toolchain relation, communication relation, funding relation, attestation scope, timestamp, and signature or approval marker.

## Witness register

| Witness ID | Role | Independence Notes | Scope | Status |
|---|---|---|---|---|
| W-001 | Internal reviewer | Not independent from author environment | Local verification review | Partial |
| W-002 | Secondary reviewer | Independence not yet demonstrated | Replay review | Partial |
| W-003 | Formal methods reviewer | Toolchain relation declared, independence partial | Theorem discharge review | Partial |

## Attestation rule

A witness may support local evidence, but no witness should be described as fully independent unless the relevant independence dimensions are documented and verified.

## Current conclusion

Witness evidence is informative but not yet sufficient for E4 or higher.
