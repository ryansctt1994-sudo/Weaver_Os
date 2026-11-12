import WNSKernel.Core

namespace WNSKernel

variable {P : Type} {s : State P} {r : Receipt P} {g : Grant}
  {roots : List Nat} {p : Proposal} {now : Nat} {apply : P → Nat → P}

theorem replay_preserves_history (ps : List Proposal) (h : r ∈ s.history) :
    r ∈ (replay apply roots g now s ps).history := by
  induction ps generalizing s with
  | nil => exact h
  | cons p ps ih =>
    exact ih (history_preserved h)

theorem replay_preserves_grants (ps : List Proposal) :
    (replay apply roots g now s ps).grants = s.grants := by
  induction ps generalizing s with
  | nil => rfl
  | cons p ps ih =>
    exact ih (s := (step apply roots s p g now).1)

/-- Remove the exact stored grant. No modeled execution transition can reinsert it. -/
def revoke (s : State P) (g : Grant) : State P :=
  { s with grants := s.grants.filter (fun candidate => candidate != g) }

theorem revoked_membership_absent : g ∉ (revoke s g).grants := by
  simp [revoke]

theorem revoked_store_denied : ¬ Eligible roots (revoke s g) p g now := by
  intro e
  exact revoked_membership_absent e.1

theorem revocation_survives_execution (ps : List Proposal) :
    ¬ Eligible roots (replay apply roots g now (revoke s g) ps) p g now := by
  intro e
  have membership := e.1
  rw [replay_preserves_grants] at membership
  exact revoked_membership_absent membership

structure Knowledge where
  dependencies : List Nat
  current : Bool

variable {k : Knowledge} {source : Nat}

/-- Applies only to explicitly recorded direct dependencies. -/
def invalidate (k : Knowledge) (changedSource : Nat) : Knowledge :=
  if changedSource ∈ k.dependencies then { k with current := false } else k

theorem changed_dependency_stale (h : source ∈ k.dependencies) :
    (invalidate k source).current = false := by
  simp [invalidate, h]

theorem unrelated_source_preserves (h : source ∉ k.dependencies) :
    invalidate k source = k := by
  simp [invalidate, h]

theorem changed_knowledge_blocks_transition (k : Knowledge) (source : Nat)
    (h : source ∈ k.dependencies) :
    (step apply roots s { p with sourceCurrent := (invalidate k source).current }
      g now).1.protectedState = s.protectedState := by
  apply rejection_preserves
  apply stale_denied
  exact changed_dependency_stale h

end WNSKernel
