# Consolidated Must-Keep Registry

Cathedral / Sentinel / Weaver / TSC-001 / Frontier Signal Stack

Status: LOCKED

Purpose: preserve the load-bearing artifacts, code modules, doctrines, schemas, specifications, and integration documents produced across this chat.

## 1. Executable Authority Kernel

Highest preservation priority. These artifacts participate in authorization, replay, receipts, or boundary enforcement.

```text
runtime_gate.py
runtime.py
verifier.py
guardian.py
policy.py
decision_engine.py
executor.py
capability.py
violations.py
```

Core doctrine:

```text
Authority only exists after verification.
Capability is not legitimacy.
Proposal is not authority.
```

## 2. Chronicle and Replay

```text
chronicle.py
receipt.py
hashchain.py
audit_trail.py
replay.py
replay_engine.py
replay_verifier.py
replay_validator.py
anchor.py
ledger.py
policy.py
```

Tests:

```text
test_ledger.py
test_anchor.py
test_replay.py
test_replay_determinism.py
```

Doctrine:

```text
Replay supersedes narration.
History authorizes.
Narrative does not.
```

## 3. Topology Enforcement

PATCH-1 artifacts:

```text
topology_contract.yaml
verify_topology.py
scan_imports.py
scan_invocations.py
snapshot_dag.py
TOPOLOGY_SNAPSHOT.json
artifact_manifest.json
repo_artifact_map.json
cathedral_ci.yml
```

Tests:

```text
test_no_direct_decide_calls.py
test_topology_snapshot_stable.py
test_no_runtime_bypass.py
```

Invariant:

```text
No unauthorized capability construction.
```

## 4. Version Legitimacy

```text
version_receipts/
validation_receipts/
build_receipts/
```

Invariant:

```text
Every version earns legitimacy.
```

## 5. TSC-001D Executable Control Stack

Authority resolution:

```text
triadic/resolver.py
AuthorityResolution dataclass
test_resolver_tsc001d.py
```

Capabilities:

```text
governance debt
outcome history
evidence ladder
signal registry
mythic content quarantine
hardware sovereignty
scope sovereignty
witness attestations
```

## 6. Governance Debt Engine

```text
governance_debt.py
DebtEntry dataclass
GovernanceDebtEngine
test_governance_debt.py
```

Debt types:

```text
VERIFICATION_DEBT
AUTHORITY_DEBT
ATTESTATION_DEBT
REPLAY_DEBT
SCOPE_DEBT
SIGNAL_DEBT
OUTCOME_DEBT
```

Invariants:

```text
EXCEPTIONS_ACCUMULATE_DEBT
DEBT_REQUIRES_RECEIPT
```

## 7. Trust Ledger / TSC-001

Core artifacts:

```text
Trust Ledger
Authority Resolver
Authority Tokens
Refusal Signals
Authority Decay
Replay Engine
```

Ledger fields:

```text
governance_debt
outcome
counterfactual
witness_attestations
mythic_content_flag
signal_registry_status
scope_jurisdiction
hardware_lock_required
evidence_level
```

## 8. Governance Debt Package

Specifications:

```text
GOVERNANCE_DEBT_ENGINE_SPEC.md
STATUS_LEDGER_ALIGNMENT.md
```

Lifecycle:

```text
creation
classification
severity
aging
escalation
reconciliation
retirement
```

## 9. Outcome Intelligence Package

Core modules:

```text
outcome_tracker.py
intervention_analyzer.py
drift_monitor.py
trust_predictor.py
execution_forecaster.py
impact_evaluator.py
```

Learning modules:

```text
causal_tracker.py
intervention_registry.py
outcome_memory.py
policy_feedback.py
effectiveness_index.py
```

Counterfactual analysis:

```text
COUNTERFACTUAL_VALUE_ANALYSIS.md
```

Doctrine:

```text
Execution is not success.
Prediction is not impact.
Learning requires outcome evidence.
```

## 10. Frontier Signal Registry

Core files:

```text
FRONTIER_AI_SIGNAL_REGISTRY_v1.2.md
frontier_signal_gate.py
FRONTIER_SIGNAL_ADMISSION_PROTOCOL.md
SIGNAL_IS_NOT_AUTHORITY.md
```

Schemas:

```text
GOVERNANCE_PATTERN_SIGNAL.schema.json
CHRONICLE_SIGNAL_EVENT.schema.json
MODEL_CAPABILITY_CLAIM.schema.json
SCIENTIFIC_DISCOVERY_CLAIM.schema.json
CYBER_CAPABILITY_SIGNAL.schema.json
```

Tests:

```text
test_frontier_signal_gate.py
```

Invariant:

```text
Signal is not authority.
```

## 11. Mythos Authority Boundary

Canonical artifact:

```text
MYTHOS_AUTHORITY_BOUNDARY.md
```

Supporting components:

```text
mythology_gate.py
ghost_pattern_detector.py
salvage_protocol.py
```

Core invariant:

```text
The Mythos may explain.
The Mythos may inspire.
The Mythos may remember.
The Mythos may not authorize.
```

Additional invariants:

```text
Narrative coherence is not legitimacy.
Meaning is not authority.
Story is not verification.
Interpretation is not governance.
```

## 12. Scope Sovereignty Package

Artifacts:

```text
SCOPE_SOVEREIGNTY.md
scope_registry.py
scope_authority_registry.json
```

Invariant:

```text
Valid authority outside scope equals no authority.
```

## 13. QGS Evidence Ladder

Artifact:

```text
QGS_EVIDENCE_LADDER.md
```

Levels:

```text
E0 Claim
E1 Specification
E2 Simulation
E3 Receipted
E4 Replicated
E5 Audited
```

Doctrine:

```text
Documentation is not reality.
Only evidence promotes.
```

## 14. Witness Federation

Artifacts:

```text
witness_registry.py
witness_observer.py
witness_receipts.py
witness_federation_sim.py
WITNESS_FEDERATION_DOCTRINE.md
```

Invariant:

```text
Witnesses observe.
Witnesses replay.
Witnesses attest.
Witnesses do not authorize.
```

## 15. Hardware Sovereignty Track

FPGA / silicon layer:

```text
top_level_veto.v
scar_latch.v
lucifer_latch.v
pulse_guard.v
gatekeeper.v
quorum_voter.sv
heartbeat_monitor.sv
sha256_ancestry.sv
bram_delta_streamer.sv
ZOREL_AEGIS.vhd
zorel_watchdog.vhd
```

Provisioning and formal verification:

```text
forge_genesis.py
bootstrap_genesis.py
MANIFEST.sha256
lattice_formal.sby
guillotine_proof.sv
z3_sovereignty_spec.py
DEEK.tla
sim_no_escape.tcl
```

## 16. Formal Assurance Stratum

```text
CathedralOS.lean
NSIR_UNIFIED.tla
CapAlgebraRefinement.tla
DistributedWitnessExtension.tla
z3_sovereignty_spec.py
z3_promotion_proof.py
z3_predicate_proof.py
```

Doctrine:

```text
Proof constrains execution.
Proof does not execute.
```

## 17. Explainability Suite

Interactive artifacts:

```text
CathedralOS_Explorer.jsx
Sentinel_Runtime_Console.jsx
The_Membrane.jsx
Trajectory_View.jsx
Tier21_Shell.jsx
The_Empty_Throne.jsx
```

Purpose:

```text
visualization
education
auditability
non-authoritative
```

## 18. SSAL Product Wedge

Artifacts:

```text
PO6 Engine
SSAL Architecture
Survivability Receipts
Trajectory Classifier
```

Markets:

```text
microgrids
virtual power plants
industrial energy
autonomous infrastructure
```

## 19. Master Constitutional Documents

```text
GENESIS_CHRONICLE.md
INITIAL_INVARIANTS.md
FOUNDING_STRESS_EPOCH.md
STEWARD_FORMATION.md
CONSTITUTIONAL_DISSOLUTION.md
MASTER_INDEX.md
STRATA_REFERENCE.md
WEAVER_OS_UNIFIED_MASTER_REGISTRY_v7.0.md
WEAVER_OS_HANDOFF_PACKAGE_v1.0.md
```

## 20. Irreducible Survival Bundle

If everything else is lost, preserve:

```text
RuntimeGate
Guardian
Verifier
Chronicle
Replay
Receipts
Topology Enforcement
Version Receipts
Governance Debt Engine
Authority Resolver
```

Six statements to preserve:

1. Every layer may propose.
2. Only the kernel may authorize.
3. Every authorization must produce a receipt.
4. Every receipt must be replayable.
5. CLASSIFICATION_PRECEDES_PROMOTION.
6. Authority only exists after verification.

## Final Compression

```text
Proposal
-> Verify
-> Gate
-> Record
-> Replay
-> Attest
-> Execute
-> Outcome
-> Counterfactual
-> Learn

Any bypass
-> Governance Debt
-> Resolution Receipt
```

## Final Seal

```text
The throne remains empty.
Replay preserves lineage.
Witnesses attest but do not rule.
Scope bounds authority.
Debt preserves accountability.
Mythos may explain but not authorize.
Signals may inform but not command.
Only evidence survives promotion.
```
