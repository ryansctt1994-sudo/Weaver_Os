import Mathlib
import WNSKernel.Core

/- EFMW-inspired residual instrumentation. The recurrence is conventional EWMA.
   Matthew Chenoweth Wright's physical interpretation is not assumed. -/
namespace WNSKernel.EFMW

def update (λ m r : ℝ) : ℝ := λ * m + (1 - λ) * r

def track (λ initial : ℝ) (residual : ℕ → ℝ) : ℕ → ℝ
  | 0 => initial
  | n + 1 => update λ (track λ initial residual n) (residual n)

theorem update_difference (λ a b r : ℝ) :
    update λ a r - update λ b r = λ * (a - b) := by
  unfold update
  ring

theorem update_constant_error (λ m r : ℝ) :
    update λ m r - r = λ * (m - r) := by
  unfold update
  ring

theorem update_interval (λ m r lo hi : ℝ)
    (h0 : 0 ≤ λ) (h1 : λ ≤ 1)
    (hm : lo ≤ m ∧ m ≤ hi) (hr : lo ≤ r ∧ r ≤ hi) :
    lo ≤ update λ m r ∧ update λ m r ≤ hi := by
  unfold update
  constructor <;> nlinarith [mul_nonneg h0 (sub_nonneg.mpr hm.1),
    mul_nonneg (sub_nonneg.mpr h1) (sub_nonneg.mpr hr.1),
    mul_nonneg h0 (sub_nonneg.mpr hm.2),
    mul_nonneg (sub_nonneg.mpr h1) (sub_nonneg.mpr hr.2)]

theorem update_bounded (λ m r B : ℝ)
    (h0 : 0 ≤ λ) (h1 : λ ≤ 1) (hm : |m| ≤ B) (hr : |r| ≤ B) :
    |update λ m r| ≤ B :=
  abs_le.mpr (update_interval λ m r (-B) B h0 h1 (abs_le.mp hm) (abs_le.mp hr))

theorem track_bounded (λ initial B : ℝ) (r : ℕ → ℝ)
    (h0 : 0 ≤ λ) (h1 : λ ≤ 1) (hi : |initial| ≤ B)
    (hr : ∀ n, |r n| ≤ B) :
    ∀ n, |track λ initial r n| ≤ B := by
  intro n
  induction n with
  | zero => exact hi
  | succ n ih => exact update_bounded λ _ _ B h0 h1 ih (hr n)

theorem initial_difference (λ a b : ℝ) (r : ℕ → ℝ) (n : ℕ) :
    track λ a r n - track λ b r n = λ ^ n * (a - b) := by
  induction n with
  | zero => simp [track]
  | succ n ih =>
    simp only [track, update_difference, ih, pow_succ]
    ring

theorem initial_distance (λ a b : ℝ) (r : ℕ → ℝ) (n : ℕ) (h0 : 0 ≤ λ) :
    |track λ a r n - track λ b r n| = λ ^ n * |a - b| := by
  rw [initial_difference, abs_mul, abs_of_nonneg (pow_nonneg h0 n)]

theorem constant_error (λ initial r : ℝ) (n : ℕ) :
    track λ initial (fun _ => r) n - r = λ ^ n * (initial - r) := by
  induction n with
  | zero => simp [track]
  | succ n ih =>
    simp only [track, update_constant_error, ih, pow_succ]
    ring

theorem constant_distance (λ initial r : ℝ) (n : ℕ) (h0 : 0 ≤ λ) :
    |track λ initial (fun _ => r) n - r| = λ ^ n * |initial - r| := by
  rw [constant_error, abs_mul, abs_of_nonneg (pow_nonneg h0 n)]

/-- A finite-horizon disturbance bound; both streams may vary arbitrarily. -/
theorem disturbance_bound (λ a b D E : ℝ) (r s : ℕ → ℝ)
    (h0 : 0 ≤ λ) (h1 : λ ≤ 1) (hi : |a-b| ≤ D)
    (hrs : ∀ n, |r n-s n| ≤ E) :
    ∀ n, |track λ a r n-track λ b s n| ≤
      λ^n * D + (1-λ^n) * E := by
  intro n
  induction n with
  | zero => simpa [track] using hi
  | succ n ih =>
    have identity : update λ (track λ a r n) (r n) -
        update λ (track λ b s n) (s n) =
        λ * (track λ a r n-track λ b s n) + (1-λ)*(r n-s n) := by
      unfold update
      ring
    simp only [track]
    rw [identity]
    calc
      _ ≤ |λ * (track λ a r n-track λ b s n)| + |(1-λ)*(r n-s n)| :=
        abs_add_le _ _
      _ = λ * |track λ a r n-track λ b s n| + (1-λ)*|r n-s n| := by
        rw [abs_mul, abs_mul, abs_of_nonneg h0,
          abs_of_nonneg (sub_nonneg.mpr h1)]
      _ ≤ λ * (λ^n*D+(1-λ^n)*E) + (1-λ)*E :=
        add_le_add (mul_le_mul_of_nonneg_left ih h0)
          (mul_le_mul_of_nonneg_left (hrs n) (sub_nonneg.mpr h1))
      _ = _ := by rw [pow_succ]; ring

/-- Monitor-only ingestion cannot execute or mint a grant. -/
def ingest {P : Type} (state : State P) (λ memory residual : ℝ) :
    State P × ℝ := (state, update λ memory residual)

theorem monitor_preserves_protected {P : Type} (state : State P) (λ m r : ℝ) :
    (ingest state λ m r).1.protectedState = state.protectedState := rfl

theorem monitor_preserves_grants {P : Type} (state : State P) (λ m r : ℝ) :
    (ingest state λ m r).1.grants = state.grants := rfl

theorem monitor_preserves_history {P : Type} (state : State P) (λ m r : ℝ) :
    (ingest state λ m r).1.history = state.history := rfl

theorem warning_without_grant_denied {P : Type} (state : State P)
    (roots : List Nat) (p : Proposal) (g : Grant) (now : Nat)
    (λ m r : ℝ) (empty : state.grants = []) :
    ¬ Eligible roots (ingest state λ m r).1 p g now :=
  empty_grants_denied empty

theorem warning_without_grant_preserves {P : Type} (state : State P)
    (roots : List Nat) (p : Proposal) (g : Grant) (now : Nat)
    (apply : P → Nat → P) (λ m r : ℝ) (empty : state.grants = []) :
    (step apply roots (ingest state λ m r).1 p g now).1.protectedState =
      state.protectedState := by
  exact rejection_preserves (warning_without_grant_denied state roots p g now λ m r empty)

end WNSKernel.EFMW
