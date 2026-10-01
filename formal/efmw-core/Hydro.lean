import Mathlib

namespace GOFB.Hydro
noncomputable section

def cap (c : ℝ) : ℝ := (2 - 3*c + c^3)/4
def factor (angle : ℝ) : ℝ := cap (Real.cos angle)

theorem cap_factorized (c : ℝ) :
    cap c = (2+c)*(1-c)^2/4 := by unfold cap; ring
theorem cap_complement (c : ℝ) :
    1-cap c = (2-c)*(1+c)^2/4 := by unfold cap; ring
theorem cap_nonnegative (c : ℝ) (lo : -1 ≤ c) : 0 ≤ cap c := by
  rw [cap_factorized]
  have h : 0 ≤ 2+c := by linarith
  positivity
theorem cap_at_most_one (c : ℝ) (hi : c ≤ 1) : cap c ≤ 1 := by
  have h2 : 0 ≤ 2-c := by linarith
  have h : 0 ≤ (2-c)*(1+c)^2/4 := by positivity
  rw [← cap_complement] at h
  linarith
theorem cap_bounds (c : ℝ) (lo : -1 ≤ c) (hi : c ≤ 1) :
    0 ≤ cap c ∧ cap c ≤ 1 :=
  ⟨cap_nonnegative c lo, cap_at_most_one c hi⟩
theorem cap_one : cap 1 = 0 := by norm_num [cap]
theorem cap_zero : cap 0 = 1/2 := by norm_num [cap]
theorem cap_neg_one : cap (-1) = 1 := by norm_num [cap]
theorem cap_antitone (a b : ℝ) (ha : -1 ≤ a) (hab : a ≤ b) (hb : b ≤ 1) :
    cap b ≤ cap a := by
  have ab : -1 ≤ b := le_trans ha hab
  have aa : a ≤ 1 := le_trans hab hb
  have asq : a*a ≤ 1 := by nlinarith
  have bsq : b*b ≤ 1 := by nlinarith
  have cross : a*b ≤ 1 := by nlinarith [sq_nonneg (a-b)]
  have prod := mul_nonneg (sub_nonneg.mpr hab)
    (show 0 ≤ 3-(a*a+a*b+b*b) by linarith)
  unfold cap
  nlinarith
theorem factor_bounds (angle : ℝ) :
    0 ≤ factor angle ∧ factor angle ≤ 1 :=
  cap_bounds _ (Real.neg_one_le_cos _) (Real.cos_le_one _)
theorem factor_zero : factor 0 = 0 := by norm_num [factor, cap]
theorem factor_pi : factor Real.pi = 1 := by norm_num [factor, cap]
theorem factor_half_pi : factor (Real.pi/2) = 1/2 := by
  norm_num [factor, cap]
/-- Angle monotonicity is restricted to the physical contact-angle domain. -/
theorem factor_monotone (a b : ℝ) (ha : 0 ≤ a) (hab : a ≤ b)
    (hb : b ≤ Real.pi) : factor a ≤ factor b := by
  apply cap_antitone
  · exact Real.neg_one_le_cos b
  · exact Real.cos_le_cos_of_nonneg_of_le_pi ha hb hab
  · exact Real.cos_le_one a

theorem barrier_bounds (angle barrier : ℝ) (h : 0 ≤ barrier) :
    0 ≤ factor angle * barrier ∧ factor angle * barrier ≤ barrier := by
  have bounds := factor_bounds angle
  constructor
  · exact mul_nonneg bounds.1 h
  · nlinarith [mul_nonneg (sub_nonneg.mpr bounds.2) h]

end
end GOFB.Hydro
