# Distributed execution boundary and single-writer assumptions

Status: **HYPOTHESIS** for distributed operation; **DOCUMENTATION ONLY** for this threat-model inventory. This is not a proof that every repository component is single-writer.

## Bounded model

Assume a single authoritative writer per logical ledger or keyspace for any test which lacks explicit multi-writer coordination. Within one process, mutexes and replay caches cannot establish cross-process mutual exclusion. Serialization, durable ordering, and atomic compare-and-set require implementation-specific evidence, not a naming convention.

## Unresolved threats and required evidence

| Boundary | Unresolved risk | Minimum validation before distributed claim |
| --- | --- | --- |
| Multi-writer ordering | Two writers assign competing successors, reuse a sequence number, or fork a prior hash | Concurrent interleaving tests with durable linearization evidence and post-crash replay |
| Clocks | Wall-clock rollback, drift, stale TTL and lease expiry | Clock model, monotonicity assumptions, skew injection, and lease-reacquisition tests |
| Key custody | Same signing key across hosts, compromised or rotated keys | Trust anchor inventory, key-ID binding, revocation rules, and historical signature test |
| Replay state | In-memory deduplication lost on restart or divergence across nodes | Durable atomic replay/nonce store exercised across processes and restarts |
| Witness governance | Observer attestations confused with permission to execute | Negative control rejecting witness-only authorization even with multiple agreeing witnesses |
| Partition/recovery | Split brain, partial commits, abandoned leases, and rollback | Fault-injected recovery tests and independently inspected event history |

Do not use host-count, signature-count, or CI success as evidence of distributed safety. No consensus, PKI, institutional custody, or distributed constitutional authority is established here. Witness is attestation, not authority; Elpis generates proposals, and Lumen evaluates admissibility subject to separately validated controls.

For the current integration decision, defer to [Gate Zero issue #29](https://github.com/ryansctt1994-sudo/Weaver_Os/issues/29); it holds production authority and independent witness promotion.
