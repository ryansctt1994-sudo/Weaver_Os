import WNSKernel.Core

namespace WNSKernel

structure BoundedGrant where
  grant : Grant
  budget : Nat
  remainingDepth : Nat

def BoundedDelegation (child parent : BoundedGrant) : Prop :=
  child.grant.issuer = parent.grant.subject ∧
  Attenuates child.grant parent.grant ∧
  parent.grant.starts ≤ child.grant.starts ∧
  child.grant.expires ≤ parent.grant.expires ∧
  child.budget ≤ parent.budget ∧
  child.remainingDepth + 1 ≤ parent.remainingDepth

variable {child parent : BoundedGrant} {action now : Nat}

theorem delegation_budget_no_growth (h : BoundedDelegation child parent) :
    child.budget ≤ parent.budget := h.2.2.2.2.1

theorem delegation_depth_decreases (h : BoundedDelegation child parent) :
    child.remainingDepth < parent.remainingDepth := h.2.2.2.2.2

theorem delegation_window_contained (h : BoundedDelegation child parent)
    (start : child.grant.starts ≤ now) (finish : now < child.grant.expires) :
    parent.grant.starts ≤ now ∧ now < parent.grant.expires := by
  exact ⟨Nat.le_trans h.2.2.1 start, Nat.lt_of_lt_of_le finish h.2.2.2.1⟩

theorem delegation_action_contained (h : BoundedDelegation child parent)
    (member : action ∈ child.grant.scope) : action ∈ parent.grant.scope :=
  h.2.1 action member

/-- Recorded provenance is not cryptographic authenticity or live ancestor validity. -/
inductive GrantLineage (roots : List Nat) : BoundedGrant → Prop where
  | root (g : BoundedGrant) (trusted : g.grant.issuer ∈ roots) : GrantLineage roots g
  | child {parent child : BoundedGrant} (prior : GrantLineage roots parent)
      (bounded : BoundedDelegation child parent) : GrantLineage roots child

theorem lineage_has_trusted_origin (h : GrantLineage roots child) :
    ∃ origin : BoundedGrant, origin.grant.issuer ∈ roots := by
  induction h with
  | root g trusted => exact ⟨g, trusted⟩
  | child prior bounded ih => exact ih

end WNSKernel
