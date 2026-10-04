import Std
import LatticeCore.Models

namespace LatticeCore

def uneven (n : Nat) : Nat := if n = 1 then 1 else 0

theorem uneven_deflationary : Deflationary assuranceOrder.toOrder uneven := by
  intro n
  change (if n = 1 then 1 else 0) ≤ n
  split <;> omega

theorem uneven_not_monotone : ¬ Monotone assuranceOrder.toOrder uneven := by
  intro h
  have impossible := h (x := 1) (y := 2) (show 1 ≤ 2 from by decide)
  change 1 ≤ 0 at impossible
  omega

def decrement (n : Nat) : Nat := n - 1

theorem decrement_deflationary : Deflationary assuranceOrder.toOrder decrement :=
  fun n => Nat.sub_le n 1

theorem decrement_monotone : Monotone assuranceOrder.toOrder decrement := by
  intro x y h
  change x ≤ y at h
  change x - 1 ≤ y - 1
  omega

theorem decrement_not_idempotent : ¬ Idempotent decrement := by
  intro h
  have impossible := h 2
  change 0 = 1 at impossible
  contradiction

end LatticeCore
