import WNSKernel.Core

namespace WNSKernel.Drift

/-- Recorded edges point from a dependency to its dependent claim. -/
inductive Reach (edge : Nat → Nat → Prop) : Nat → Nat → Prop where
  | direct {source claim} : edge source claim → Reach edge source claim
  | extend {source middle claim} : Reach edge source middle → edge middle claim →
      Reach edge source claim

/-- Currentness requires matching revisions for every recorded transitive source. -/
def Current (edge : Nat → Nat → Prop) (observed actual : Nat → Nat) (claim : Nat) : Prop :=
  ∀ source, Reach edge source claim → observed source = actual source

theorem transitive_changed_source_denies (edge : Nat → Nat → Prop)
    (observed actual : Nat → Nat) (source claim : Nat) (path : Reach edge source claim)
    (changed : observed source ≠ actual source) : ¬ Current edge observed actual claim := by
  intro current
  exact changed (current source path)

theorem two_edge_drift (edge : Nat → Nat → Prop) (observed actual : Nat → Nat)
    (source middle claim : Nat) (first : edge source middle) (second : edge middle claim)
    (changed : observed source ≠ actual source) : ¬ Current edge observed actual claim := by
  exact transitive_changed_source_denies _ _ _ _ _ (.extend (.direct first) second) changed

/-- Any stale-set implementation closed under dependency edges propagates all recorded paths. -/
theorem closed_stale_set_propagates (edge : Nat → Nat → Prop) (stale : Nat → Prop)
    (closed : ∀ x y, stale x → edge x y → stale y) (source claim : Nat)
    (path : Reach edge source claim) (changed : stale source) : stale claim := by
  induction path with
  | direct h => exact closed _ _ changed h
  | extend prior h ih => exact closed _ _ ih h

/-- Executable bounded fixed-point expansion; fuel limits coverage, never asserts currentness. -/
def expand (edges : List (Nat × Nat)) (stale : List Nat) : List Nat :=
  stale ++ ((edges.filter (fun e => stale.contains e.1)).map Prod.snd)

def propagate (edges : List (Nat × Nat)) : Nat → List Nat → List Nat
  | 0, stale => stale
  | fuel + 1, stale => propagate edges fuel (expand edges stale)

theorem expansion_preserves_stale (edges : List (Nat × Nat)) (stale : List Nat)
    (id : Nat) (h : id ∈ stale) : id ∈ expand edges stale := by
  exact List.mem_append.mpr (Or.inl h)

theorem propagation_preserves_stale (edges : List (Nat × Nat)) (fuel : Nat)
    (stale : List Nat) (id : Nat) (h : id ∈ stale) : id ∈ propagate edges fuel stale := by
  induction fuel generalizing stale with
  | zero => exact h
  | succ n ih => exact ih _ (expansion_preserves_stale _ _ _ h)

theorem two_hop_executable_example :
    3 ∈ propagate [(1,2),(2,3)] 2 [1] := by decide

theorem insufficient_fuel_counterexample :
    3 ∉ propagate [(1,2),(2,3)] 1 [1] := by decide

end WNSKernel.Drift
