import Mathlib

namespace CP8
def Adj (n a b : Nat) : Prop :=
  ∃ bit ∈ List.range n, Nat.xor a b = 2^bit

instance (n a b : Nat) : Decidable (Adj n a b) := by
  unfold Adj
  infer_instance

def Valid (n : Nat) (path : List Nat) : Prop :=
  path ≠ [] ∧ path.Nodup ∧ (∀ v ∈ path, v < 2^n) ∧
  (∀ i ∈ List.range path.length, ∀ j ∈ List.range path.length,
    (j = i+1 → Adj n (path.getD i 0) (path.getD j 0)) ∧
    (i+1 < j → ¬ Adj n (path.getD i 0) (path.getD j 0)))

instance (n : Nat) (path : List Nat) : Decidable (Valid n path) := by
  unfold Valid
  infer_instance

def check (n : Nat) (path : List Nat) : Bool := decide (Valid n path)

/-- Abstract validated import. Hash verification is a separate explicit Boolean gate. -/
def commit (n : Nat) (old candidate : List Nat) (sealValid : Bool) : List Nat :=
  if sealValid && check n candidate then candidate else old

theorem checker_sound (n : Nat) (path : List Nat) (h : check n path = true) :
    Valid n path := by simpa [check] using h

theorem checker_complete (n : Nat) (path : List Nat) (h : Valid n path) :
    check n path = true := by simp [check,h]

theorem invalid_preserves (n : Nat) (old candidate : List Nat)
    (sealOk : Bool) (h : ¬ Valid n candidate) : commit n old candidate sealOk = old := by
  simp [commit,check,h]

theorem invalid_seal_preserves (n : Nat) (old candidate : List Nat) :
    commit n old candidate false = old := by simp [commit]

theorem empty_denied (n : Nat) : check n [] = false := by
  simp [check,Valid]

theorem valid_has_no_revisits (n : Nat) (path : List Nat) (h : Valid n path) :
    path.Nodup := h.2.1

theorem valid_states_in_range (n : Nat) (path : List Nat)
    (h : Valid n path) (v : Nat) (hv : v ∈ path) : v < 2^n := h.2.2.1 v hv

theorem committed_valid (n : Nat) (old candidate : List Nat)
    (h : Valid n candidate) : commit n old candidate true = candidate := by
  simp [commit,check,h]

/-- An auxiliary score does not participate in structural validation. -/
def scoredCheck (n : Nat) (path : List Nat) (_score : Nat) : Bool := check n path

theorem score_cannot_change_verdict (n : Nat) (path : List Nat) (a b : Nat) :
    scoredCheck n path a = scoredCheck n path b := rfl

end CP8
