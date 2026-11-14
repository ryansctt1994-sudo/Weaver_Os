import Std

/- Weaver Formal Core v0.1: reference semantics, not a proof of existing Python.
   Nat identities are exact abstract identifiers, not claims of hash injectivity.
   Grant issuance/authenticity and trustworthy time are outside this model. -/
namespace Weaver

inductive Verdict where
  | pass
  | fail
  | insufficient (missing : List Nat)
  deriving DecidableEq, Repr

structure Binding where
  artifact : Nat
  policy : Nat
  experiment : Nat
  action : Nat
  deriving DecidableEq, Repr

structure Receipt where
  binding : Binding
  verdict : Verdict
  deriving DecidableEq, Repr

-- A concrete tagged wire representation. This is not JSON or cryptography.
def encode (r : Receipt) : Binding × Nat × List Nat :=
  match r.verdict with
  | .pass => (r.binding, 0, [])
  | .fail => (r.binding, 1, [])
  | .insufficient xs => (r.binding, 2, xs)

def decode (w : Binding × Nat × List Nat) : Option Receipt :=
  match w with
  | (b, 0, []) => some ⟨b, .pass⟩
  | (b, 1, []) => some ⟨b, .fail⟩
  | (b, 2, xs) => some ⟨b, .insufficient xs⟩
  | _ => none

theorem receipt_roundtrip (r : Receipt) : decode (encode r) = some r := by
  cases r with
  | mk b v => cases v <;> rfl

theorem insufficient_preserved (b : Binding) (xs : List Nat) :
    decode (encode ⟨b, .insufficient xs⟩) = some ⟨b, .insufficient xs⟩ := by
  rfl

structure Grant where
  binding : Binding
  epoch : Nat
  expires : Nat
  revoked : Bool
  deriving DecidableEq, Repr

structure Context where
  binding : Binding
  epoch : Nat
  now : Nat
  deriving DecidableEq, Repr

-- Declarative consumption policy, distinct from the executable Boolean checker.
def Authorized (c : Context) (r : Receipt) (g : Grant) : Prop :=
  r.binding = c.binding ∧ r.verdict = .pass ∧
  g.binding = c.binding ∧ g.epoch = c.epoch ∧
  c.now < g.expires ∧ g.revoked = false

def check (c : Context) (r : Receipt) (g : Grant) : Bool :=
  decide (r.binding = c.binding) && decide (r.verdict = .pass) &&
  decide (g.binding = c.binding) && decide (g.epoch = c.epoch) &&
  decide (c.now < g.expires) && !g.revoked

theorem check_correct (c : Context) (r : Receipt) (g : Grant) :
    check c r g = true ↔ Authorized c r g := by
  simp [check, Authorized, Bool.and_eq_true, and_assoc]

theorem insufficient_denied (c : Context) (b : Binding) (xs : List Nat) (g : Grant) :
    check c ⟨b, .insufficient xs⟩ g = false := by
  simp [check]

theorem revoked_denied (c : Context) (r : Receipt) (g : Grant)
    (h : g.revoked = true) : check c r g = false := by
  simp [check, h]

theorem expired_denied (c : Context) (r : Receipt) (g : Grant)
    (h : g.expires ≤ c.now) : check c r g = false := by
  simp [check, Nat.not_lt.mpr h]

theorem binding_denied (c : Context) (r : Receipt) (g : Grant)
    (h : r.binding ≠ c.binding) : check c r g = false := by
  simp [check, h]

structure State where
  grants : List Grant
  receipts : List Receipt
  executed : List Binding
  deriving DecidableEq, Repr

-- Evidence identifiers are supplied by a trusted adapter; presence is not truth.
def evaluate (binding : Binding) (required observed : List Nat) (failed : Bool) : Receipt :=
  let missing := required.filter (fun id => !(observed.contains id))
  ⟨binding, if failed then .fail else if missing = [] then .pass else .insufficient missing⟩

theorem evaluate_missing (b : Binding) (required observed : List Nat)
    (h : required.filter (fun id => !(observed.contains id)) ≠ []) :
    (evaluate b required observed false).verdict =
      .insufficient (required.filter (fun id => !(observed.contains id))) := by
  change (if required.filter (fun id => !(observed.contains id)) = [] then Verdict.pass
    else Verdict.insufficient (required.filter (fun id => !(observed.contains id)))) = _
  exact if_neg h

inductive Event where
  | evaluate (binding : Binding) (required observed : List Nat) (failed : Bool)
  | execute (context : Context) (receipt : Receipt) (grant : Grant)
  deriving DecidableEq, Repr

-- No grant issuance operation in this kernel. Execution requires membership
-- in the supplied state, a matching recorded receipt, and current policy checks.
def step (s : State) : Event → State
  | .evaluate b required observed failed =>
      { s with receipts := s.receipts ++ [evaluate b required observed failed] }
  | .execute c r g =>
      if g ∈ s.grants ∧ r ∈ s.receipts ∧ check c r g = true then
        { s with executed := s.executed ++ [c.binding] }
      else s

def replay (s : State) : List Event → State
  | [] => s
  | e :: es => replay (step s e) es

theorem step_preserves_authority (s : State) (e : Event) :
    (step s e).grants = s.grants := by
  cases e with
  | evaluate b required observed failed => rfl
  | execute c r g => simp only [step]; split <;> rfl

theorem replay_preserves_authority (es : List Event) (s : State) :
    (replay s es).grants = s.grants := by
  induction es generalizing s with
  | nil => rfl
  | cons e es ih =>
      exact (ih (step s e)).trans (step_preserves_authority s e)

theorem replay_append (xs ys : List Event) (s : State) :
    replay s (xs ++ ys) = replay (replay s xs) ys := by
  induction xs generalizing s with
  | nil => rfl
  | cons e es ih => exact ih (step s e)

theorem execution_sound (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : (step s (.execute c r g)).executed ≠ s.executed) :
    g ∈ s.grants ∧ r ∈ s.receipts ∧ Authorized c r g := by
  simp only [step] at h
  split at h
  next hgate => exact ⟨hgate.1, hgate.2.1, (check_correct c r g).mp hgate.2.2⟩
  next => exact False.elim (h rfl)

theorem empty_ledger_denied (s : State) (c : Context) (r : Receipt) (g : Grant)
    (h : s.receipts = []) : step s (.execute c r g) = s := by
  simp [step, h]

-- Dependency semantics: alternatives are OR; each support set is AND.
-- This version takes already-expanded leaf evidence dependencies; it does not
-- compute transitive closure over arbitrary cyclic claim graphs.
abbrev Supports := List (List Nat)
def Supported (supports : Supports) (valid : Nat → Prop) : Prop :=
  ∃ path ∈ supports, ∀ e ∈ path, valid e

def invalidate (bad : Nat) (valid : Nat → Prop) : Nat → Prop :=
  fun e => valid e ∧ e ≠ bad

theorem invalidation_no_promotion (supports : Supports) (valid : Nat → Prop) (bad : Nat) :
    Supported supports (invalidate bad valid) → Supported supports valid := by
  rintro ⟨path, hp, hv⟩
  exact ⟨path, hp, fun e he => (hv e he).1⟩

theorem unrelated_support_unchanged (supports : Supports) (valid : Nat → Prop) (bad : Nat)
    (hscope : ∀ path ∈ supports, bad ∉ path) :
    Supported supports (invalidate bad valid) ↔ Supported supports valid := by
  constructor
  · exact invalidation_no_promotion supports valid bad
  · rintro ⟨path, hp, hv⟩
    refine ⟨path, hp, ?_⟩
    intro e he
    refine ⟨hv e he, ?_⟩
    intro eq
    subst e
    exact hscope path hp he

theorem surviving_alternative (supports : Supports) (valid : Nat → Prop) (bad : Nat)
    (path : List Nat) (hp : path ∈ supports) (hv : ∀ e ∈ path, valid e)
    (hb : bad ∉ path) : Supported supports (invalidate bad valid) := by
  refine ⟨path, hp, ?_⟩
  intro e he
  refine ⟨hv e he, ?_⟩
  intro eq
  subst e
  exact hb he

theorem required_dependency_invalidates (supports : Supports) (valid : Nat → Prop) (bad : Nat)
    (hrequired : ∀ path ∈ supports, bad ∈ path) :
    ¬ Supported supports (invalidate bad valid) := by
  rintro ⟨path, hp, hv⟩
  exact (hv bad (hrequired path hp)).2 rfl

-- Executed kernel-checked examples; these are not empirical AI claims.
def b : Binding := ⟨1, 2, 3, 4⟩
def c : Context := ⟨b, 7, 10⟩
def r : Receipt := ⟨b, .pass⟩
def g : Grant := ⟨b, 7, 20, false⟩
example : check c r g = true := by decide
example : check c r { g with revoked := true } = false := by decide
example : check { c with now := 20 } r g = false := by decide
example : check { c with epoch := 8 } r g = false := by decide
example : check { c with binding := { b with experiment := 99 } } r g = false := by decide
example : decode (b, 99, []) = none := by decide
example : decode (b, 0, [1]) = none := by decide
example : (replay ⟨[g], [], []⟩ [.evaluate b [1] [1] false, .execute c r g]).executed = [b] := by decide
example : (replay ⟨[g], [], []⟩ [.execute c r g]).executed = [] := by decide
example : (replay ⟨[g], [], []⟩ [.evaluate b [1] [] false, .execute c r g]).executed = [] := by decide

#print axioms receipt_roundtrip
#print axioms evaluate_missing
#print axioms insufficient_preserved
#print axioms check_correct
#print axioms insufficient_denied
#print axioms revoked_denied
#print axioms expired_denied
#print axioms binding_denied
#print axioms step_preserves_authority
#print axioms replay_preserves_authority
#print axioms replay_append
#print axioms execution_sound
#print axioms empty_ledger_denied
#print axioms invalidation_no_promotion
#print axioms unrelated_support_unchanged
#print axioms surviving_alternative
#print axioms required_dependency_invalidates

end Weaver
