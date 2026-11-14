import Core

namespace Weaver

-- These strengthen the frozen core without modifying its semantics.
theorem denied_preserves_state (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : check c r g = false) : step s (.execute c r g) = s := by
  simp [step, h]

theorem absent_grant_preserves_state (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : g ∉ s.grants) : step s (.execute c r g) = s := by
  simp [step, h]

theorem revoked_preserves_state (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : g.revoked = true) : step s (.execute c r g) = s := by
  exact denied_preserves_state s c r g (revoked_denied c r g h)

theorem expired_preserves_state (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : g.expires ≤ c.now) : step s (.execute c r g) = s := by
  exact denied_preserves_state s c r g (expired_denied c r g h)

-- Scope the trace to execution attempts with a failed policy check.
-- No evaluation events are included: those legitimately append receipts.
def DeniedAttempt : Event → Prop
  | .execute c r g => check c r g = false
  | .evaluate _ _ _ _ => False

theorem denied_attempt_preserves_state (s : State) (e : Event)
    (h : DeniedAttempt e) : step s e = s := by
  cases e with
  | evaluate b required observed failed => exact False.elim h
  | execute c r g => exact denied_preserves_state s c r g h

theorem denied_trace_preserves_state (es : List Event) (s : State)
    (h : ∀ e ∈ es, DeniedAttempt e) : replay s es = s := by
  induction es generalizing s with
  | nil => rfl
  | cons e es ih =>
      have he : step s e = s := denied_attempt_preserves_state s e (h e (by simp))
      simp only [replay, he]
      exact ih s (fun x hx => h x (by simp [hx]))

-- Equality preservation works for any pure observation, not just a hash.
-- This does not assume or prove that cryptographic hashes are injective.
theorem denied_observation_preserved {α : Type} (observe : State → α)
    (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : check c r g = false) :
    observe (step s (.execute c r g)) = observe s := by
  rw [denied_preserves_state s c r g h]

#print axioms denied_preserves_state
#print axioms absent_grant_preserves_state
#print axioms revoked_preserves_state
#print axioms expired_preserves_state
#print axioms denied_attempt_preserves_state
#print axioms denied_trace_preserves_state
#print axioms denied_observation_preserved

end Weaver
