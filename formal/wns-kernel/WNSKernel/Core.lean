import Std

namespace WNSKernel

structure Grant where
  issuer : Nat
  subject : Nat
  scope : List Nat
  starts : Nat
  expires : Nat
  revoked : Bool
  deriving DecidableEq

structure Proposal where
  actor : Nat
  action : Nat
  evidenceValid : Bool
  sourceCurrent : Bool
  preconditions : Bool

inductive Verdict where
  | accept | reject
  deriving DecidableEq

structure Receipt (Protected : Type) where
  actor : Nat
  action : Nat
  verdict : Verdict
  before : Protected
  after : Protected

structure State (Protected : Type) where
  protectedState : Protected
  grants : List Grant
  history : List (Receipt Protected)

variable {P : Type} {g child parent : Grant} {roots : List Nat}
  {s : State P} {p : Proposal} {now action : Nat} {r : Receipt P}
  {apply : P → Nat → P} {ps xs ys : List Proposal}

def Grant.valid (roots : List Nat) (g : Grant) (p : Proposal) (now : Nat) : Prop :=
  g.issuer ∈ roots ∧ g.subject = p.actor ∧ p.action ∈ g.scope ∧
  g.starts ≤ now ∧ now < g.expires ∧ g.revoked = false

def Eligible (roots : List Nat) (s : State P) (p : Proposal) (g : Grant)
    (now : Nat) : Prop :=
  g ∈ s.grants ∧ g.valid roots p now ∧ p.evidenceValid = true ∧
  p.sourceCurrent = true ∧ p.preconditions = true

instance (roots : List Nat) (s : State P) (p : Proposal) (g : Grant) (now : Nat) :
    Decidable (Eligible roots s p g now) := by
  unfold Eligible Grant.valid
  infer_instance

/-- Audit state may change on rejection; protected state and stored grants do not. -/
def step (apply : P → Nat → P) (roots : List Nat) (s : State P)
    (p : Proposal) (g : Grant) (now : Nat) : State P × Receipt P :=
  let accepted := decide (Eligible roots s p g now)
  let after := if accepted then apply s.protectedState p.action else s.protectedState
  let r : Receipt P := ⟨p.actor, p.action,
    if accepted then .accept else .reject, s.protectedState, after⟩
  (⟨after, s.grants, s.history ++ [r]⟩, r)

theorem rejection_preserves (h : ¬ Eligible roots s p g now) :
    (step apply roots s p g now).1.protectedState = s.protectedState := by
  simp [step, h]

theorem rejected_verdict_preserves
    (h : (step apply roots s p g now).2.verdict = .reject) :
    (step apply roots s p g now).1.protectedState = s.protectedState := by
  by_cases eligible : Eligible roots s p g now
  · simp [step, eligible] at h
  · exact rejection_preserves eligible

theorem accepted_requires_eligibility
    (h : (step apply roots s p g now).2.verdict = .accept) :
    Eligible roots s p g now := by
  by_cases eligible : Eligible roots s p g now
  · exact eligible
  · simp [step, eligible] at h

theorem grants_preserved : (step apply roots s p g now).1.grants = s.grants := by
  rfl

theorem receipt_binds_before : (step apply roots s p g now).2.before = s.protectedState := by
  rfl

theorem receipt_binds_after :
    (step apply roots s p g now).2.after = (step apply roots s p g now).1.protectedState := by
  rfl

theorem receipt_binds_action : (step apply roots s p g now).2.action = p.action := by
  rfl

theorem receipt_recorded :
    (step apply roots s p g now).2 ∈ (step apply roots s p g now).1.history := by
  simp [step]

theorem history_preserved (h : r ∈ s.history) :
    r ∈ (step apply roots s p g now).1.history := by
  simp only [step, List.mem_append, List.mem_singleton]
  exact Or.inl h

theorem stale_denied (h : p.sourceCurrent = false) : ¬ Eligible roots s p g now := by
  intro e
  have current := e.2.2.2.1
  simp [h] at current

theorem empty_grants_denied (h : s.grants = []) : ¬ Eligible roots s p g now := by
  intro e
  have stored := e.1
  simp [h] at stored

theorem revoked_denied (h : g.revoked = true) : ¬ g.valid roots p now := by
  intro e
  have unrevoked := e.2.2.2.2.2
  simp [h] at unrevoked

theorem expired_denied (h : g.expires ≤ now) : ¬ g.valid roots p now := by
  intro e
  exact Nat.not_lt_of_ge h e.2.2.2.2.1

/-- Scope attenuation alone; validity and delegation provenance are separate obligations. -/
def Attenuates (child parent : Grant) : Prop :=
  ∀ action, action ∈ child.scope → action ∈ parent.scope

theorem delegated_scope_no_growth (h : Attenuates child parent)
    (a : action ∈ child.scope) : action ∈ parent.scope := h action a

/-- A seam preserves protected data but starts a new authority and audit context. -/
def seam (s : State P) : State P := ⟨s.protectedState, [], []⟩

theorem seam_has_no_authority : (seam s).grants = [] := rfl

theorem seam_denied : ¬ Eligible roots (seam s) p g now :=
  empty_grants_denied rfl

/-- Replay re-evaluates proposals under frozen roots, grants, time, and apply semantics. -/
def replay (apply : P → Nat → P) (roots : List Nat) (g : Grant) (now : Nat)
    (s : State P) (proposals : List Proposal) : State P :=
  proposals.foldl (fun state p => (step apply roots state p g now).1) s

theorem replay_cons :
    replay apply roots g now s (p :: ps) =
      replay apply roots g now (step apply roots s p g now).1 ps := rfl

theorem replay_append :
    replay apply roots g now s (xs ++ ys) =
      replay apply roots g now (replay apply roots g now s xs) ys := by
  simp [replay, List.foldl_append]

end WNSKernel
