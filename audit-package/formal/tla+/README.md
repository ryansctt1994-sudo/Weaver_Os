# WitnessBoundary bounded model

This concrete TLA+ model abstracts a single protected counter, one command, and three ledger blocks. It checks that a rejected command preserves the counter, an accepted command follows the authorized action, and a verification verdict requires intact blocks, the pinned head, and the trusted key. The `ByteTamper` action is a Boolean abstraction of byte mutation; the model does not compute SHA-256, Ed25519, or JSON parsing. The Python adversarial tests exercise those implementation details separately.

Run TLC with the `tla2tools.jar` from the official `tlaplus/tlaplus` v1.8.0 release. Verify SHA-256 `e3f5f648b75d68c14176b961ec7bfc1e94ab4c14de57f251b8c40a0fbf916e27` before use:

```sh
cd audit-package/formal/tla+
java -cp /path/to/tla2tools.jar tlc2.TLC -deadlock -config WitnessBoundary.cfg WitnessBoundary.tla
```

Local run on 2026-10-01 UTC: TLC2 `2026.10.01.003433`, 917 states generated, 254 distinct states, complete graph depth 8, zero errors. A negative control changed `Unauthorized` to increment `protected`; TLC reported `RejectedPreservesState` violation at depth 2. CI repeats the positive run with the pinned JAR.

This is bounded model checking of this abstraction. It does not prove the Python implementation refines the model, discharge the older CCS skeleton, authenticate a publisher, or provide an independent operator's reproduction receipt.
