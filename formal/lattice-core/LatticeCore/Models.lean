import LatticeCore.Deflation

namespace LatticeCore

/-- Inclusion order over permission or observation predicates. -/
def predicateOrder (α : Type u) : Order (α → Prop) where
  le p q := ∀ x, p x → q x
  refl _ _ h := h
  trans h₁ h₂ x hx := h₂ x (h₁ x hx)
  antisymm h₁ h₂ := funext (fun x => propext ⟨h₁ x, h₂ x⟩)

def permissionOrder (α : Type u) : MeetOrder (α → Prop) where
  toOrder := predicateOrder α
  meet p q := fun x => p x ∧ q x
  meet_le_left _ _ _ h := h.1
  meet_le_right _ _ _ h := h.2
  le_meet h₁ h₂ x hx := ⟨h₁ x hx, h₂ x hx⟩

def attenuate (ceiling grants : α → Prop) : α → Prop :=
  restrict (permissionOrder α) ceiling grants

theorem permission_attenuation (ceiling : α → Prop) :
    Deflationary (predicateOrder α) (attenuate ceiling) :=
  restrict_deflationary (permissionOrder α) ceiling

def assuranceOrder : MeetOrder Nat where
  le := Nat.le
  refl := Nat.le_refl
  trans := Nat.le_trans
  antisymm := Nat.le_antisymm
  meet := Nat.min
  meet_le_left := Nat.min_le_left
  meet_le_right := Nat.min_le_right
  le_meet h₁ h₂ := Nat.le_min.mpr ⟨h₁, h₂⟩

/-- Smaller rungs mean weaker effective assurance, independently of evidence volume. -/
def constrainAssurance (dependency rating : Nat) : Nat :=
  restrict assuranceOrder dependency rating

theorem assurance_weakest_link (dependency : Nat) :
    Deflationary assuranceOrder.toOrder (constrainAssurance dependency) :=
  restrict_deflationary assuranceOrder dependency

/-- Information accumulates under inclusion, the opposite direction to attenuation. -/
def collect (observations information : α → Prop) : α → Prop :=
  fun x => information x ∨ observations x

theorem collect_inflationary (observations : α → Prop) :
    Inflationary (predicateOrder α) (collect observations) :=
  fun _ _ h => Or.inl h

theorem collect_monotone (observations : α → Prop) :
    Monotone (predicateOrder α) (collect observations) := by
  intro p q h x hx
  cases hx with
  | inl hp => exact Or.inl (h x hp)
  | inr ho => exact Or.inr ho

theorem collect_idempotent (observations : α → Prop) :
    Idempotent (collect observations) := by
  intro p
  funext x
  apply propext
  constructor
  · intro h
    cases h with
    | inl h => exact h
    | inr h => exact Or.inr h
  · intro h
    exact Or.inl h

end LatticeCore
