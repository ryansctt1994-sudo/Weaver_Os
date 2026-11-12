# WF-001Y — Extended ZOREL / Delta controls for Weaver OS

**Status:** TEST-ONLY, DRAFT, DO NOT MERGE. E2 / W0 / O0 and V008 HOLD unchanged.
**Integration parent:** WF-001X PR #131; source baseline \`54b873de2179aed1da616dab9472d504af616015\`.
**Upstream pins:** ZOREL \`abd777e43906cd7bacbd210a5975665730446d2f\`, Delta-717 \`c0a84e44967f9206fecc601acd370b5d7642fa0a\`.

## Provenance and translation

- **ZOREL:** \`tests/test_replay.py\`, \`tests/test_witness.py\`, \`tests/test_admissibility.py\`. Reuse their attack questions: untrusted witness metadata, typed actor/operation identity, hash determinism and signature/authority non-escalation. Do **not** import ZOREL's grant or ledger authority.
- **Delta:** \`tests/guide/test_guide.py\` (tampered, missing, reordered, inserted, truncated, rewritten histories; invalid numeric input; simulated atomic-write failure; misleading APPROVED status). Execute corresponding scenarios on Weaver's actual \`ReceiptLedger\`, \`verify_snapshot\`, \`parse_strict\`, and V008 owner IPC. Do **not** import Delta's local ForensicLedger.
- **Weaver:** \`tests/fusion/test_upstream_replay_evidence.py\` and \`tests/isolation/test_fusion_owner_boundary.py\` contain new behavioral test ports, not copies of entire upstream suites.

## Required direct execution

\`\`\`sh
python -m pytest -q tests/fusion/test_upstream_replay_evidence.py
python -m pytest -q tests/fusion
sudo -E env "PATH=$PATH" WEAVER_REQUIRE_ISOLATION=1 \
  python -m pytest -q -p no:cacheprovider tests/isolation/test_fusion_owner_boundary.py
python -m tools.verify_all
\`\`\`

The existing hosted \`v008-isolation\` workflow executes \`tests/isolation\` as root with skip-as-failure enforcement. Confirm exact-head logs explicitly show new tests were collected and completed. Compare full-suite counts to the pinned previous head; do not call a queued workflow a pass.

## Non-claims

- A green hosted owner test establishes bounded cross-UID behavior for the configured fixture; it does not prove arbitrary attacker resistance, a fixed revocation/commit race, or independent witness custody.
- The Delta assessment is untrusted; the test deliberately tries to submit \`APPROVED\` metadata where a signed grant is required. Refusal must not be promoted to a universal theorem.
- Unanchored hashes do not prove history integrity. The external anchor in the tests is held inside the test process, not by an external witness.
- No production code or protected owner, grant, ledger, gate, signing or receipt implementation is modified.
- Test-only progress cannot close issue #1, promote E2/W0/O0, or release V008 HOLD.

## Evidence acceptance

Require actual pytest terminal summaries, isolated-owner results with skip enforcement, full verifier report, signed/source-pinned provenance if available, clean complete CI, and independent human review before any integration merge.
