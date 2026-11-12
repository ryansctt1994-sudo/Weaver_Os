# FINDINGS split — review-only source custody

**From combined reference:** `f65fa54c56341a8d5508af728fc773055afa1cd2` (PR #135).  **Base:** `de15972b4fc29ec0a21f521ccf641946270ffcbf` (PR #134). **Source files copied by exact Git blob SHA.**

**Limit:** Repeat-observation comparisons and typed differences only. A CONFIRMED finding is never a signed grant, independent witness or execution permission.

This branch intentionally omits unrelated combined integration assets and eight donor ZIPs. Licenses and original donor revisions are retained in the upstream source manifest of PR #135; source-file attribution is shown below. No independent witness is established.

## Selected files and source metadata

| Path | Donor/source revision | Expected SHA-256 (or integration identity) |
| --- | --- | --- |
| `tests/consolidation/__init__.py` | #135 integration-only | Git blob pinned to `f65fa54c5634` |
| `tests/consolidation/test_findings.py` | `bb17b6ae4caa` | `96c4c90b6cbce4bc9a8f16a833b7d3de0047d91fe5894a7288b4dc83af154823` |
| `tools/consolidation/__init__.py` | #135 integration-only | Git blob pinned to `f65fa54c5634` |
| `tools/consolidation/findings.py` | `bb17b6ae4caa` | `da4f028749b71a536776a03deac6a715b32c7e77ef1a0521b73155a8bde8ef30` |

## Execution required before any acceptance

```sh
python -m pytest -q tests/consolidation/test_findings.py
python -m tools.verify_all
```

Check exact-head logs and negative-control results. Source copy is not equivalent to executed tests. No production/authority promotion or merger is implied.

**E2 / W0 / O0 · V008 HOLD · DO NOT MERGE.**
