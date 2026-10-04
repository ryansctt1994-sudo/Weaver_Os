# WitnessBoundary bounded model

This concrete TLA+ model abstracts a single protected counter, one command, and three ledger blocks. It checks that a rejected command preserves the counter, an accepted command follows the authorized action, and a verification verdict requires intact blocks, the pinned head, and the trusted key. The `ByteTamper` action is a Boolean abstraction of byte mutation; the model does not compute SHA-256, Ed25519, or JSON parsing. The Python adversarial tests exercise those implementation details separately.

Run TLC using official GitHub asset ID `602290600` from `tlaplus/tlaplus` v1.8.0. Download `https://api.github.com/repos/tlaplus/tlaplus/releases/assets/602290600` with the `Accept: application/octet-stream` header. Verify SHA-256 `1d99ab9ad6cf6fb9839dcc7d4a04fd262e136d452edf2a4928c5c18dd4b3468f` before use. CI pins both the asset ID and digest, so replacing the named release asset will not silently select a new binary:

```sh
cd audit-package/formal/tla+
java -cp /path/to/tla2tools.jar tlc2.TLC -deadlock -config WitnessBoundary.cfg WitnessBoundary.tla
```

Local run on 2026-10-01 UTC: TLC2 `2026.10.01.003433`, 917 states generated, 254 distinct states, complete graph depth 8, zero errors. A negative control changed `Unauthorized` to increment `protected`; TLC reported `RejectedPreservesState` violation at depth 2. The original JAR had SHA-256 `e3f5f648b75d68c14176b961ec7bfc1e94ab4c14de57f251b8c40a0fbf916e27`. On 2026-10-01 the named release download returned different bytes, and the pinned checksum correctly stopped CI. The replacement was explicitly inspected against the official asset metadata and rerun: TLC2 `2026.10.01.024053` (rev `0dab95e`), the same 917 generated / 254 distinct states, depth 8, and zero errors. The current pinned asset and digest are given above. This preserves the old result as history and records a new tool revision rather than treating the old download URL as an immutable artifact.

This is bounded model checking of this abstraction. It does not prove the Python implementation refines the model, discharge the older CCS skeleton, authenticate a publisher, or provide an independent operator's reproduction receipt.


## WeaverActivation bounded model

`WeaverActivation.tla` is a separate bounded model for the Weaver Activation Runtime. It models two concurrent requests, authority admission, an explicit authority-event → request/contract/backend/checkpoint/input binding, single execution via an execution counter, phase-correct rejection, substitution and non-finite-result rejection, PASS recording, deterministic REJECT evidence, protected-state preservation, and zero authority gain.

Run it with the same pinned TLC JAR:

```sh
cd audit-package/formal/tla+
java -cp /path/to/tla2tools.jar tlc2.TLC -deadlock -config WeaverActivation.cfg WeaverActivation.tla
```

The repository verification gate requires both `WitnessBoundary` and `WeaverActivation`. Neither model is a refinement proof of the Python/C implementation; runtime correspondence remains a separate obligation.
