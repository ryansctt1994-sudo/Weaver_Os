# Weekly Audit Loop

## Objective

Prevent registry drift, unsupported promotion, and concept duplication.

## Procedure

1. Review all outputs created during the week.
2. Group artifacts by type: code, document, schema, workflow, policy, receipt.
3. Compare new items against canonical invariants.
4. Identify unsupported claims and downgrade them if needed.
5. Identify stale artifacts and superseded claims.
6. List promotion candidates with missing requirements.
7. Refresh the fresh-session handoff.

## Audit categories

- VERIFIED
- LIKELY
- SPECULATIVE
- UNKNOWN
- PRESERVATION_ONLY
- IMPLEMENTATION_TARGET
- PROMOTION_CANDIDATE
- PROMOTED_BY_RECEIPT

## Success criteria

The registry becomes smaller, clearer, more accurate, and more useful. Expansion alone is not success.