# Cross-host spine execution receipt

**Status:** BOUNDED EVIDENCE MECHANIC  
**Witness:** W0  
**Authority:** O0 WITHHELD  
**Production:** PROHIBITED

`tools/emit_spine_receipt.py` emits a machine-readable receipt for one
execution of the deterministic Weaver spine.

The receipt derives rather than trusts:

- authority-ledger digest;
- ordered chain head;
- bounded local authority-state digest;
- state-digest method;
- manifest self-digest.

It records both:

- `verified_commit` — the exact Git object actually checked out and executed;
- `source_head_sha` — the source branch head supplied separately by CI.

On pull-request workflows these may differ because GitHub can execute a
synthetic merge commit.

```text
PRSourceHead != VerifiedMergeCommit
```

That difference is preserved rather than collapsed.

## Remote CI classification

When executed by GitHub Actions, the receipt is classified:

```text
REMOTE_CI_SAME_ORIGIN
```

A successful remote CI receipt establishes only that the bounded mechanics
replayed on that hosted runner for the bound tested tree.

It does not establish an independent operator or independent witness:

```text
RemoteCIReplay != IndependentOperatorReproduction
CrossHostMechanics != E3.5
Witness = W0
Authority = O0_WITHHELD
Production = PROHIBITED
```

The workflow is `.github/workflows/cross-host-spine.yml` and uploads the raw
JSON receipt as a workflow artifact.

## Receipt integrity

The receipt contains `receipt_sha256`, computed over the canonical receipt
payload excluding that field.

That digest detects later receipt editing. It does not make the receipt true and
does not authenticate an independent witness.

```text
ReceiptDigest != Signature
Signature != Truth
```
