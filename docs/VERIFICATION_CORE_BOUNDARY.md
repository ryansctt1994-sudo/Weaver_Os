# One verification core; bounded companion evidence

Implementation routing clarification under PORTFOLIO_STATUS.md and existing
consolidation ownership rules. No new governance decision, evidence promotion,
retirement of historical artifacts, or architecture ratification is claimed.

| Repository | Route for new verification work | Existing evidence boundary |
| --- | --- | --- |
| Weaver_Os | Canonical contracts in packages/contracts, replay/runtime in packages/runtime, read-only verification in packages/verifier | Exact artifact and environment only; RC1 archive deferrals remain separate |
| Lumen | Legacy prototype/reference; route new shared verification work to Weaver_Os | Retain original provenance; legacy local E3/E4 labels do not promote portfolio state |
| Lumen-Nexus | Frozen architecture/specification and historical PG-001R reference; shared implementation lives in Weaver packages | R-level labels do not become E-level evidence; missing PG-001 history remains unresolved |
| cathedral-verified | Bounded Chronicle and RTL companion | Chronicle is distinct from Weaver's deferred RC1 Chronicle; simulation is not silicon |
| Weaver--Cathedral- | Isolated integration experiments | Integration does not inherit source evidence or production authority |

Use installed Weaver contracts/runtime/verifier packages for new integrations.
Do not build another authorization decision path in a companion repository.
Existing migrations and byte-identity/conformance checks remain in force. This
clarification does not replace incompatible historical APIs with untested shims.

Count one execution once, keyed by source snapshot digest, test/claim scope,
frozen environment identity and execution receipt identity. Mirroring an artifact,
copying a receipt or rerunning the same origin-controlled CI under another repo
name does not establish an additional independent witness. A fresh rerun is an
additional local attempt, not independent corroboration. Keep source and imported
artifacts linked; do not add their test counts as distinct verified properties.

The joint reproduction kit binds two distinct snapshots and one frozen userspace.
Its results retain per-command logs and exit codes. It never aggregates those
counts into an evidence tier. Witness independence requires external review;
self-signed operator metadata cannot admit itself.

Open: independent reproduction, board validation, review of remaining legacy
consumers, external Chronicle anchors, and VTK containment/second-verifier work.
O0 / production prohibited persists until explicit governance review of actual
evidence; completion of a checklist never automatically grants authority.
