import Mathlib
import WNSKernel.Core

/- EFMW-inspired residual instrumentation. The recurrence is conventional EWMA.
   Matthew Chenoweth Wright's physical interpretation is not assumed. -/
namespace WNSKernel.EFMW

noncomputable section

def update (weight m r : ℝ) : ℝ := weight * m + (1 - weight) * r

def track (weight initial : ℝ) (residual : ℕ → ℝ) : ℕ → ℝ
  | 0 => initial
  | n + 1 => update weight (track weight initial residual n) (residual n)

theorem update_difference (weight a b r : ℝ) :
    update weight a r - update weight b r = weight * (a - b) := by
  unfold update
  ring

theorem update_constant_error (weight m r : ℝ) :
    update weight m r - r = weight * (m - r) := by
  unfold update
  ring

theorem update_interval (weight m r lo hi : ℝ)
    (h0 : 0 ≤ weight) (h1 : weight ≤ 1)
    (hm : lo ≤ m ∧ m ≤ hi) (hr : lo ≤ r ∧ r ≤ hi) :
    lo ≤ update weight m r ∧ update weight m r ≤ hi := by
  unfold update
  constructor <;> nlinarith [mul_nonneg h0 (sub_nonneg.mpr hm.1),
    mul_nonneg (sub_nonneg.mpr h1) (sub_nonneg.mpr hr.1),
    mul_nonneg h0 (sub_nonneg.mpr hm.2),
    mul_nonneg (sub_nonneg.mpr h1) (sub_nonneg.mpr hr.2)]

theorem update_bounded (weight m r B : ℝ)
    (h0 : 0 ≤ weight) (h1 : weight ≤ 1) (hm : |m| ≤ B) (hr : |r| ≤ B) :
    |update weight m r| ≤ B :=
  abs_le.mpr (update_interval weight m r (-B) B h0 h1 (abs_le.mp hm) (abs_le.mp hr))

theorem track_bounded (weight initial B : ℝ) (r : ℕ → ℝ)
    (h0 : 0 ≤ weight) (h1 : weight ≤ 1) (hi : |initial| ≤ B)
    (hr : ∀ n, |r n| ≤ B) :
    ∀ n, |track weight initial r n| ≤ B := by
  intro n
  induction n with
  | zero => exact hi
  | succ n ih => exact update_bounded weight _ _ B h0 h1 ih (hr n)

theorem initial_difference (weight a b : ℝ) (r : ℕ → ℝ) (n : ℕ) :
    track weight a r n - track weight b r n = weight ^ n * (a - b) := by
  induction n with
  | zero => simp [track]
  | succ n ih =>
    simp only [track, update_difference, ih, pow_succ]
    ring

theorem initial_distance (weight a b : ℝ) (r : ℕ → ℝ) (n : ℕ) (h0 : 0 ≤ weight) :
    |track weight a r n - track weight b r n| = weight ^ n * |a - b| := by
  rw [initial_difference, abs_mul, abs_of_nonneg (pow_nonneg h0 n)]

theorem constant_error (weight initial r : ℝ) (n : ℕ) :
    track weight initial (fun _ => r) n - r = weight ^ n * (initial - r) := by
  induction n with
  | zero => simp [track]
  | succ n ih =>
    simp only [track, update_constant_error, ih, pow_succ]
    ring

theorem constant_distance (weight initial r : ℝ) (n : ℕ) (h0 : 0 ≤ weight) :
    |track weight initial (fun _ => r) n - r| = weight ^ n * |initial - r| := by
  rw [constant_error, abs_mul, abs_of_nonneg (pow_nonneg h0 n)]


theorem constant_converges (weight initial r : ℝ)
    (h0 : 0 ≤ weight) (h1 : weight < 1) :
    Filter.Tendsto (track weight initial (fun _ => r)) Filter.atTop (nhds r) := by
  have formula : track weight initial (fun _ => r) =
      (fun n => weight^n * (initial-r) + r) := by
    funext n
    have h := constant_error weight initial r n
    linarith
  rw [formula]
  simpa using ((tendsto_pow_atTop_nhds_zero_of_lt_one h0 h1).mul_const
    (initial-r)).add_const r

theorem initial_difference_converges (weight a b : ℝ) (r : ℕ → ℝ)
    (h0 : 0 ≤ weight) (h1 : weight < 1) :
    Filter.Tendsto (fun n => track weight a r n-track weight b r n)
      Filter.atTop (nhds 0) := by
  have formula : (fun n => track weight a r n-track weight b r n) =
      (fun n => weight^n * (a-b)) := by
    funext n
    exact initial_difference weight a b r n
  rw [formula]
  simpa using (tendsto_pow_atTop_nhds_zero_of_lt_one h0 h1).mul_const (a-b)

/-- A finite-horizon disturbance bound; both streams may vary arbitrarily. -/
theorem disturbance_bound (weight a b D E : ℝ) (r s : ℕ → ℝ)
    (h0 : 0 ≤ weight) (h1 : weight ≤ 1) (hi : |a-b| ≤ D)
    (hrs : ∀ n, |r n-s n| ≤ E) :
    ∀ n, |track weight a r n-track weight b s n| ≤
      weight^n * D + (1-weight^n) * E := by
  intro n
  induction n with
  | zero => simpa [track] using hi
  | succ n ih =>
    have identity : update weight (track weight a r n) (r n) -
        update weight (track weight b s n) (s n) =
        weight * (track weight a r n-track weight b s n) + (1-weight)*(r n-s n) := by
      unfold update
      ring
    simp only [track]
    rw [identity]
    calc
      _ ≤ |weight * (track weight a r n-track weight b s n)| + |(1-weight)*(r n-s n)| :=
        abs_add_le _ _
      _ = weight * |track weight a r n-track weight b s n| + (1-weight)*|r n-s n| := by
        rw [abs_mul, abs_mul, abs_of_nonneg h0,
          abs_of_nonneg (sub_nonneg.mpr h1)]
      _ ≤ weight * (weight^n*D+(1-weight^n)*E) + (1-weight)*E :=
        add_le_add (mul_le_mul_of_nonneg_left ih h0)
          (mul_le_mul_of_nonneg_left (hrs n) (sub_nonneg.mpr h1))
      _ = _ := by rw [pow_succ]; ring

/-- Monitor-only ingestion cannot execute or mint a grant. -/
def ingest {P : Type} (state : State P) (weight memory residual : ℝ) :
    State P × ℝ := (state, update weight memory residual)

theorem monitor_preserves_protected {P : Type} (state : State P) (weight m r : ℝ) :
    (ingest state weight m r).1.protectedState = state.protectedState := rfl

theorem monitor_preserves_grants {P : Type} (state : State P) (weight m r : ℝ) :
    (ingest state weight m r).1.grants = state.grants := rfl

theorem monitor_preserves_history {P : Type} (state : State P) (weight m r : ℝ) :
    (ingest state weight m r).1.history = state.history := rfl

theorem warning_without_grant_denied {P : Type} (state : State P)
    (roots : List Nat) (p : Proposal) (g : Grant) (now : Nat)
    (weight m r : ℝ) (empty : state.grants = []) :
    ¬ Eligible roots (ingest state weight m r).1 p g now :=
  empty_grants_denied empty

theorem warning_without_grant_preserves {P : Type} (state : State P)
    (roots : List Nat) (p : Proposal) (g : Grant) (now : Nat)
    (apply : P → Nat → P) (weight m r : ℝ) (empty : state.grants = []) :
    (step apply roots (ingest state weight m r).1 p g now).1.protectedState =
      state.protectedState := by
  exact rejection_preserves (warning_without_grant_denied state roots p g now weight m r empty)

end WNSKernel.EFMW
