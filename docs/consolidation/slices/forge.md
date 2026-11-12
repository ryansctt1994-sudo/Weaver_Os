# FORGE split — review-only source custody

**From combined reference:** `f65fa54c56341a8d5508af728fc773055afa1cd2` (PR #135).  **Base:** `de15972b4fc29ec0a21f521ccf641946270ffcbf` (PR #134). **Source files copied by exact Git blob SHA.**

**Limit:** Contributor templates and donor license notices only. These remain reference documents, not acceptance receipts or witness certification.

This branch intentionally omits unrelated combined integration assets and eight donor ZIPs. Licenses and original donor revisions are retained in the upstream source manifest of PR #135; source-file attribution is shown below. No independent witness is established.

## Selected files and source metadata

| Path | Donor/source revision | Expected SHA-256 (or integration identity) |
| --- | --- | --- |
| `docs/consolidation/forge/CONTRIBUTING.md` | `4df6b98cd5d5` | `1b7ca79f3292d08e5f429c3f1a88fe785aae1f2e85fd2ce4fe0dc786d4c6a1fd` |
| `docs/consolidation/forge/RECEIPT_TEMPLATE.md` | `4df6b98cd5d5` | `b5c366f616b5caef2916e8ddb57fa7722ce6dfdc21c177ed640fa9100652f310` |
| `docs/consolidation/forge/RUNBOOK.md` | `4df6b98cd5d5` | `4c4978ac0f6e233db07c8c5c3bbd001ad88ac4183e5a5eaac894da8d7e203f19` |
| `docs/consolidation/forge/WITNESS_REVIEW_TEMPLATE.md` | `4df6b98cd5d5` | `c5501b0ea1f2d41aea20b018c1e4229837c37c79af45a108b26e713c9bc49dfb` |
| `docs/consolidation/licenses/cathedral-verified.txt` | `1c4181714b48` | `97b3af70c8e3e83d46dac823681f443b55456a30c3b0e63b6ada280bf31d7bac` |
| `docs/consolidation/licenses/weaver-cathedral.txt` | `2d905e6771cf` | `97b3af70c8e3e83d46dac823681f443b55456a30c3b0e63b6ada280bf31d7bac` |
| `docs/consolidation/licenses/weavers-forge.txt` | `3585019f3ab8` | `97b3af70c8e3e83d46dac823681f443b55456a30c3b0e63b6ada280bf31d7bac` |

## Execution required before any acceptance

```sh
python -m tools.verify_all
python -m tools.check_trust_domains
```

Check exact-head logs and negative-control results. Source copy is not equivalent to executed tests. No production/authority promotion or merger is implied.

**E2 / W0 / O0 · V008 HOLD · DO NOT MERGE.**
