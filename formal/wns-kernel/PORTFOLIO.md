# Connected portfolio formal slice

NEXUS compares every recorded direct dependency revision to an explicit revision function. A mismatch forces sourceCurrent false. Unrecorded dependencies and the accuracy of the revision function remain caller obligations.

ACADEMY requires support, completed challenge, at least two recorded independent replications, and no unresolved failures. Independence is an input assertion, not established by counting. Recording or correcting failures appends an event; correction preserves the original failure record. Eligibility does not establish empirical truth.

COMMONS validates leaf-first chains against the live grant store and fixed time. Every node must be stored, unrevoked and within its validity window. Each edge checks issuer/subject binding, scope, time, budget and depth attenuation. The terminal issuer must belong to the explicit trusted roots. Invalid parent chains cascade to denial. Provenance is structural; signatures, root selection and store authenticity are outside this model.

The composed governedStep uses the existing Core transition and separately gates current sources, insight eligibility and live chain validity. Delegated leaf issuers are admitted only to the local Core call; they are not added to persisted roots. Three theorems establish protected-state preservation for a stale dependency, unresolved failure, or invalid chain. Receipts still bind the resulting Core transition.

Run `lake build` and `lake env lean Audit.lean` from formal/wns-kernel using the pinned toolchain. This formal model is not a refinement proof of the Python runtime or evidence of Academy effectiveness. Independent reproduction remains outstanding.
