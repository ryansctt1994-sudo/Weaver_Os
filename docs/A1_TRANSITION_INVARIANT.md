# A1 executable transition invariant — candidate

**Status:** CANDIDATE · NOT FROZEN  
**Authority:** NONE  
**Production:** PROHIBITED

This slice turns two A1 freeze blockers into executable checks:

1. a transition certificate must bind the exact predecessor claim state and policy head;
2. scope coverage is an admissibility predicate and cannot substitute for evidential support.

## State rule

For a claim state such as the Elpis scientific tuple:

```text
(binding, mechanics, scientific_result, reproduction, scope, authority)
```

a certificate changes exactly one named coordinate.

```text
mechanics pass != scientific-result pass
independent replay != scope expansion
scope coverage != evidential support
evidence != authority
```

## Exact predecessor binding

The candidate validator hashes the entire current claim-state object and requires:

```text
certificate.predecessor_state_hash == hash(current_state)
certificate.policy_head == current_policy_head
```

A stale certificate is rejected with `STALE_PREDECESSOR`.

This is compare-and-swap style semantics: a certificate applies to one exact
predecessor, not to every future state that happens to carry the same label.

## Separate support and scope predicates

The validator receives these from outside the certificate:

- admissible support receipt IDs;
- admissible scope atoms;
- expected artifact bindings.

The certificate may reference those values but may not manufacture them.

A transition requires both:

```text
support_ids subset-of admissible_support_ids
requested_scope subset-of admissible_scope_atoms
```

Passing the scope check does not increase evidential support. Passing the support
check does not broaden scope.

## Scope drift rule

If the claim state contains a `scope` coordinate, any transition of a different
coordinate must request exactly that existing scope.

Therefore a reproduction transition cannot silently broaden experimental scope.

A scope transition is possible only as its own one-coordinate transition and
must request the exact proposed new scope.

## Current implementation

- `policy/claim_transition.py`
- `tests/test_claim_transition.py`

This is a bounded reference invariant. It is not yet the frozen Codex A1, a
portfolio-wide migration, or operational authority.
