/-! Explicit order laws; no bundled inference between map properties. -/
namespace LatticeCore

structure Order (α : Type u) where
  le : α → α → Prop
  refl : ∀ x, le x x
  trans : ∀ {x y z}, le x y → le y z → le x z
  antisymm : ∀ {x y}, le x y → le y x → x = y

structure MeetOrder (α : Type u) extends Order α where
  meet : α → α → α
  meet_le_left : ∀ x y, le (meet x y) x
  meet_le_right : ∀ x y, le (meet x y) y
  le_meet : ∀ {x y z}, le x y → le x z → le x (meet y z)

def Deflationary (o : Order α) (f : α → α) : Prop := ∀ x, o.le (f x) x
def Inflationary (o : Order α) (f : α → α) : Prop := ∀ x, o.le x (f x)
def Monotone (o : Order α) (f : α → α) : Prop :=
  ∀ {x y}, o.le x y → o.le (f x) (f y)
def Idempotent (f : α → α) : Prop := ∀ x, f (f x) = f x

theorem comp_deflationary (o : Order α) {f g : α → α}
    (hf : Deflationary o f) (hg : Deflationary o g) :
    Deflationary o (fun x => f (g x)) :=
  fun x => o.trans (hf (g x)) (hg x)

theorem comp_monotone (o : Order α) {f g : α → α}
    (hf : Monotone o f) (hg : Monotone o g) :
    Monotone o (fun x => f (g x)) := fun h => hf (hg h)

theorem comp_idempotent_of_commute {f g : α → α}
    (hf : Idempotent f) (hg : Idempotent g) (hfg : ∀ x, g (f x) = f (g x)) :
    Idempotent (fun x => f (g x)) := by
  intro x
  change f (g (f (g x))) = f (g x)
  rw [hfg, hf, hg]

def restrict (o : MeetOrder α) (ceiling : α) (x : α) : α := o.meet x ceiling

theorem restrict_deflationary (o : MeetOrder α) (c : α) :
    Deflationary o.toOrder (restrict o c) := fun x => o.meet_le_left x c

theorem restrict_monotone (o : MeetOrder α) (c : α) :
    Monotone o.toOrder (restrict o c) := by
  intro x y h
  exact o.le_meet (o.trans (o.meet_le_left x c) h) (o.meet_le_right x c)

theorem restrict_idempotent (o : MeetOrder α) (c : α) :
    Idempotent (restrict o c) := by
  intro x
  apply o.antisymm
  · exact o.meet_le_left (o.meet x c) c
  · exact o.le_meet (o.refl _) (o.meet_le_right x c)

end LatticeCore
