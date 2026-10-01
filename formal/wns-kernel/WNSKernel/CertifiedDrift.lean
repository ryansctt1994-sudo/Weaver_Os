import WNSKernel.Drift
import WNSKernel.Portfolio

namespace WNSKernel.CertifiedDrift

structure Report where
  stale : List Nat
  complete : Bool

/-- A finite check covering every recorded dependency edge. -/
def closedCheck (edges : List (Nat × Nat)) (stale : List Nat) : Bool :=
  edges.all (fun e => decide (e.1 ∈ stale → e.2 ∈ stale))

def analyze (edges : List (Nat × Nat)) (fuel : Nat) (seeds : List Nat) : Report :=
  let result := Drift.propagate edges fuel seeds
  ⟨result, closedCheck edges result⟩

theorem checked_edge_closed (edges : List (Nat × Nat)) (stale : List Nat)
    (complete : closedCheck edges stale = true) (x y : Nat)
    (edge : (x, y) ∈ edges) (hx : x ∈ stale) : y ∈ stale := by
  have hc := (List.all_eq_true.mp complete) (x, y) edge
  have implication : x ∈ stale → y ∈ stale := by simpa using hc
  exact implication hx

theorem complete_report_covers_every_path (edges : List (Nat × Nat)) (fuel : Nat)
    (seeds : List Nat) (source claim : Nat)
    (complete : (analyze edges fuel seeds).complete = true)
    (changed : source ∈ seeds)
    (path : Drift.Reach (fun x y => (x, y) ∈ edges) source claim) :
    claim ∈ (analyze edges fuel seeds).stale := by
  apply Drift.closed_stale_set_propagates (fun x y => (x, y) ∈ edges)
    (fun x => x ∈ (analyze edges fuel seeds).stale)
  · intro x y hx edge
    exact checked_edge_closed edges _ complete x y edge hx
  · exact path
  · exact Drift.propagation_preserves_stale edges fuel seeds source changed

theorem seeds_preserved (edges : List (Nat × Nat)) (fuel : Nat) (seeds : List Nat)
    (source : Nat) (changed : source ∈ seeds) :
    source ∈ (analyze edges fuel seeds).stale :=
  Drift.propagation_preserves_stale edges fuel seeds source changed

/-- Only completed coverage may support absence-based eligibility. -/
def absenceEligible (report : Report) (claim : Nat) : Bool :=
  report.complete && decide (claim ∉ report.stale)

theorem incomplete_denies (report : Report) (claim : Nat)
    (h : report.complete = false) : absenceEligible report claim = false := by
  simp [absenceEligible, h]

theorem reached_claim_denies (edges : List (Nat × Nat)) (fuel : Nat) (seeds : List Nat)
    (source claim : Nat) (complete : (analyze edges fuel seeds).complete = true)
    (changed : source ∈ seeds)
    (path : Drift.Reach (fun x y => (x, y) ∈ edges) source claim) :
    absenceEligible (analyze edges fuel seeds) claim = false := by
  have stale := complete_report_covers_every_path edges fuel seeds source claim complete changed path
  simp [absenceEligible, stale]

theorem incomplete_preserves_protected {P : Type} (apply : P → Nat → P)
    (roots : List Nat) (s : WNSKernel.State P) (p : WNSKernel.Proposal)
    (g : WNSKernel.Grant) (now : Nat) (report : Report) (claim : Nat)
    (h : report.complete = false) :
    (WNSKernel.step apply roots s
      { p with preconditions := p.preconditions && absenceEligible report claim } g now).1.protectedState
      = s.protectedState := by
  apply WNSKernel.rejection_preserves
  apply WNSKernel.Portfolio.preconditions_false_denies
  simp [incomplete_denies report claim h]

theorem insufficient_fuel_reports_incomplete :
    (analyze [(1,2),(2,3)] 1 [1]).complete = false := by decide

theorem sufficient_example_reports_complete :
    (analyze [(1,2),(2,3)] 2 [1]).complete = true := by decide

theorem cyclic_example_complete :
    (analyze [(1,2),(2,1),(2,3)] 2 [1]).complete = true := by decide

/-- This correction operation changes only the separately held insight object. -/
def learningCorrection {P : Type} (s : WNSKernel.State P)
    (i : WNSKernel.Portfolio.Insight) (failure : Nat) :=
  (s, WNSKernel.Portfolio.correctFailure i failure)

theorem learning_correction_preserves_grants {P : Type} (s : WNSKernel.State P)
    (i : WNSKernel.Portfolio.Insight) (failure : Nat) :
    (learningCorrection s i failure).1.grants = s.grants := rfl

theorem learning_correction_preserves_protected {P : Type} (s : WNSKernel.State P)
    (i : WNSKernel.Portfolio.Insight) (failure : Nat) :
    (learningCorrection s i failure).1.protectedState = s.protectedState := rfl

end WNSKernel.CertifiedDrift
