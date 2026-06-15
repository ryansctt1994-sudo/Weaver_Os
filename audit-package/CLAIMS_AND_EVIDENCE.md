# Claims and Evidence Register

## Claim Register

| ID | Claim | Status | Evidence Source | Notes |
|---|---|---|---|---|
| C-001 | The architecture separates execution, evidence, and authority. | Locally supported | Constitution, three-chain model, invariants | Core constitutional claim. |
| C-002 | Canon-OS is a meaning-preservation system, not an authority system. | Design claim | Canon-OS model | Boundary claim. |
| C-003 | The evidence ladder distinguishes local verification from external validation. | Supported | Evidence ladder | Critical audit posture. |
| C-004 | Authority has not been earned. | Supported | Readiness assessment, missing independent validation | Negative claim. |
| C-005 | Production use is prohibited. | Supported | Status statements | Safety constraint. |
| C-006 | Replay exists as a bounded verification concept. | Locally supported | Chronicle/replay model | Partial. |
| C-007 | Witness independence is required for higher evidence levels. | Design claim | Witness model | Required for E4+. |
| C-008 | Challenge preservation retains rejected claims and objections. | Design claim | Challenge preservation section | Prevents lineage loss. |

## Evidence Matrix

| Evidence ID | Evidence Type | Description | Supports Claims | Current Status |
|---|---|---|---|---|
| E-001 | Constitution document | Core constitutional rules and separation principle. | C-001, C-004, C-005 | Local support |
| E-002 | META invariants | Non-collapse and non-promotion invariants. | C-001, C-003, C-004 | Local support |
| E-003 | Three-chain model | Execution/evidence/authority separation. | C-001, C-003 | Local support |
| E-004 | Canon-OS model | Meaning-preservation framework. | C-002 | Design support |
| E-005 | Evidence ladder | Promotion levels from concept to external audit. | C-003, C-007 | Design support |
| E-006 | Mock execution records | Internal execution evidence for replayable runs. | C-006 | Local support |
| E-007 | Theorem discharge summary | Formal verification evidence. | C-004, C-007 | Local support |
| E-008 | Integration test results | Local integration evidence. | C-001, C-004 | Local support |
| E-009 | Replay artifacts | Replay reports, logs, and manifests. | C-006 | Partial |
| E-010 | Challenge log | Rejected claims, failed tests, and falsification attempts. | C-008 | Partial |

## Reviewer rule

No claim may be promoted beyond its strongest available evidence level.
