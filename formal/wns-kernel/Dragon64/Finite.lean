import Std

set_option maxRecDepth 1000000
set_option maxHeartbeats 0

namespace Dragon64

/-- Base-eight encoding (a,b,c,d) ↦ a + 8b + 64c + 512d. -/
def a (m : Nat) := m % 8
def b (m : Nat) := (m / 8) % 8
def c (m : Nat) := (m / 64) % 8
def d (m : Nat) := (m / 512) % 8

/-- 7 is -1 modulo eight; avoids truncated natural subtraction. -/
def determinantOne (m : Nat) : Bool :=
  (a m * d m + 7 * b m * c m) % 8 == 1

def sl2 : List Nat := (List.range 4096).filter determinantOne

def act (m v : Nat) : Nat :=
  ((a m * (v / 8) + b m * (v % 8)) % 8) * 8 +
    (c m * (v / 8) + d m * (v % 8)) % 8

def identity := 513
def generatorS := 120
def generatorT := 961

def pointOrbit (v : Nat) : List Nat := (sl2.map (fun m => act m v)).eraseDups

theorem determinant_enumeration_count : sl2.length = 384 := by decide

theorem identity_determinant_one : determinantOne identity = true := by decide
theorem s_determinant_one : determinantOne generatorS = true := by decide
theorem t_determinant_one : determinantOne generatorT = true := by decide

theorem identity_action (v : Fin 64) : act identity v.val = v.val := by decide

theorem s_fourth_power (v : Fin 64) :
    act generatorS (act generatorS (act generatorS (act generatorS v.val))) = v.val := by
  decide

def iterate (m : Nat) : Nat → Nat → Nat
  | 0, v => v
  | n + 1, v => act m (iterate m n v)

theorem t_eighth_power (v : Fin 64) : iterate generatorT 8 v.val = v.val := by decide

theorem zero_orbit_size : (pointOrbit 0).length = 1 := by decide
theorem four_orbit_size : (pointOrbit 4).length = 3 := by decide
theorem two_orbit_size : (pointOrbit 2).length = 12 := by decide
theorem one_orbit_size : (pointOrbit 1).length = 48 := by decide

def pointPartition := [pointOrbit 0, pointOrbit 4, pointOrbit 2, pointOrbit 1]

theorem point_partition_covers :
    (List.range 64).all (fun v => pointPartition.flatten.contains v) = true := by decide

theorem point_partition_no_overlap : pointPartition.flatten.eraseDups.length = 64 := by decide

/-- Per-matrix fixed points, evaluated directly on all 64 points. -/
def fixedPoints (m : Nat) :=
  ((List.range 64).filter (fun v => act m v == v)).length

def fixedPairSum := (sl2.map (fun m => fixedPoints m * fixedPoints m)).foldl (· + ·) 0

/-- Exact numerator; applying Burnside's theorem is a separate mathematical bridge. -/
theorem fixed_pair_sum_exact : fixedPairSum = 16896 := by decide
theorem burnside_quotient_arithmetic : 16896 / 384 = (44 : Nat) := by decide

end Dragon64
