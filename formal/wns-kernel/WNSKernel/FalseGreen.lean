import Std

namespace WNSKernel.FalseGreen

/-- A concrete lossy commitment, not an attack on SHA-256. -/
def commitment (n : Nat) := n % 2

theorem equal_commitments_distinct_states :
    commitment 0 = commitment 2 ∧ (0 : Nat) ≠ 2 := by
  decide

structure Report where
  authenticated : Bool
  worldClaimTrue : Bool

theorem authenticated_does_not_establish_truth :
    ∃ r : Report, r.authenticated = true ∧ r.worldClaimTrue = false := by
  exact ⟨⟨true, false⟩, rfl, rfl⟩

structure TestRun where
  exitCode : Nat
  checksExecuted : Nat

theorem zero_exit_can_execute_no_checks :
    ∃ r : TestRun, r.exitCode = 0 ∧ r.checksExecuted = 0 := by
  exact ⟨⟨0, 0⟩, rfl, rfl⟩

structure Emergency where
  eligible : Bool
  authorityGranted : Bool

theorem eligibility_without_authority :
    ∃ e : Emergency, e.eligible = true ∧ e.authorityGranted = false := by
  exact ⟨⟨true, false⟩, rfl, rfl⟩

end WNSKernel.FalseGreen
