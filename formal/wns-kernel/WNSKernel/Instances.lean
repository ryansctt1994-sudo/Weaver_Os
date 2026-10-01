import WNSKernel.Core

namespace WNSKernel

def rootGrant : Grant := ⟨0, 1, [7], 0, 10, false⟩
def good : Proposal := ⟨1, 7, true, true, true⟩
def selfProposal : Proposal := ⟨9, 7, true, true, true⟩
def initial : State Nat := ⟨0, [rootGrant], []⟩
def increment (n _action : Nat) := n + 1

theorem weaver_accepts :
    (step increment [0] initial good rootGrant 1).1.protected = 1 := by
  decide

theorem weaver_rejects_self_proposal :
    (step increment [0] initial selfProposal rootGrant 1).1.protected = 0 := by
  decide

/-- A routing edge is separate from the grant store. -/
def commonsRouting : List (Nat × Nat) := [(9, 1)]

theorem commons_route_without_authority :
    (9, 1) ∈ commonsRouting ∧
    ¬ Eligible [0] initial selfProposal rootGrant 1 := by
  decide

theorem copied_state_requires_regrant :
    (step increment [0] (seam initial) good rootGrant 1).1.protected = 0 := by
  decide

theorem evidence_without_grant_denied :
    good.evidenceValid = true ∧ ¬ Eligible [0] (seam initial) good rootGrant 1 := by
  decide

end WNSKernel
