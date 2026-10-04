# WitnessBoundary bounded model

This concrete TLA+ model abstracts a single protected counter, one command, and three ledger blocks. It checks that a rejected command preserves the counter, an accepted command follows the authorized action, and a verification verdict requires intact blocks, the pinned head, and the trusted key. The `ByteTamper` action is a Boolean abstraction of byte mutation; the model does not compute SHA-256, Ed25519, or JSON parsing. The Python adversarial tests exercise those implementation details separately.

Run TLC using the repository's canonical pinned acquisition helper, `python -m tools.fetch_tlc /path/to/tla2tools.jar`. The current pin is TLA+ tools v1.7.4 with SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`. Both standalone formal workflows and the consolidated verification gate use this same helper so the tool identity cannot drift silently:

```sh
cd audit-package/formal/tla+
java -cp /path/to/tla2tools.jar tlc2.TLC -deadlock -config WitnessBoundary.cfg WitnessBoundary.tla
```

Historical local WitnessBoundary runs remain evidence for those specific tool revisions only. Current CI truth is the repository pin above; changing the TLC version or digest requires an explicit source change and a fresh verification run.

This is bounded model checking of this abstraction. It does not prove the Python implementation refines the model, discharge the older CCS skeleton, authenticate a publisher, or provide an independent operator's reproduction receipt.


## WeaverActivation bounded model

`WeaverActivation.tla` is a separate bounded model for the Weaver Activation Runtime. It models two concurrent requests, authority admission, an explicit authority-event → request/contract/backend/checkpoint/input binding, single execution via an execution counter, phase-correct rejection, substitution and non-finite-result rejection, PASS recording, deterministic REJECT evidence, protected-state preservation, and zero authority gain.

Run it with the same pinned TLC JAR:

```sh
cd audit-package/formal/tla+
java -cp /path/to/tla2tools.jar tlc2.TLC -deadlock -config WeaverActivation.cfg WeaverActivation.tla
```

The repository verification gate requires both `WitnessBoundary` and `WeaverActivation`. It also runs targeted `WeaverActivation` mutation probes: removing the exact authority/contract binding guard must violate `Inv_AuthorityExactBinding`, and removing the rejection-phase guard must violate `Inv_RejectionPhaseSound`.

### WeaverActivation runtime-trace correspondence

`WeaverActivationTrace.tla` replays canonical runtime observations emitted by `ActivationTraceRecorder`. The frozen first-attempt corpus is executed through the Python adapter, each NDJSON trace is SHA-256 bound, and the conformance checker deterministically generates a `GeneratedActivationTrace.tla` data module for TLC.

`Inv_TraceCanAdvance` is the critical refinement-side guard: if an unconsumed runtime event remains, that exact abstract event must be enabled in the base model. This prevents impossible traces from passing by stuttering. CI also requires two negative controls to fail: `Execute` before `BindContract`, and an authority-phase rejection code after execution.

This establishes mechanical correspondence for the frozen first-attempt adapter corpus. It is not a universal refinement proof. Duplicate-request behavior needs a persisted consumed-request pre-state before it can be represented faithfully, and native checkpoint execution/memory integrity remain separate lower-layer obligations.
