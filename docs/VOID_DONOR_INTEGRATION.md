# VOID neural capability donor integration

Status: reference integration candidate. No authority or evidence promotion is implied.

VOID is treated here as a capability donor, not a peer governance stack. The imported ideas are narrowly scoped to neural activation: a reusable activation lifecycle, model/backend/checkpoint identity binding, restart-friendly checkpoint semantics, primary plus retention metrics, and duplicate-request defense.

The authority path remains Weaver-owned:

```text
proposal
  -> triadic_controls cryptographic authority verification
  -> weaver_void activation adapter
  -> native/private neural backend
  -> ActivationEvidence
  -> canonical receipt / Chronicle path when that source-tree implementation is admitted
  -> replay / witness / adversarial verification
```

Hard boundaries:
- `weaver_void` never mints authority.
- Every evidence object has `authority_delta = 0`.
- The signed authority payload must bind the exact request, action, model, backend identity, native backend digest when present, checkpoint digest, and input digest.
- A valid token for a different activation tuple is rejected.
- Backend result identity must match the authorized intent. Native execution additionally checks the shared-library SHA-256 before and after load and rejects input-byte digest substitution before crossing the ABI.
- A declared retention floor fails closed when the metric is missing or below threshold.
- Process-local duplicate suppression is defense in depth only. Durable exactly-once semantics remain an execution-boundary responsibility.
- No parallel Chronicle or receipt implementation is introduced. The current source-tree `chronicle` and `receipt` boundaries remain deferred to the bound witness until separately admitted.

Native seam status: the public integration now includes a frozen `weaver_void_activate_v1` C ABI header, a strict `ctypes` wrapper, and a compiled conformance fixture. The private/native VOID implementation itself is not in this repository and is not claimed as connected. The native implementation remains responsible for proving that the checkpoint digest named in the request is the checkpoint actually executed.

Next native step: point `NativeVoidBackend` at the private compiled VOID library and run the same signed activation flow against that artifact. The Python adapter remains thin: verify authority, bind identity, verify backend/input digests, call the native seam, normalize results, and hand evidence onward. Model quality, retention, or generalization never imply deployment authority.
