# WC-4R-001 — Four-repository test consolidation experiment

**Status:** REVIEW-ONLY, NO CODE IMPORTS, NO PROMOTION.  
**Source pins:** `catalog.json` (2026-11-13).  
**Authority:** O0 WITHHELD. **Production:** PROHIBITED.

## Owners

| Canonical owner | Responsibility |
| --- | --- |
| `Weaver_Os` | Contracts, authorization, receipt and replay verification |
| `Assurance-Lab` | Finite-state, adversarial, mutation and negative-control evaluation |
| `Alpha-OmegaLeanTeam` | Lean theorem registry, mutation oracle, proof replay and refinement obligations |
| `Weaver--Cathedral-` | Isolated integrations, agent adapters, hardware simulation and VGI-M1 prototype |

**Eighteen families are review candidates, not imported tests.** Source repositories, forks, licenses and their history remain unchanged. A single family can contain more than one concrete test; catalog family counts must never be confused with pytest counts.

## Test → Fix → Validate cycle

1. **SELECT:** pin source repository, SHA, license, exact original test names and expected behavior. Capture original failures and negative controls; record as historical references, not fresh passes.
2. **REPRODUCE:** run the original test on the pinned source and record a fresh event (PASS, FAIL, BLOCKED, INCONCLUSIVE or SKIP). Never use a green workflow as an uncounted proxy for all tests.
3. **FIX:** create a review-only branch in the owner repo. Preserve before/after hashes, record a failed baseline before claiming a repair.
4. **VALIDATE:** run the exact test on the candidate HEAD, include a regression that fails on the original defect, and record a separate event with `repair_of` referencing the prior FAIL.
5. **VERIFY:** rerun in a clean environment and independently review if promoting the evidence tier. A distinct model on the same owner-controlled CI is not an independent witness.
6. **DECIDE:** human review may accept/reject the PR. Tests and receipts never grant execution authority automatically.

## Counting rules

`catalog.json` contains **18 candidate families**. `events.jsonl` starts empty: **0 fresh attempts, 0 fresh passes, 0 fresh failures, 0 validated repairs**. Do not import historical counts into that stream. Each JSONL event is a distinct *attempt*; its candidate is one family, not necessarily one assertion or test case.

Example of a future event, **NOT EXECUTED**:

```json
{"event_id":"example-001","candidate_id":"CATHEDRAL-GATE","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","environment":"ubuntu-py311","outcome":"FAIL","evidence_class":"OWNER_CI","receipt_url":"https://example.org/receipt"}
```

A repair is a new **PASS** event with `repair_of: "example-001"` for the same candidate. The historic FAIL remains in the log. `validated_repair_passes` counts repair *attempts* with recorded positive results, not unique vulnerabilities fixed or independently verified repairs. Unique latest-case results are reported separately.

Run:

```sh
python governance/consolidation-v0.1/ledger.py --self-test
python governance/consolidation-v0.1/ledger.py
```

The validator refuses invalid identifiers, unsupported outcomes, duplicate event IDs, malformed SHA values and unsupported repair references. The CI check establishes only internal schema/logic behavior. It does not reproduce donor tests or establish secure append-only storage: Git history and branch controls are separate custody concerns.

## Promotion protections

- The only canonical authority anchor remains `Weaver_Os`; this catalog does not ratify a new architecture.
- No automatically generated number raises evidence, witness, security or operational authority level.
- A source test moved into an owner repository must retain attribution and license permissions.
- Do not count source tests and mirrored tests twice as independent corroboration.
- If a test is unable to execute because of missing hardware, dependencies or permissions, use BLOCKED or INCONCLUSIVE, never PASS.
- Evidence claiming non-origin reproduction needs independently authenticated execution and custody; `EXTERNAL_REPORTED` is a metadata label, not verification.
- VGI-M1 is a new specified acceptance suite, not an already passing package.
