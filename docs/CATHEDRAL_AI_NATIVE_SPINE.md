# Cathedral AI-Native Spine

Status: canonical architecture note / implementation roadmap  
Scope: Weaver OS / Cathedral-Sentinel-Weaver MVP track  
Authority: specification and build-order guide, not a receipt

## Core identity

```text
AI-Native Stack = capability engine
Weaver-Lumen / Elpis = authority governor
Cathedral System = constitutional wrapper around capability
```

The architecture is not just agents. It is agent capability plus authority
boundaries, evidence registry, replay, witnesses, governance debt, and immutable
Chronicle records.

## Core flow

```text
User / Agent Proposal
        ↓
Scope Sovereignty
Who, What, Where, How Long
        ↓
Reality Gate
Policy + firewall + safety check
        ↓
Agent Orchestration
CrewAI / LangGraph / HITL / tools
        ↓
Chronicle
Every event logged immutably
        ↓
Replay Service
Can the action be reconstructed?
        ↓
Witness Layer
Can another node reproduce it?
        ↓
Evidence Registry
Promote E0 → E5
        ↓
Governance Debt
Track any exception or unresolved gap
```

## Canonical components

### 1. Governance Debt Engine

Tracks every exception.

```text
Exception
→ Debt
→ Severity
→ Aging
→ Escalation
→ Resolution Receipt
→ Closure
```

Canonical files:

```text
cathedral_core/witness/governance_debt.py
cathedral_core/witness/debt_registry.py
cathedral_core/witness/debt_receipt.py
```

This is the highest-value first build because unresolved exceptions must never
disappear into narrative memory.

### 2. Evidence Registry

Tracks artifact maturity through QGS.

```text
E0_CLAIM
E1_SPEC
E2_IMPLEMENTED
E3_RECEIPTED
E4_REPLICATED
E5_AUDITED
```

`E5_PRODUCTION_BOUND` may exist as a backward-compatible code alias, but the
ratified semantic name is `E5_AUDITED`.

Canonical files:

```text
cathedral_core/witness/qgs.py
cathedral_core/witness/evidence_registry.py
cathedral_core/witness/evidence_promotion.py
```

No artifact should claim maturity without a QGS level and a recorded basis.

### 3. Chronicle

Immutable event memory.

Logs:

```text
proposal
scope decision
tool call
approval
rejection
debt event
replay result
witness result
evidence promotion
```

Canonical files:

```text
cathedral_core/chronicle/audit_log.py
cathedral_core/chronicle/receipt.py
```

Initial backend may be append-only local JSONL. ClickHouse can be used later for
analytics. Hash-chained receipts belong after the MVP test surface is stable.

### 4. Scope Sovereignty

Every action must answer:

```text
Who is acting?
What are they allowed to do?
Where may they do it?
How long is authority valid?
```

Canonical files:

```text
cathedral_core/lumen/scope_sovereignty.py
cathedral_core/lumen/scope_receipt.py
cathedral_core/lumen/policy_bundles/
```

This prevents authority leakage.

### 5. Replay Service

Traces are not enough. Replay requires:

```text
state snapshot
event stream
deterministic re-run
state equality check
```

Canonical files:

```text
cathedral_core/witness/replay_service.py
cathedral_core/witness/state_snapshot.py
cathedral_core/witness/replay_assert.py
```

Replay failure creates governance debt.

### 6. Witness Layer

Independent reproduction.

```text
Primary result
↓
Witness rerun
↓
Signed attestation
↓
QGS promotion
```

Canonical files:

```text
cathedral_core/witness/witness_node.py
cathedral_core/witness/witness_federation.py
cathedral_core/witness/witness_receipt.py
```

Rule:

```text
Witnesses attest.
Witnesses do not rule.
```

## Correct build order

Do not start with the full agent platform. Start with the receipt-bearing spine.

### Phase 1 — Foundation

```text
governance_debt.py
debt_registry.py
debt_receipt.py
evidence_registry.py
evidence_promotion.py
chronicle/audit_log.py
```

Goal: every claim, debt, and action has a place to land.

### Phase 2 — Scope

```text
scope_sovereignty.py
scope_receipt.py
basic OPA/Rego policies
```

Goal: no authority outside scope.

### Phase 3 — Replay

```text
replay_service.py
state_snapshot.py
replay_assert.py
```

Goal: original state equals replayed state.

### Phase 4 — Witness

```text
witness_node.py
witness_receipt.py
quorum rules
```

Goal: independent reproduction.

### Phase 5 — Agent Integration

```text
model router
AI firewall
LangGraph / CrewAI
HITL middleware
CI/CD red-team pipeline
```

Goal: powerful agents under constitutional governance.

## Key warnings

```text
LangSmith traces ≠ replay
Audit logs ≠ evidence
Human approval ≠ scoped authority
Witness agreement ≠ truth
Production-oriented ≠ production-ready
```

## Current repository mapping

The user-facing conceptual layout may be called `cathedral-ai/`, but this
repository is `Weaver_Os`. To avoid namespace collision with existing top-level
placeholder directories, new MVP implementation code should live under
`cathedral_core/` until the spine is stable.

```text
cathedral_core/
├── lumen/
│   ├── authority_fsm.py
│   ├── scope_sovereignty.py
│   ├── scope_receipt.py                # future
│   └── policy_bundles/                 # future
├── witness/
│   ├── governance_debt.py
│   ├── debt_registry.py                # future
│   ├── debt_receipt.py                 # future
│   ├── qgs.py
│   ├── evidence_registry.py
│   ├── evidence_promotion.py
│   ├── replay_service.py               # future
│   ├── state_snapshot.py               # future
│   ├── replay_assert.py                # future
│   ├── witness_node.py                 # future
│   ├── witness_federation.py           # future
│   └── witness_receipt.py              # future
├── chronicle/
│   ├── audit_log.py                    # future
│   └── receipt.py                      # future
└── agents/
    ├── router.py                       # future
    ├── ai_firewall.py                  # future
    ├── hitl.py                         # future
    └── tool_registry.py                # future
```

## Final status

```text
Architecture: strong
Governance design: strong
Evidence model: strong
Implementation: pending / partial MVP-0
Production readiness: not demonstrated
Next milestone: first receipt-bearing vertical slice
```

Bottom line:

```text
The architecture is ready. Build the spine that produces receipts.
```

No mechanism may silently convert uncertainty into authority.
