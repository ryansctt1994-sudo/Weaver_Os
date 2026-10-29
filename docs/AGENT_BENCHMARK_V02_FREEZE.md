# Frozen synthetic benchmark v0.2 — dependency boundary

**Frozen branch:** `freeze/agent-reliability-v0.2-20261029`  
**Exact commit:** `d72737d7fa51704e2af3d222ecc321e4839770c6`  
**v0.2 test fixture SHA-256:** `68a0eb8bc8a41ccda9d799a743a9a29c13091f1ca888b80424ffe05e6700c75f`  
**v0.2 report SHA-256 (internal report canonical digest):** `59841f8206222e65011550406be0cc6319a0b294a12976c4af28e08c3bdf6872`  
**Git blob SHA of `benchmarks/agent_reliability/portable.py`:** `f2456938297641ce0443d74fa436d58220237baf`  
**Git blob SHA of `tests/test_portable_agent_eval.py`:** `4a56b361c2e1fa54940fba98af2c41888205f15d`

These hashes are content identifiers, not independent assurance. The immutable reference is the exact Git commit; Git branches themselves can be moved. Run the existing v0.2 synthetic suite unchanged. v0.3 builds on but must not modify the v0.2 reference evaluator, case generator or test oracle. Adapter launch aborts on fixture or report hash drift.

v0.2 measures only its fixed synthetic reference, not a real agent. Production E2/W0/O0 HOLD unchanged.
