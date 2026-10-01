# Integrated formal portfolio

This integration imports the exact Dragon source from d4a62be62a25c6de341f6145b98808ea25c446c3 and extends the durable/portfolio kernel from 21551a6a7d4e69d8db9ada4a33dd649fc8a8218b. Both libraries compile in one pinned Lean 4.19.0 build, with separate complete axiom audits.

CertifiedDrift computes bounded propagation and checks closure against every recorded edge. A theorem connects a successful closure check to coverage of every recorded transitive path from the changed seeds. Insufficient fuel yields an incomplete report whenever an outstanding outgoing dependency is detected. Absence-based eligibility requires completion; incomplete reports preserve protected state via the existing execution gate. Cycles and insufficient/sufficient fuel have checked examples.

This closes the previous conditional propagation connection: consumers can use a checked result rather than assume that their chosen fuel was adequate. It does not prove that one particular universal fuel bound always succeeds; insufficient runs safely deny absence-based eligibility. Coverage concerns the recorded graph, not unrecorded dependencies or empirical source accuracy. The algorithm can over-invalidate and does not establish freshness merely from absence of recorded changes.

The modeled Academy correction operation separately returns the unchanged execution state and the corrected insight. Its grants and protected state are proved unchanged; this is not a claim about arbitrary learning implementations.

Reproduce from formal/wns-kernel: lake build; lake env lean Audit.lean; lake env lean DragonAudit.lean. Dragon uses the bounded 64 MiB thread-stack setting in lakefile.toml. CI retains both build/axiom logs. This is formal-model integration, not a runtime refinement proof or an independent external witness.
