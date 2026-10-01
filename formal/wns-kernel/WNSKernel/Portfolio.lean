import WNSKernel.Temporal
import WNSKernel.Delegation

namespace WNSKernel.Portfolio

structure Dependency where
  source : Nat
  revision : Nat

def current (dependencies : List Dependency) (revision : Nat → Nat) : Bool :=
  dependencies.all (fun d => d.revision == revision d.source)

theorem changed_dependency_not_current (ds : List Dependency) (revision : Nat → Nat)
    (d : Dependency) (member : d ∈ ds) (changed : d.revision ≠ revision d.source) :
    current ds revision = false := by
  cases h : current ds revision with
  | false => rfl
  | true =>
    have hc := (List.all_eq_true.mp h) d member
    have same : d.revision = revision d.source := by simpa using hc
    exact False.elim (changed same)

theorem matching_dependencies_current (ds : List Dependency) (revision : Nat → Nat)
    (h : ∀ d ∈ ds, d.revision = revision d.source) : current ds revision = true := by
  apply List.all_eq_true.mpr
  intro d member
  simp [h d member]

structure LearningEvent where
  failureId : Nat
  corrected : Bool
  deriving DecidableEq

structure Insight where
  supported : Bool
  challenged : Bool
  independentReplications : Nat
  unresolved : List Nat
  history : List LearningEvent

def insightEligible (i : Insight) : Bool :=
  i.supported && i.challenged && decide (2 ≤ i.independentReplications) &&
    decide (i.unresolved = [])

def recordFailure (i : Insight) (id : Nat) : Insight :=
  { i with unresolved := id :: i.unresolved, history := i.history ++ [⟨id, false⟩] }

def correctFailure (i : Insight) (id : Nat) : Insight :=
  { i with unresolved := i.unresolved.filter (fun n => n != id), history := i.history ++ [⟨id, true⟩] }

theorem unresolved_failure_denies (i : Insight) (id : Nat) (h : id ∈ i.unresolved) :
    insightEligible i = false := by
  have nonempty : i.unresolved ≠ [] := by
    intro empty
    simp [empty] at h
  simp [insightEligible, nonempty]

theorem recorded_failure_denies (i : Insight) (id : Nat) :
    insightEligible (recordFailure i id) = false := by
  simp [insightEligible, recordFailure]

theorem correction_preserves_history (i : Insight) (id : Nat) (e : LearningEvent)
    (h : e ∈ i.history) : e ∈ (correctFailure i id).history := by
  exact List.mem_append.mpr (Or.inl h)

theorem recording_preserves_history (i : Insight) (id : Nat) (e : LearningEvent)
    (h : e ∈ i.history) : e ∈ (recordFailure i id).history := by
  exact List.mem_append.mpr (Or.inl h)

theorem recorded_failure_survives_correction (i : Insight) (id : Nat) :
    (⟨id, false⟩ : LearningEvent) ∈ (correctFailure (recordFailure i id) id).history := by
  simp [correctFailure, recordFailure]

/-- Live validity is checked against an explicit store and time at every chain node. -/
def live (store : List Grant) (now : Nat) (g : BoundedGrant) : Bool :=
  decide (g.grant ∈ store) && decide (g.grant.starts ≤ now) &&
    decide (now < g.grant.expires) && !g.grant.revoked

def delegationCheck (child parent : BoundedGrant) : Bool :=
  (child.grant.issuer == parent.grant.subject) &&
  child.grant.scope.all (fun a => parent.grant.scope.contains a) &&
  decide (parent.grant.starts ≤ child.grant.starts) &&
  decide (child.grant.expires ≤ parent.grant.expires) &&
  decide (child.budget ≤ parent.budget) &&
  decide (child.remainingDepth + 1 ≤ parent.remainingDepth)

/-- Leaf first; a singleton terminates only at a trusted root. -/
def chainValid (roots : List Nat) (store : List Grant) (now : Nat) : List BoundedGrant → Bool
  | [] => false
  | [g] => live store now g && roots.contains g.grant.issuer
  | child :: parent :: rest =>
    live store now child && delegationCheck child parent &&
      chainValid roots store now (parent :: rest)

theorem empty_chain_denies (roots : List Nat) (store : List Grant) (now : Nat) :
    chainValid roots store now [] = false := rfl

theorem revoked_node_not_live (store : List Grant) (now : Nat) (g : BoundedGrant)
    (h : g.grant.revoked = true) : live store now g = false := by
  simp [live, h]

theorem absent_node_not_live (store : List Grant) (now : Nat) (g : BoundedGrant)
    (h : g.grant ∉ store) : live store now g = false := by
  simp [live, h]

theorem expired_node_not_live (store : List Grant) (now : Nat) (g : BoundedGrant)
    (h : g.grant.expires ≤ now) : live store now g = false := by
  simp [live, Nat.not_lt_of_ge h]

theorem invalid_parent_chain_denies (roots : List Nat) (store : List Grant) (now : Nat)
    (child parent : BoundedGrant) (rest : List BoundedGrant)
    (h : chainValid roots store now (parent :: rest) = false) :
    chainValid roots store now (child :: parent :: rest) = false := by
  simp [chainValid, h]

theorem both_true (a b : Bool) : (a && b) = true ↔ a = true ∧ b = true := by
  cases a <;> cases b <;> decide

theorem live_head_required (roots : List Nat) (store : List Grant) (now : Nat)
    (g : BoundedGrant) (rest : List BoundedGrant)
    (h : chainValid roots store now (g :: rest) = true) : live store now g = true := by
  cases rest with
  | nil => exact ((both_true _ _).mp h).1
  | cons parent tail => exact ((both_true _ _).mp ((both_true _ _).mp h).1).1

theorem chain_has_trusted_root (roots : List Nat) (store : List Grant) (now : Nat)
    (chain : List BoundedGrant) (h : chainValid roots store now chain = true) :
    ∃ g ∈ chain, g.grant.issuer ∈ roots := by
  induction chain with
  | nil => simp [chainValid] at h
  | cons g rest ih =>
    cases rest with
    | nil =>
      have hr := ((both_true _ _).mp h).2
      exact ⟨g, by simp, by simpa using hr⟩
    | cons parent tail =>
      have hp := ((both_true _ _).mp h).2
      obtain ⟨origin, member, trusted⟩ := ih hp
      exact ⟨origin, List.mem_cons.mpr (Or.inr member), trusted⟩

def governedProposal (p : Proposal) (ds : List Dependency) (revision : Nat → Nat)
    (i : Insight) (roots : List Nat) (store : List Grant) (now : Nat)
    (g : BoundedGrant) (ancestors : List BoundedGrant) : Proposal :=
  { p with sourceCurrent := p.sourceCurrent && current ds revision, preconditions := p.preconditions && insightEligible i &&
      chainValid roots store now (g :: ancestors) }

/-- The chain supplies root provenance; the core checks the selected leaf's actor and scope.
    The issuer passed to Core is local only and is never persisted as a trusted root. -/
def governedStep {P : Type} (apply : P → Nat → P) (roots : List Nat) (s : State P)
    (p : Proposal) (ds : List Dependency) (revision : Nat → Nat) (i : Insight)
    (g : BoundedGrant) (ancestors : List BoundedGrant) (now : Nat) :=
  step apply [g.grant.issuer] s
    (governedProposal p ds revision i roots s.grants now g ancestors) g.grant now

theorem preconditions_false_denies {P : Type} (roots : List Nat) (s : State P)
    (p : Proposal) (g : Grant) (now : Nat) (h : p.preconditions = false) :
    ¬ Eligible roots s p g now := by
  intro e
  have hp := e.2.2.2.2
  simp [h] at hp

theorem stale_dependency_preserves {P : Type} (apply : P → Nat → P)
    (roots : List Nat) (s : State P) (p : Proposal) (ds : List Dependency)
    (revision : Nat → Nat) (i : Insight) (g : BoundedGrant) (ancestors : List BoundedGrant)
    (now : Nat) (d : Dependency) (member : d ∈ ds) (changed : d.revision ≠ revision d.source) :
    (governedStep apply roots s p ds revision i g ancestors now).1.protectedState =
      s.protectedState := by
  apply rejection_preserves
  apply stale_denied
  simp [governedProposal, changed_dependency_not_current ds revision d member changed]

theorem failed_insight_preserves {P : Type} (apply : P → Nat → P)
    (roots : List Nat) (s : State P) (p : Proposal) (ds : List Dependency)
    (revision : Nat → Nat) (i : Insight) (g : BoundedGrant) (ancestors : List BoundedGrant)
    (now : Nat) (id : Nat) (failed : id ∈ i.unresolved) :
    (governedStep apply roots s p ds revision i g ancestors now).1.protectedState =
      s.protectedState := by
  apply rejection_preserves
  apply preconditions_false_denies
  simp [governedProposal, unresolved_failure_denies i id failed]

theorem invalid_chain_preserves {P : Type} (apply : P → Nat → P)
    (roots : List Nat) (s : State P) (p : Proposal) (ds : List Dependency)
    (revision : Nat → Nat) (i : Insight) (g : BoundedGrant) (ancestors : List BoundedGrant)
    (now : Nat) (invalid : chainValid roots s.grants now (g :: ancestors) = false) :
    (governedStep apply roots s p ds revision i g ancestors now).1.protectedState =
      s.protectedState := by
  apply rejection_preserves
  apply preconditions_false_denies
  simp [governedProposal, invalid]

theorem every_chain_node_live (roots : List Nat) (store : List Grant) (now : Nat)
    (chain : List BoundedGrant) (valid : chainValid roots store now chain = true)
    (node : BoundedGrant) (member : node ∈ chain) : live store now node = true := by
  induction chain with
  | nil => simp at member
  | cons head rest ih =>
    rcases List.mem_cons.mp member with same | tailMember
    · subst node
      exact live_head_required roots store now head rest valid
    · cases rest with
      | nil => simp at tailMember
      | cons parent tail =>
        exact ih ((both_true _ _).mp valid).2 tailMember

theorem revoked_ancestor_denies (roots : List Nat) (store : List Grant) (now : Nat)
    (chain : List BoundedGrant) (node : BoundedGrant) (member : node ∈ chain)
    (revoked : node.grant.revoked = true) : chainValid roots store now chain = false := by
  cases h : chainValid roots store now chain with
  | false => rfl
  | true =>
    have hl := every_chain_node_live roots store now chain h node member
    rw [revoked_node_not_live store now node revoked] at hl
    contradiction

def demoRoot : BoundedGrant := ⟨⟨0, 1, [7], 0, 10, false⟩, 10, 2⟩
def demoLeaf : BoundedGrant := ⟨⟨1, 2, [7], 1, 9, false⟩, 5, 1⟩
def demoState : State Nat := ⟨0, [demoRoot.grant, demoLeaf.grant], []⟩
def demoInsight : Insight := ⟨true, true, 2, [], []⟩
def demoProposal : Proposal := ⟨2, 7, true, true, true⟩

theorem delegated_acceptance_example :
    (governedStep (fun n _ => n + 1) [0] demoState demoProposal [⟨3, 1⟩]
      (fun _ => 1) demoInsight demoLeaf [demoRoot] 2).2.verdict = .accept := by decide

theorem failure_rejection_example :
    (governedStep (fun n _ => n + 1) [0] demoState demoProposal [⟨3, 1⟩]
      (fun _ => 1) (recordFailure demoInsight 42) demoLeaf [demoRoot] 2).2.verdict = .reject := by decide

end WNSKernel.Portfolio
