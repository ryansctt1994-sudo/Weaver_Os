import Dragon64.Finite
set_option maxRecDepth 1000000
set_option maxHeartbeats 0
namespace Dragon64

def multiply (m n : Nat) : Nat :=
  ((a m * a n + b m * c n) % 8) +
  8 * ((a m * b n + b m * d n) % 8) +
  64 * ((c m * a n + d m * c n) % 8) +
  512 * ((c m * b n + d m * d n) % 8)

def wordMatrix : List Bool → Nat
  | [] => identity
  | bit :: rest => multiply (if bit then generatorT else generatorS) (wordMatrix rest)

/-- Explicit positive S/T words, checked by the Lean kernel. -/
def generatorWords : List (List Bool) := [
  [false],
  [false, true],
  [false, true, true],
  [false, true, true, true],
  [false, true, true, true, true],
  [false, true, true, true, true, true],
  [true, false, true, true, false, true, false],
  [true, false, true, false],
  [true, true, true, false, true, true, true, false, true, true, true],
  [true, true, true, true, true, false, true, true, true, true, true, false, false, false],
  [true, true, true, false, true, true, true, false, true],
  [true, true, false, true, true, true, false, true, true, false, false, false],
  [true, true, true, false, true, true, true, true, false, true, false],
  [true, true, true, false, true, true, true, false, true, true],
  [true, true, false, true, true, true, false, true, true, false, true, false, false],
  [true, true, true, false, true, true, true, false],
  [true, true, true, false, true, true, true, false, true, true, true, false, false],
  [true, true, true, false, true, true, true, false, false, false],
  [true, true, false, true, true, true, false, true, true, false, true],
  [true, true, true, false, true, true, true, false, true, true, false, false],
  [true, true, true, false, true, true, true, true, false, true, false, false, false],
  [true, true, false, true, true, true, false, true, true, false],
  [true, true, true, false, true, true, true, false, true, false, false],
  [true, true, true, true, true, false, true, true, true, true, true, false],
  [false, false, false],
  [true, false, true, false, false, false],
  [true, false, true, true, false, true, false, false, false],
  [false, true, true, true, true, true, false, false],
  [false, true, true, true, true, false, false],
  [false, true, true, true, false, false],
  [false, true, true, false, false],
  [false, true, false, false],
  [],
  [false, true, false, false, false],
  [false, true, true, false, false, false],
  [false, true, true, true, false, false, false],
  [false, true, true, true, true, false, false, false],
  [false, true, true, true, true, true, false, false, false],
  [true, false, true, true, false, true],
  [true, false, true],
  [false, true, false, true, false, false, false],
  [false, true, true, false, true, false, false, false],
  [false, true, true, true, false, true, false, false, false],
  [false, true, true, true, true, false, true, false, false, false],
  [false, true, true, true, true, true, false, true, false, false, false],
  [true, false, true, true, false, true, true, false],
  [true, false, true, true, false],
  [true, false],
  [true, true, true, true, true, true],
  [false, true, true, false, true, true, false, true, false, false, false],
  [false, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, false, true, true, true, true, true, false],
  [false, true, true, true, true, true, false, true, true, false, true, false, false, false],
  [true, false, true, true, false, true, true, true, false, true, false],
  [true, false, true, true, true, false, true, false],
  [true, true, false, true, false],
  [true, true, true, true, true],
  [false, true, false, true, true, true, true, true, false, false],
  [true, true, true, true, false, true, true, false, true, false, false],
  [true, true, true, false, true, true, false, true, true, false, false, false],
  [true, true, true, true, false, true, true, true, true, false, true, false, false],
  [true, true, false, true, true, false, true, true, true, false, true, true, false, false],
  [true, false, true, true, true, false, true, true, false, true, false],
  [true, true, false, true, true, false, true, false],
  [true, true, true, true],
  [false, true, false, true, true, true, true, false, false],
  [true, true, true, true, false, true, true, false, false, false],
  [false, true, true, true, false, true, true, true, true, false, false],
  [true, true, true, true, false, true, true, true, true, false, false, false],
  [true, true, false, true, true, false, true, true, true, false, true, false, false],
  [true, true, true, true, true, false, true, true, false, true],
  [true, false, true, true, true, true, true],
  [true, true, true],
  [false, true, false, true, true, true, false, false],
  [false, true, true, false, true, true, true, false, false],
  [false, true, true, true, false, true, true, true, false, false],
  [true, true, false, true, true, true, true, false, true, false, false],
  [true, true, false, true, true, false, true, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, false],
  [true, false, true, true, true, true],
  [true, true],
  [false, true, false, true, true, false, false],
  [false, true, true, false, true, true, false, false],
  [false, true, true, true, false, true, true, false, false],
  [true, true, false, true, true, true, true, false, false, false],
  [false, true, true, true, true, true, false, true, true, false, false],
  [true, false, true, true, false, true, true, true],
  [true, false, true, true, true],
  [true],
  [false, true, false, true, false, false],
  [false, true, true, false, true, false, false],
  [false, true, true, true, false, true, false, false],
  [false, true, true, true, true, false, true, false, false],
  [false, true, true, true, true, true, false, true, false, false],
  [true, false, true, true, false, true, true],
  [true, false, true, true],
  [false, true, false, true, true, false, false, false],
  [false, true, true, true, true, true, false, true, true, false, false, false],
  [false, true, true, false, true, true, false, false, false],
  [true, false, true, true, false, true, true, true, false],
  [false, true, true, true, false, true, true, false, false, false],
  [true, false, true, true, true, false],
  [true, true, false],
  [true, true, false, true, true, true, true],
  [false, true, false, true, true, true, false, true, false, false, false],
  [true, true, true, true, true, true, false, true, true, false, false],
  [true, true, true, true, true, false, true, true, true, false, false, false],
  [false, true, true, false, true, true, true, false, true, false, false, false],
  [true, false, true, true, true, false, true, true, true],
  [true, false, true, true, true, true, false, true, false],
  [true, true, false, true, true, true],
  [true, true, true, false, true, false],
  [false, true, false, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, true, true, true, true, false, true, false, false],
  [true, false, true, true, false, true, true, true, false, true, true],
  [false, true, true, false, true, true, false, true, true, false, false],
  [true, true, true, false, true, true, true, true, true, false, false, false],
  [true, false, true, true, true, false, true, true],
  [true, true, false, true, true],
  [true, true, true, false, true, true, false, true, false],
  [true, true, true, true, true, true, false, false, false],
  [false, true, true, true, true, true, false, true, true, false, true, false, false],
  [true, false, true, true, false, true, true, true, false, true],
  [false, true, true, false, true, true, false, true, false, false],
  [true, false, true, true, true, false, true],
  [false, true, true, true, false, true, true, false, true, false, false],
  [true, true, false, true],
  [true, true, false, true, true, true, true, true],
  [true, true, true, false, true, true, true, false, true, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, true, true, true, false, false],
  [true, true, true, false, true, true, true, false, true, false, false, false],
  [true, true, false, true, true, true, false, true, true, false, false],
  [true, true, true, false, true, true, true, true, false, true],
  [true, true, true, false, true, true, true, false, true, true, false, false, false],
  [true, true, false, true, true, true, false, true, true, false, true, false],
  [true, true, true, false, true, true, true],
  [false, true, true, true, false, true, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, false, false],
  [false, true, false, true, true, true, false, false, false],
  [true, true, false, true, true, true, true, false, true, false, false, false],
  [true, false, true, true, true, true, false],
  [false, true, true, false, true, true, true, false, false, false],
  [true, true, false, true, true, false, true, true, true],
  [true, true, true, false],
  [true, false, true, true, false, true, true, true, false, true, true, false],
  [true, true, true, true, true, true, false, true, false, false, false],
  [true, true, true, false, true, true, false, true, false, false],
  [true, false, true, true, true, false, true, true, false],
  [false, true, true, false, true, true, false, true, true, false, false, false],
  [false, true, false, true, true, true, false, true, true, false, true],
  [true, true, false, true, true, false],
  [true, true, true, false, true, true, true, true, true],
  [true, true, false, true, true, true, false, true, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, true, true, false, false],
  [false, true, false, true, true, true, false, true, true, false, false],
  [true, true, false, true, true, true, false, true, false, false],
  [true, true, true, false, true, true, true, true, false],
  [false, true, true, false, true, true, true, false, true, true, false, false],
  [true, true, true, true, true, true, false, true, true, false, true],
  [true, true, true, false, true, true],
  [false, true, true, true, false, true, true, true, true, false, true, false, false, false],
  [true, true, true, true, true, false, true, false, false],
  [false, true, false, true, true, true, true, false, true, false, false, false],
  [true, true, true, true, false, true, true, true, true, true, false],
  [true, false, true, true, true, true, true, false, true, false],
  [true, true, true, true, false, true, true, true, false],
  [true, true, false, true, true, false, true, true],
  [true, true, true, true, false, true, false],
  [false, true, true, false, true, true, true, false, true, true, false],
  [true, true, true, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, true, false, true, true, false, false, false],
  [true, true, false, true, true, true, false, true, true, true, false, false],
  [true, true, true, true, true, false, true, true, true, true, false],
  [false, true, false, true, true, true, false, true, true, false],
  [true, true, false, true, true, true, false, true, false],
  [true, true, true, false, true, true, true, true],
  [true, false, true, true, true, false, true, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, true, false, false],
  [false, true, false, true, true, true, false, true, false, false],
  [true, true, false, true, true, true, false, false, false],
  [true, false, true, true, true, true, false, true],
  [false, true, true, false, true, true, true, false, true, false, false],
  [true, true, true, true, true, true, false, true, true, false],
  [true, true, true, false, true],
  [true, true, false, true, true, false, true, true, true, false, true, true, false],
  [true, true, true, true, true, false, false, false],
  [true, true, true, false, true, true, false, true, true, false, false],
  [true, false, true, true, true, false, true, true, false, true],
  [false, true, false, true, true, true, true, true, false],
  [true, true, true, true, false, true, true, true, true, false, true, false],
  [true, true, false, true, true, false, true],
  [true, true, true, true, false, true, true, false, true, false],
  [false, true, false, true, true, true, true, false, false, false],
  [false, true, true, true, false, true, true, true, true, false, false, false],
  [true, true, false, true, true, false, true, true, true, false, true, false, false, false],
  [true, false, true, true, true, true, true, false],
  [true, true, true, true, false],
  [true, true, true, true, false, true, true],
  [true, true, true, true, false, true, true, true, true],
  [true, true, true, true, true, false, true, true, false, true, false],
  [true, true, true, true, true, false, true, false, false, false],
  [true, true, true, true, false, true, true, true, true, true, false, false],
  [true, true, true, true, false, true, true, true, false, false],
  [true, true, true, true, false, true, false, false],
  [false, true, true, true, false, true, true, true, true, false, true],
  [false, true, false, true, true, true, true, false, true],
  [true, false, true, true, true, true, true, false, true, false, false],
  [true, true, false, true, true, false, true, true, false],
  [false, true, true, true, false, true, true, true, true, false, true, false, false],
  [true, true, false, true, true, false, true, true, false, false, false],
  [true, false, true, true, true, true, true, false, true],
  [false, true, false, true, true, true, true, false, true, false, false],
  [true, true, true, true, false, true],
  [true, true, true, true, false, true, true, true],
  [true, true, true, true, false, true, true, true, true, true],
  [true, true, true, true, true, false, true, false],
  [true, true, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, true, true, false, true, true, true, true, false, false],
  [true, true, true, true, false, true, true, false, false],
  [true, false, true, true, true, true, true, false, false, false],
  [true, true, false, true, true, false, true, true, true, false, true, false],
  [false, true, true, true, false, true, true, true, true, false],
  [false, true, false, true, true, true, true, false],
  [true, true, true, false, true, true, true, false, true, true, true, false],
  [true, true, true, false, true, true, true, false, false],
  [true, true, false, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, true, false, true, true, true, false, true, true, false],
  [true, true, true, false, true, true, true, true, false, true, false, false],
  [true, true, false, true, true, true, false, true, true],
  [true, true, true, false, true, true, true, false, true, false],
  [true, true, true, true, true, false, true, true, true, true, true],
  [true, true, false, true, true, false, true, true, true, false, true, true, false, false, false],
  [true, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, false, true, true, false, true, false, false],
  [true, true, true, true, false, true, true, true, true, false, true, false, false, false],
  [false, true, false, true, true, true, true, true, false, false, false],
  [true, false, true, true, true, false, true, true, false, true, false, false],
  [true, true, true, false, true, true, false, true, true],
  [true, true, true, true, true, false],
  [true, false, true, true, true, false, true, true, true, false],
  [true, true, true, false, true, false, false],
  [true, true, true, true, true, true, false, true, true, false, false, false],
  [false, true, true, false, true, true, true, false, true],
  [true, false, true, true, true, true, false, true, false, false],
  [true, true, false, true, true, true, false],
  [false, true, false, true, true, true, false, true],
  [true, true, true, true, true, false, true, true, true],
  [false, true, true, false, true, true, true, false, true, true, false, false, false],
  [true, true, true, false, true, true, true, true, false, false],
  [true, true, false, true, true, true, false, true, false, false, false],
  [false, true, false, true, true, true, false, true, true, false, false, false],
  [true, true, true, true, true, false, true, true, true, true, false, false, false],
  [true, true, false, true, true, true, false, true, true, true],
  [true, true, true, false, true, true, false],
  [true, true, true, true, true, true, false, true, true, false, true, false],
  [false, true, true, true, false, true, true, true, true, false, true, false],
  [true, true, true, true, false, true, false, false, false],
  [true, true, false, true, true, false, true, true, false, false],
  [true, true, true, true, false, true, true, true, false, false, false],
  [true, false, true, true, true, true, true, false, true, false, false, false],
  [true, true, true, true, false, true, true, true, true, true, false, false, false],
  [false, true, false, true, true, true, true, false, true, false],
  [true, true, true, true, true, false, true],
  [true, true, false, true, true, true, false, true, true, true, false],
  [true, true, true, false, true, true, false, false],
  [true, true, true, true, true, true, false, true, true, false, true, false, false],
  [false, true, true, false, true, true, true, false, true, true],
  [true, true, true, false, true, true, true, true, false, false, false],
  [true, true, false, true, true, true, false, true],
  [false, true, false, true, true, true, false, true, true],
  [true, true, true, true, true, false, true, true, true, true],
  [true, false, true, true, false, true, true, true, false, true, true, false, false, false],
  [true, true, true, false, true, true, true, true, true, false, false],
  [true, true, false, true, true, false, false, false],
  [false, true, false, true, true, true, false, true, true, false, true, false, false],
  [false, true, true, false, true, true, false, true, true, false],
  [true, false, true, true, true, false, true, true, false, false, false],
  [true, true, true, false, true, true, false, true],
  [true, true, true, true, true, true, false, true, false],
  [false, true, true, true, false, true, true, true, false],
  [true, true, true, false, false, false],
  [true, true, false, true, true, false, true, true, true, false, false],
  [false, true, true, false, true, true, true, false],
  [true, false, true, true, true, true, false, false, false],
  [true, true, false, true, true, true, true, false, true, false],
  [false, true, false, true, true, true, false],
  [true, true, true, true, true, false, true, true],
  [true, true, false, true, true, true, true, true, false, false],
  [true, true, false, true, false, false],
  [false, true, true, true, false, true, true, false, true],
  [true, false, true, true, true, false, true, false, false],
  [false, true, true, false, true, true, false, true],
  [true, false, true, true, false, true, true, true, false, true, false, false],
  [true, true, true, true, true, true, false],
  [false, true, true, true, true, true, false, true, true, false, true],
  [true, true, true, false, true, true, false, true, false, false, false],
  [true, true, false, true, true, false, false],
  [true, false, true, true, true, false, true, true, false, false],
  [true, true, true, false, true, true, true, true, true, false],
  [true, false, true, true, false, true, true, true, false, true, true, false, false],
  [false, true, true, false, true, true, false, true, true],
  [true, true, true, true, true, true, false, true],
  [false, true, false, true, true, true, false, true, true, false, true, false],
  [true, true, true, false, true, false, false, false],
  [true, true, false, true, true, true, false, false],
  [true, false, true, true, true, false, true, true, true, false, false],
  [true, false, true, true, true, true, false, true, false, false, false],
  [false, true, true, false, true, true, true, false, true, false],
  [true, true, true, true, true, false, true, true, true, false],
  [true, true, true, true, true, true, false, true, true],
  [false, true, false, true, true, true, false, true, false],
  [true, true, false, false, false],
  [true, true, false, true, true, true, true, false, false],
  [true, false, true, true, true, false, false, false],
  [false, true, true, true, false, true, true, false],
  [true, false, true, true, false, true, true, true, false, false, false],
  [false, true, true, false, true, true, false],
  [false, true, true, true, true, true, false, true, true, false],
  [false, true, false, true, true, false],
  [false, false],
  [true, false, true, false, false],
  [true, false, true, true, false, true, false, false],
  [false, true, true, true, true, true, false],
  [false, true, true, true, true, false],
  [false, true, true, true, false],
  [false, true, true, false],
  [false, true, false],
  [true, false, false],
  [true, false, true, true, false, false],
  [true, false, true, true, false, true, true, false, false],
  [false, true, true, true, true, true, false, true],
  [false, true, true, true, true, false, true],
  [false, true, true, true, false, true],
  [false, true, true, false, true],
  [false, true, false, true],
  [true, true, false, false],
  [true, false, true, true, true, false, false],
  [true, false, true, true, false, true, true, true, false, false],
  [false, true, true, true, true, true, false, true, true],
  [true, true, false, true, true, true, true, false],
  [false, true, true, true, false, true, true],
  [false, true, true, false, true, true],
  [false, true, false, true, true],
  [true, true, true, false, false],
  [true, false, true, true, true, true, false, false],
  [true, true, true, true, true, false, true, true, false, false, false],
  [true, true, false, true, true, false, true, true, true, false],
  [true, true, false, true, true, true, true, false, true],
  [false, true, true, true, false, true, true, true],
  [false, true, true, false, true, true, true],
  [false, true, false, true, true, true],
  [true, true, true, true, false, false],
  [true, false, true, true, true, true, true, false, false],
  [true, true, true, true, true, false, true, true, false, true, false, false],
  [true, true, false, true, true, false, true, true, true, false, true],
  [true, true, true, true, false, true, true, true, true, false],
  [false, true, true, true, false, true, true, true, true],
  [true, true, true, true, false, true, true, false],
  [false, true, false, true, true, true, true],
  [true, true, true, true, true, false, false],
  [true, true, false, true, true, false, true, false, false, false],
  [true, false, true, true, true, false, true, true, false, true, false, false, false],
  [true, true, false, true, true, false, true, true, true, false, true, true],
  [true, true, true, true, false, true, true, true, true, false, true],
  [true, true, true, false, true, true, false, true, true, false],
  [true, true, true, true, false, true, true, false, true],
  [false, true, false, true, true, true, true, true],
  [true, true, true, true, true, true, false, false],
  [true, true, false, true, false, false, false],
  [true, false, true, true, true, false, true, false, false, false],
  [true, false, true, true, false, true, true, true, false, true, false, false, false],
  [false, true, true, true, true, true, false, true, true, false, true, false],
  [true, true, false, true, true, true, true, true, false, false, false],
  [false, true, true, true, false, true, true, false, true, false],
  [false, true, true, false, true, true, false, true, false],
  [false, true, false, true, false],
  [true, false, false, false],
  [true, false, true, true, false, false, false],
  [true, false, true, true, false, true, true, false, false, false],
  [false, true, true, true, true, true, false, true, false],
  [false, true, true, true, true, false, true, false],
  [false, true, true, true, false, true, false],
  [false, true, true, false, true, false]
]

theorem generator_words_complete : generatorWords.map wordMatrix = sl2 := by decide

theorem every_enumerated_matrix_generated (m : Nat) (h : m ∈ sl2) :
    ∃ w : List Bool, wordMatrix w = m := by
  rw [← generator_words_complete] at h
  obtain ⟨w, _, hw⟩ := List.mem_map.mp h
  exact ⟨w, hw⟩

/-- Generator composition laws on the complete determinant-one enumeration. -/
def generatorActionCheck (g : Nat) : Bool :=
  sl2.all (fun m => (List.range 64).all (fun v =>
    act (multiply g m) v == act g (act m v)))
theorem s_composition_checked : generatorActionCheck generatorS = true := by decide
theorem t_composition_checked : generatorActionCheck generatorT = true := by decide

def pairAct (m p : Nat) := 64 * act m (p / 64) + act m (p % 64)
def pairOrbit (p : Nat) := (sl2.map (fun m => pairAct m p)).eraseDups
def pairRepresentatives : List Nat := [0, 1, 2, 4, 64, 65, 66, 67, 68, 69, 70, 71, 72, 80, 81, 88, 96, 97, 98, 99, 104, 112, 113, 120, 128, 129, 130, 131, 132, 134, 136, 144, 145, 152, 160, 162, 176, 256, 257, 258, 260, 264, 272, 288]
def pairPartition := pairRepresentatives.map pairOrbit

/-- Materialized certificate; equality to computed images is checked below. -/
def pairBlocks : List (List Nat) := [
  [0],
  [56, 40, 24, 8, 1, 9, 17, 25, 33, 41, 49, 57, 10, 26, 42, 58, 3, 11, 19, 27, 35, 43, 51, 59, 28, 60, 12, 44, 5, 13, 21, 29, 37, 45, 53, 61, 14, 30, 46, 62, 7, 15, 23, 31, 39, 47, 55, 63],
  [48, 16, 2, 18, 34, 50, 20, 52, 6, 22, 38, 54],
  [32, 4, 36],
  [3584, 2560, 1536, 512, 64, 576, 1088, 1600, 2112, 2624, 3136, 3648, 640, 1664, 2688, 3712, 192, 704, 1216, 1728, 2240, 2752, 3264, 3776, 1792, 3840, 768, 2816, 320, 832, 1344, 1856, 2368, 2880, 3392, 3904, 896, 1920, 2944, 3968, 448, 960, 1472, 1984, 2496, 3008, 3520, 4032],
  [3640, 2600, 1560, 520, 65, 585, 1105, 1625, 2145, 2665, 3185, 3705, 650, 1690, 2730, 3770, 195, 715, 1235, 1755, 2275, 2795, 3315, 3835, 1820, 3900, 780, 2860, 325, 845, 1365, 1885, 2405, 2925, 3445, 3965, 910, 1950, 2990, 4030, 455, 975, 1495, 2015, 2535, 3055, 3575, 4095],
  [3632, 2576, 1584, 528, 66, 594, 1122, 1650, 2114, 2642, 3170, 3698, 660, 1716, 2708, 3764, 198, 726, 1254, 1782, 2246, 2774, 3302, 3830, 1840, 3888, 784, 2832, 322, 850, 1378, 1906, 2370, 2898, 3426, 3954, 916, 1972, 2964, 4020, 454, 982, 1510, 2038, 2502, 3030, 3558, 4086],
  [3624, 2616, 1544, 536, 67, 603, 1139, 1611, 2147, 2683, 3155, 3691, 670, 1678, 2750, 3758, 193, 729, 1265, 1737, 2273, 2809, 3281, 3817, 1804, 3884, 796, 2876, 327, 863, 1399, 1871, 2407, 2943, 3415, 3951, 922, 1930, 3002, 4010, 453, 989, 1525, 1997, 2533, 3069, 3541, 4077],
  [3616, 2592, 1568, 544, 68, 612, 1092, 1636, 2116, 2660, 3140, 3684, 672, 1696, 2720, 3744, 196, 740, 1220, 1764, 2244, 2788, 3268, 3812, 1824, 3872, 800, 2848, 324, 868, 1348, 1892, 2372, 2916, 3396, 3940, 928, 1952, 2976, 4000, 452, 996, 1476, 2020, 2500, 3044, 3524, 4068],
  [3608, 2568, 1592, 552, 69, 621, 1109, 1661, 2149, 2637, 3189, 3677, 682, 1722, 2698, 3738, 199, 751, 1239, 1791, 2279, 2767, 3319, 3807, 1852, 3868, 812, 2828, 321, 873, 1361, 1913, 2401, 2889, 3441, 3929, 942, 1982, 2958, 3998, 451, 1003, 1491, 2043, 2531, 3019, 3571, 4059],
  [3600, 2608, 1552, 560, 70, 630, 1126, 1622, 2118, 2678, 3174, 3670, 692, 1684, 2740, 3732, 194, 754, 1250, 1746, 2242, 2802, 3298, 3794, 1808, 3856, 816, 2864, 326, 886, 1382, 1878, 2374, 2934, 3430, 3926, 948, 1940, 2996, 3988, 450, 1010, 1506, 2002, 2498, 3058, 3554, 4050],
  [3592, 2584, 1576, 568, 71, 639, 1143, 1647, 2151, 2655, 3159, 3663, 702, 1710, 2718, 3726, 197, 765, 1269, 1773, 2277, 2781, 3285, 3789, 1836, 3852, 828, 2844, 323, 891, 1395, 1899, 2403, 2907, 3411, 3915, 954, 1962, 2970, 3978, 449, 1017, 1521, 2025, 2529, 3033, 3537, 4041],
  [3585, 3593, 3601, 3609, 3617, 3625, 3633, 3641, 2563, 2571, 2579, 2587, 2595, 2603, 2611, 2619, 1541, 1549, 1557, 1565, 1573, 1581, 1589, 1597, 519, 527, 535, 543, 551, 559, 567, 575, 72, 584, 1096, 1608, 2120, 2632, 3144, 3656, 73, 593, 1113, 1633, 2153, 2673, 3193, 3649, 74, 602, 1130, 1658, 2122, 2650, 3178, 3706, 75, 611, 1147, 1619, 2155, 2627, 3163, 3699, 76, 620, 1100, 1644, 2124, 2668, 3148, 3692, 77, 629, 1117, 1605, 2157, 2645, 3197, 3685, 78, 638, 1134, 1630, 2126, 2686, 3182, 3678, 79, 583, 1151, 1655, 2159, 2663, 3167, 3671, 649, 681, 1681, 1713, 2713, 2745, 3713, 3745, 659, 691, 1675, 1707, 2691, 2723, 3739, 3771, 669, 701, 1669, 1701, 2701, 2733, 3733, 3765, 647, 679, 1695, 1727, 2711, 2743, 3727, 3759, 216, 728, 1240, 1752, 2264, 2776, 3288, 3800, 217, 753, 1225, 1761, 2297, 2769, 3305, 3777, 218, 714, 1274, 1770, 2266, 2762, 3322, 3818, 219, 739, 1259, 1779, 2299, 2755, 3275, 3795, 220, 764, 1244, 1788, 2268, 2812, 3292, 3836, 221, 725, 1229, 1733, 2301, 2805, 3309, 3813, 222, 750, 1278, 1742, 2270, 2798, 3326, 3790, 223, 711, 1263, 1751, 2303, 2791, 3279, 3831, 1801, 1817, 1833, 1849, 3841, 3857, 3873, 3889, 779, 795, 811, 827, 2819, 2835, 2851, 2867, 1797, 1813, 1829, 1845, 3853, 3869, 3885, 3901, 775, 791, 807, 823, 2831, 2847, 2863, 2879, 360, 872, 1384, 1896, 2408, 2920, 3432, 3944, 361, 849, 1401, 1889, 2377, 2929, 3417, 3905, 362, 890, 1354, 1882, 2410, 2938, 3402, 3930, 363, 867, 1371, 1875, 2379, 2883, 3451, 3955, 364, 844, 1388, 1868, 2412, 2892, 3436, 3916, 365, 885, 1405, 1861, 2381, 2901, 3421, 3941, 366, 862, 1358, 1918, 2414, 2910, 3406, 3966, 367, 839, 1375, 1911, 2383, 2919, 3455, 3927, 921, 953, 1937, 1969, 2953, 2985, 3969, 4001, 915, 947, 1947, 1979, 2947, 2979, 3979, 4011, 909, 941, 1925, 1957, 2973, 3005, 3989, 4021, 903, 935, 1935, 1967, 2967, 2999, 3999, 4031, 504, 1016, 1528, 2040, 2552, 3064, 3576, 4088, 505, 1009, 1513, 2017, 2521, 3025, 3529, 4033, 506, 1002, 1498, 1994, 2554, 3050, 3546, 4042, 507, 995, 1483, 2035, 2523, 3011, 3563, 4051, 508, 988, 1532, 2012, 2556, 3036, 3580, 4060, 509, 981, 1517, 1989, 2525, 3061, 3533, 4069, 510, 974, 1502, 2030, 2558, 3022, 3550, 4078, 511, 967, 1487, 2007, 2527, 3047, 3567, 4087],
  [3586, 3602, 3618, 3634, 2566, 2582, 2598, 2614, 1538, 1554, 1570, 1586, 518, 534, 550, 566, 80, 592, 1104, 1616, 2128, 2640, 3152, 3664, 82, 610, 1138, 1602, 2130, 2658, 3186, 3650, 84, 628, 1108, 1652, 2132, 2676, 3156, 3700, 86, 582, 1142, 1638, 2134, 2630, 3190, 3686, 658, 1698, 2738, 3714, 678, 1686, 2694, 3766, 690, 1666, 2706, 3746, 646, 1718, 2726, 3734, 240, 752, 1264, 1776, 2288, 2800, 3312, 3824, 242, 738, 1234, 1730, 2290, 2786, 3282, 3778, 244, 724, 1268, 1748, 2292, 2772, 3316, 3796, 246, 710, 1238, 1766, 2294, 2758, 3286, 3814, 1810, 1842, 3842, 3874, 790, 822, 2822, 2854, 1794, 1826, 3858, 3890, 774, 806, 2838, 2870, 336, 848, 1360, 1872, 2384, 2896, 3408, 3920, 338, 866, 1394, 1858, 2386, 2914, 3442, 3906, 340, 884, 1364, 1908, 2388, 2932, 3412, 3956, 342, 838, 1398, 1894, 2390, 2886, 3446, 3942, 946, 1954, 2962, 3970, 934, 1974, 2950, 3990, 914, 1922, 2994, 4002, 902, 1942, 2982, 4022, 496, 1008, 1520, 2032, 2544, 3056, 3568, 4080, 498, 994, 1490, 1986, 2546, 3042, 3538, 4034, 500, 980, 1524, 2004, 2548, 3028, 3572, 4052, 502, 966, 1494, 2022, 2550, 3014, 3542, 4070],
  [3642, 3594, 3610, 3626, 2606, 2622, 2574, 2590, 1562, 1578, 1594, 1546, 526, 542, 558, 574, 81, 601, 1121, 1641, 2161, 2681, 3137, 3657, 83, 619, 1091, 1627, 2163, 2635, 3171, 3707, 85, 637, 1125, 1613, 2165, 2653, 3141, 3693, 87, 591, 1095, 1663, 2167, 2671, 3175, 3679, 668, 1724, 2716, 3772, 680, 1704, 2728, 3752, 700, 1692, 2748, 3740, 648, 1672, 2696, 3720, 243, 763, 1219, 1739, 2259, 2779, 3299, 3819, 245, 749, 1253, 1757, 2261, 2765, 3269, 3837, 247, 735, 1223, 1775, 2263, 2815, 3303, 3791, 241, 713, 1249, 1785, 2257, 2793, 3265, 3801, 1838, 1806, 3902, 3870, 794, 826, 2858, 2826, 1822, 1854, 3854, 3886, 778, 810, 2874, 2842, 341, 861, 1381, 1901, 2421, 2941, 3397, 3917, 343, 879, 1351, 1887, 2423, 2895, 3431, 3967, 337, 889, 1377, 1865, 2417, 2905, 3393, 3945, 339, 843, 1347, 1915, 2419, 2923, 3427, 3931, 952, 1976, 3000, 4024, 940, 1932, 2988, 3980, 920, 1944, 2968, 3992, 908, 1964, 2956, 4012, 503, 1023, 1479, 1999, 2519, 3039, 3559, 4079, 497, 1001, 1505, 2009, 2513, 3017, 3521, 4089, 499, 987, 1475, 2027, 2515, 3067, 3555, 4043, 501, 973, 1509, 2045, 2517, 3053, 3525, 4061],
  [3587, 3611, 3635, 3595, 3619, 3643, 3603, 3627, 2561, 2585, 2609, 2569, 2593, 2617, 2577, 2601, 1543, 1567, 1591, 1551, 1575, 1599, 1559, 1583, 517, 541, 565, 525, 549, 573, 533, 557, 88, 600, 1112, 1624, 2136, 2648, 3160, 3672, 91, 627, 1099, 1635, 2171, 2643, 3179, 3651, 94, 590, 1150, 1646, 2142, 2638, 3198, 3694, 89, 609, 1129, 1649, 2169, 2625, 3145, 3665, 92, 636, 1116, 1660, 2140, 2684, 3164, 3708, 95, 599, 1103, 1607, 2175, 2679, 3183, 3687, 90, 618, 1146, 1610, 2138, 2666, 3194, 3658, 93, 581, 1133, 1621, 2173, 2661, 3149, 3701, 667, 699, 1715, 1683, 2699, 2731, 3715, 3747, 689, 657, 1689, 1721, 2689, 2721, 3721, 3753, 655, 687, 1671, 1703, 2719, 2751, 3767, 3735, 645, 677, 1677, 1709, 2741, 2709, 3741, 3773, 200, 712, 1224, 1736, 2248, 2760, 3272, 3784, 203, 723, 1243, 1763, 2283, 2803, 3323, 3779, 206, 734, 1262, 1790, 2254, 2782, 3310, 3838, 201, 737, 1273, 1745, 2281, 2753, 3289, 3825, 204, 748, 1228, 1772, 2252, 2796, 3276, 3820, 207, 759, 1247, 1735, 2287, 2775, 3327, 3815, 202, 762, 1258, 1754, 2250, 2810, 3306, 3802, 205, 709, 1277, 1781, 2285, 2789, 3293, 3797, 1819, 1803, 1851, 1835, 3843, 3891, 3875, 3859, 793, 777, 825, 809, 2817, 2865, 2849, 2833, 1799, 1847, 1831, 1815, 3871, 3855, 3903, 3887, 773, 821, 805, 789, 2845, 2829, 2877, 2861, 376, 888, 1400, 1912, 2424, 2936, 3448, 3960, 379, 883, 1387, 1891, 2395, 2899, 3403, 3907, 382, 878, 1374, 1870, 2430, 2926, 3422, 3918, 377, 865, 1353, 1905, 2393, 2881, 3433, 3921, 380, 860, 1404, 1884, 2428, 2908, 3452, 3932, 383, 855, 1391, 1863, 2399, 2935, 3407, 3943, 378, 842, 1370, 1898, 2426, 2890, 3418, 3946, 381, 837, 1357, 1877, 2397, 2917, 3437, 3957, 907, 939, 1971, 1939, 2971, 3003, 3971, 4003, 945, 913, 1929, 1961, 2945, 2977, 3993, 4025, 927, 959, 1927, 1959, 2959, 2991, 4023, 3991, 901, 933, 1949, 1981, 2997, 2965, 3981, 4013, 488, 1000, 1512, 2024, 2536, 3048, 3560, 4072, 491, 979, 1531, 2019, 2507, 3059, 3547, 4035, 494, 1022, 1486, 2014, 2542, 3070, 3534, 4062, 489, 993, 1497, 2001, 2505, 3009, 3577, 4081, 492, 972, 1516, 1996, 2540, 3020, 3564, 4044, 495, 1015, 1535, 1991, 2511, 3031, 3551, 4071, 490, 986, 1482, 2042, 2538, 3034, 3530, 4090, 493, 965, 1501, 2037, 2509, 3045, 3581, 4053],
  [3588, 3620, 2564, 2596, 1540, 1572, 516, 548, 96, 608, 1120, 1632, 2144, 2656, 3168, 3680, 100, 580, 1124, 1604, 2148, 2628, 3172, 3652, 676, 1668, 2724, 3716, 644, 1700, 2692, 3748, 224, 736, 1248, 1760, 2272, 2784, 3296, 3808, 228, 708, 1252, 1732, 2276, 2756, 3300, 3780, 1828, 3844, 804, 2820, 1796, 3876, 772, 2852, 352, 864, 1376, 1888, 2400, 2912, 3424, 3936, 356, 836, 1380, 1860, 2404, 2884, 3428, 3908, 932, 1924, 2980, 3972, 900, 1956, 2948, 4004, 480, 992, 1504, 2016, 2528, 3040, 3552, 4064, 484, 964, 1508, 1988, 2532, 3012, 3556, 4036],
  [3644, 3612, 2604, 2572, 1564, 1596, 524, 556, 97, 617, 1137, 1657, 2113, 2633, 3153, 3673, 101, 589, 1141, 1629, 2117, 2669, 3157, 3709, 686, 1694, 2702, 3774, 654, 1726, 2734, 3742, 227, 747, 1267, 1787, 2243, 2763, 3283, 3803, 231, 719, 1271, 1759, 2247, 2799, 3287, 3839, 1848, 3896, 808, 2856, 1816, 3864, 776, 2824, 357, 877, 1397, 1917, 2373, 2893, 3413, 3933, 353, 841, 1393, 1881, 2369, 2921, 3409, 3961, 938, 1946, 2954, 4026, 906, 1978, 2986, 3994, 487, 1007, 1527, 2047, 2503, 3023, 3543, 4063, 483, 971, 1523, 2011, 2499, 3051, 3539, 4091],
  [3636, 3604, 2580, 2612, 1588, 1556, 532, 564, 98, 626, 1090, 1618, 2146, 2674, 3138, 3666, 102, 598, 1094, 1654, 2150, 2646, 3142, 3702, 688, 1712, 2736, 3760, 656, 1680, 2704, 3728, 230, 758, 1222, 1750, 2278, 2806, 3270, 3798, 226, 722, 1218, 1778, 2274, 2770, 3266, 3826, 1812, 3892, 820, 2836, 1844, 3860, 788, 2868, 354, 882, 1346, 1874, 2402, 2930, 3394, 3922, 358, 854, 1350, 1910, 2406, 2902, 3398, 3958, 944, 1968, 2992, 4016, 912, 1936, 2960, 3984, 486, 1014, 1478, 2006, 2534, 3062, 3526, 4054, 482, 978, 1474, 2034, 2530, 3026, 3522, 4082],
  [3628, 3596, 2620, 2588, 1548, 1580, 540, 572, 99, 635, 1107, 1643, 2115, 2651, 3187, 3659, 103, 607, 1111, 1615, 2119, 2687, 3191, 3695, 698, 1674, 2714, 3754, 666, 1706, 2746, 3722, 225, 761, 1233, 1769, 2241, 2777, 3313, 3785, 229, 733, 1237, 1741, 2245, 2813, 3317, 3821, 1832, 3880, 824, 2872, 1800, 3848, 792, 2840, 359, 895, 1367, 1903, 2375, 2911, 3447, 3919, 355, 859, 1363, 1867, 2371, 2939, 3443, 3947, 958, 1934, 2974, 4014, 926, 1966, 3006, 3982, 485, 1021, 1493, 2029, 2501, 3037, 3573, 4045, 481, 985, 1489, 1993, 2497, 3065, 3569, 4073],
  [3589, 3629, 3605, 3645, 3621, 3597, 3637, 3613, 2567, 2607, 2583, 2623, 2599, 2575, 2615, 2591, 1537, 1577, 1553, 1593, 1569, 1545, 1585, 1561, 515, 555, 531, 571, 547, 523, 563, 539, 104, 616, 1128, 1640, 2152, 2664, 3176, 3688, 109, 597, 1149, 1637, 2125, 2677, 3165, 3653, 106, 634, 1098, 1626, 2154, 2682, 3146, 3674, 111, 615, 1119, 1623, 2127, 2631, 3199, 3703, 108, 588, 1132, 1612, 2156, 2636, 3180, 3660, 105, 625, 1145, 1601, 2121, 2641, 3161, 3681, 110, 606, 1102, 1662, 2158, 2654, 3150, 3710, 107, 579, 1115, 1651, 2123, 2659, 3195, 3667, 685, 653, 1685, 1717, 2749, 2717, 3717, 3749, 663, 695, 1711, 1679, 2695, 2727, 3775, 3743, 697, 665, 1665, 1697, 2729, 2697, 3729, 3761, 643, 675, 1723, 1691, 2707, 2739, 3755, 3723, 248, 760, 1272, 1784, 2296, 2808, 3320, 3832, 253, 757, 1261, 1765, 2269, 2773, 3277, 3781, 250, 746, 1242, 1738, 2298, 2794, 3290, 3786, 255, 743, 1231, 1783, 2271, 2759, 3311, 3799, 252, 732, 1276, 1756, 2300, 2780, 3324, 3804, 249, 721, 1257, 1729, 2265, 2801, 3273, 3809, 254, 718, 1246, 1774, 2302, 2766, 3294, 3822, 251, 707, 1227, 1747, 2267, 2787, 3307, 3827, 1837, 1853, 1805, 1821, 3845, 3861, 3877, 3893, 815, 831, 783, 799, 2823, 2839, 2855, 2871, 1793, 1809, 1825, 1841, 3881, 3897, 3849, 3865, 771, 787, 803, 819, 2859, 2875, 2827, 2843, 328, 840, 1352, 1864, 2376, 2888, 3400, 3912, 333, 853, 1373, 1893, 2413, 2933, 3453, 3909, 330, 858, 1386, 1914, 2378, 2906, 3434, 3962, 335, 871, 1407, 1879, 2415, 2887, 3423, 3959, 332, 876, 1356, 1900, 2380, 2924, 3404, 3948, 329, 881, 1369, 1857, 2409, 2897, 3449, 3937, 334, 894, 1390, 1886, 2382, 2942, 3438, 3934, 331, 835, 1403, 1907, 2411, 2915, 3419, 3923, 957, 925, 1941, 1973, 2989, 2957, 3973, 4005, 919, 951, 1983, 1951, 2951, 2983, 4015, 3983, 937, 905, 1921, 1953, 3001, 2969, 3985, 4017, 899, 931, 1963, 1931, 2963, 2995, 4027, 3995, 472, 984, 1496, 2008, 2520, 3032, 3544, 4056, 477, 1013, 1485, 2021, 2557, 3029, 3565, 4037, 474, 970, 1530, 2026, 2522, 3018, 3578, 4074, 479, 999, 1519, 2039, 2559, 3015, 3535, 4055, 476, 1020, 1500, 2044, 2524, 3068, 3548, 4092, 473, 977, 1481, 1985, 2553, 3057, 3561, 4065, 478, 1006, 1534, 1998, 2526, 3054, 3582, 4046, 475, 963, 1515, 2003, 2555, 3043, 3531, 4083],
  [3590, 3638, 3622, 3606, 2562, 2610, 2594, 2578, 1542, 1590, 1574, 1558, 514, 562, 546, 530, 112, 624, 1136, 1648, 2160, 2672, 3184, 3696, 118, 614, 1110, 1606, 2166, 2662, 3158, 3654, 116, 596, 1140, 1620, 2164, 2644, 3188, 3668, 114, 578, 1106, 1634, 2162, 2626, 3154, 3682, 694, 1702, 2710, 3718, 674, 1714, 2690, 3730, 662, 1670, 2742, 3750, 642, 1682, 2722, 3762, 208, 720, 1232, 1744, 2256, 2768, 3280, 3792, 214, 742, 1270, 1734, 2262, 2790, 3318, 3782, 212, 756, 1236, 1780, 2260, 2804, 3284, 3828, 210, 706, 1266, 1762, 2258, 2754, 3314, 3810, 1846, 1814, 3846, 3878, 818, 786, 2818, 2850, 1798, 1830, 3894, 3862, 770, 802, 2866, 2834, 368, 880, 1392, 1904, 2416, 2928, 3440, 3952, 374, 870, 1366, 1862, 2422, 2918, 3414, 3910, 372, 852, 1396, 1876, 2420, 2900, 3444, 3924, 370, 834, 1362, 1890, 2418, 2882, 3410, 3938, 918, 1958, 2998, 3974, 930, 1938, 2946, 4018, 950, 1926, 2966, 4006, 898, 1970, 2978, 3986, 464, 976, 1488, 2000, 2512, 3024, 3536, 4048, 470, 998, 1526, 1990, 2518, 3046, 3574, 4038, 468, 1012, 1492, 2036, 2516, 3060, 3540, 4084, 466, 962, 1522, 2018, 2514, 3010, 3570, 4066],
  [3646, 3630, 3614, 3598, 2602, 2586, 2570, 2618, 1566, 1550, 1598, 1582, 522, 570, 554, 538, 113, 633, 1089, 1609, 2129, 2649, 3169, 3689, 119, 623, 1127, 1631, 2135, 2639, 3143, 3711, 117, 605, 1093, 1645, 2133, 2685, 3173, 3661, 115, 587, 1123, 1659, 2131, 2667, 3139, 3675, 696, 1720, 2744, 3768, 684, 1676, 2732, 3724, 664, 1688, 2712, 3736, 652, 1708, 2700, 3756, 211, 731, 1251, 1771, 2291, 2811, 3267, 3787, 209, 745, 1217, 1753, 2289, 2761, 3297, 3833, 215, 767, 1255, 1743, 2295, 2783, 3271, 3823, 213, 717, 1221, 1789, 2293, 2797, 3301, 3805, 1802, 1834, 3898, 3866, 830, 798, 2862, 2830, 1818, 1850, 3882, 3850, 782, 814, 2846, 2878, 373, 893, 1349, 1869, 2389, 2909, 3429, 3949, 371, 875, 1379, 1883, 2387, 2891, 3395, 3963, 369, 857, 1345, 1897, 2385, 2937, 3425, 3913, 375, 847, 1383, 1919, 2391, 2927, 3399, 3935, 924, 1980, 2972, 4028, 936, 1960, 2984, 4008, 956, 1948, 3004, 3996, 904, 1928, 2952, 3976, 471, 991, 1511, 2031, 2551, 3071, 3527, 4047, 469, 1005, 1477, 2013, 2549, 3021, 3557, 4093, 467, 1019, 1507, 1995, 2547, 3035, 3523, 4075, 465, 969, 1473, 2041, 2545, 3049, 3553, 4057],
  [3591, 3647, 3639, 3631, 3623, 3615, 3607, 3599, 2565, 2621, 2613, 2605, 2597, 2589, 2581, 2573, 1539, 1595, 1587, 1579, 1571, 1563, 1555, 1547, 513, 569, 561, 553, 545, 537, 529, 521, 120, 632, 1144, 1656, 2168, 2680, 3192, 3704, 127, 631, 1135, 1639, 2143, 2647, 3151, 3655, 126, 622, 1118, 1614, 2174, 2670, 3166, 3662, 125, 613, 1101, 1653, 2141, 2629, 3181, 3669, 124, 604, 1148, 1628, 2172, 2652, 3196, 3676, 123, 595, 1131, 1603, 2139, 2675, 3147, 3683, 122, 586, 1114, 1642, 2170, 2634, 3162, 3690, 121, 577, 1097, 1617, 2137, 2657, 3177, 3697, 703, 671, 1719, 1687, 2735, 2703, 3719, 3751, 693, 661, 1725, 1693, 2693, 2725, 3757, 3725, 683, 651, 1667, 1699, 2747, 2715, 3763, 3731, 641, 673, 1705, 1673, 2737, 2705, 3769, 3737, 232, 744, 1256, 1768, 2280, 2792, 3304, 3816, 239, 727, 1279, 1767, 2255, 2807, 3295, 3783, 238, 766, 1230, 1758, 2286, 2814, 3278, 3806, 237, 741, 1245, 1749, 2253, 2757, 3325, 3829, 236, 716, 1260, 1740, 2284, 2764, 3308, 3788, 235, 755, 1275, 1731, 2251, 2771, 3291, 3811, 234, 730, 1226, 1786, 2282, 2778, 3274, 3834, 233, 705, 1241, 1777, 2249, 2785, 3321, 3793, 1855, 1839, 1823, 1807, 3847, 3895, 3879, 3863, 829, 813, 797, 781, 2821, 2869, 2853, 2837, 1795, 1843, 1827, 1811, 3899, 3883, 3867, 3851, 769, 817, 801, 785, 2873, 2857, 2841, 2825, 344, 856, 1368, 1880, 2392, 2904, 3416, 3928, 351, 887, 1359, 1895, 2431, 2903, 3439, 3911, 350, 846, 1406, 1902, 2398, 2894, 3454, 3950, 349, 869, 1389, 1909, 2429, 2885, 3405, 3925, 348, 892, 1372, 1916, 2396, 2940, 3420, 3964, 347, 851, 1355, 1859, 2427, 2931, 3435, 3939, 346, 874, 1402, 1866, 2394, 2922, 3450, 3914, 345, 833, 1385, 1873, 2425, 2913, 3401, 3953, 943, 911, 1975, 1943, 3007, 2975, 3975, 4007, 949, 917, 1965, 1933, 2949, 2981, 4029, 3997, 955, 923, 1923, 1955, 2987, 2955, 4019, 3987, 897, 929, 1977, 1945, 2993, 2961, 4009, 3977, 456, 968, 1480, 1992, 2504, 3016, 3528, 4040, 463, 983, 1503, 2023, 2543, 3063, 3583, 4039, 462, 990, 1518, 2046, 2510, 3038, 3566, 4094, 461, 997, 1533, 2005, 2541, 3013, 3549, 4085, 460, 1004, 1484, 2028, 2508, 3052, 3532, 4076, 459, 1011, 1499, 1987, 2539, 3027, 3579, 4067, 458, 1018, 1514, 2010, 2506, 3066, 3562, 4058, 457, 961, 1529, 2033, 2537, 3041, 3545, 4049],
  [3072, 1024, 128, 1152, 2176, 3200, 1280, 3328, 384, 1408, 2432, 3456],
  [3128, 1064, 3096, 1032, 129, 1161, 2193, 3225, 161, 1193, 2225, 3257, 1290, 3354, 1322, 3386, 387, 1419, 2451, 3483, 419, 1451, 2483, 3515, 3100, 3132, 1036, 1068, 133, 1165, 2197, 3229, 165, 1197, 2229, 3261, 1294, 3358, 1326, 3390, 391, 1423, 2455, 3487, 423, 1455, 2487, 3519],
  [3120, 1040, 130, 1170, 2210, 3250, 1300, 3380, 390, 1430, 2470, 3510],
  [3112, 1080, 3080, 1048, 131, 1179, 2227, 3211, 163, 1211, 2195, 3243, 1310, 3342, 1342, 3374, 385, 1433, 2481, 3465, 417, 1465, 2449, 3497, 3084, 3116, 1052, 1084, 135, 1183, 2231, 3215, 167, 1215, 2199, 3247, 1306, 3338, 1338, 3370, 389, 1437, 2485, 3469, 421, 1469, 2453, 3501],
  [3104, 1056, 132, 1188, 2180, 3236, 1312, 3360, 388, 1444, 2436, 3492],
  [3088, 1072, 134, 1206, 2214, 3222, 1332, 3348, 386, 1458, 2466, 3474],
  [3073, 3081, 3089, 3097, 3105, 3113, 3121, 3129, 1027, 1035, 1043, 1051, 1059, 1067, 1075, 1083, 3077, 3085, 3093, 3101, 3109, 3117, 3125, 3133, 1031, 1039, 1047, 1055, 1063, 1071, 1079, 1087, 136, 1160, 2184, 3208, 137, 1169, 2201, 3233, 169, 1201, 2233, 3201, 138, 1178, 2218, 3258, 139, 1187, 2235, 3219, 171, 1155, 2203, 3251, 140, 1196, 2188, 3244, 141, 1205, 2205, 3205, 173, 1173, 2237, 3237, 142, 1214, 2222, 3230, 143, 1159, 2239, 3255, 175, 1191, 2207, 3223, 1289, 1321, 3345, 3377, 1305, 1337, 3329, 3361, 1299, 1331, 3339, 3371, 1283, 1315, 3355, 3387, 1309, 1341, 3333, 3365, 1293, 1325, 3349, 3381, 1287, 1319, 3359, 3391, 1303, 1335, 3343, 3375, 408, 1432, 2456, 3480, 409, 1457, 2441, 3489, 441, 1425, 2473, 3457, 410, 1418, 2490, 3498, 411, 1443, 2475, 3507, 443, 1411, 2443, 3475, 412, 1468, 2460, 3516, 413, 1429, 2445, 3461, 445, 1461, 2477, 3493, 414, 1454, 2494, 3470, 415, 1415, 2479, 3479, 447, 1447, 2447, 3511, 168, 1192, 2216, 3240, 170, 1210, 2186, 3226, 172, 1164, 2220, 3212, 174, 1182, 2190, 3262, 440, 1464, 2488, 3512, 442, 1450, 2458, 3466, 444, 1436, 2492, 3484, 446, 1422, 2462, 3502],
  [3074, 3090, 3106, 3122, 1030, 1046, 1062, 1078, 144, 1168, 2192, 3216, 146, 1186, 2226, 3202, 148, 1204, 2196, 3252, 150, 1158, 2230, 3238, 1298, 3362, 1330, 3330, 1318, 3350, 1286, 3382, 432, 1456, 2480, 3504, 434, 1442, 2450, 3458, 436, 1428, 2484, 3476, 438, 1414, 2454, 3494],
  [3130, 3082, 3098, 3114, 1070, 1086, 1038, 1054, 145, 1177, 2209, 3241, 177, 1209, 2177, 3209, 147, 1195, 2179, 3227, 179, 1163, 2211, 3259, 149, 1213, 2213, 3213, 181, 1181, 2181, 3245, 151, 1167, 2183, 3263, 183, 1199, 2215, 3231, 1308, 3388, 1320, 3368, 1340, 3356, 1288, 3336, 435, 1467, 2435, 3467, 403, 1435, 2467, 3499, 437, 1453, 2469, 3485, 405, 1421, 2437, 3517, 439, 1439, 2439, 3503, 407, 1471, 2471, 3471, 433, 1417, 2465, 3513, 401, 1449, 2433, 3481, 3118, 3086, 3134, 3102, 1050, 1082, 1066, 1034, 1336, 3384, 1324, 3340, 1304, 3352, 1292, 3372],
  [3075, 3099, 3123, 3083, 3107, 3131, 3091, 3115, 1025, 1049, 1073, 1033, 1057, 1081, 1041, 1065, 3079, 3103, 3127, 3087, 3111, 3135, 3095, 3119, 1029, 1053, 1077, 1037, 1061, 1085, 1045, 1069, 152, 1176, 2200, 3224, 155, 1203, 2187, 3235, 187, 1171, 2219, 3203, 158, 1166, 2238, 3246, 153, 1185, 2217, 3249, 185, 1153, 2185, 3217, 156, 1212, 2204, 3260, 159, 1175, 2191, 3207, 191, 1207, 2223, 3239, 154, 1194, 2234, 3210, 157, 1157, 2221, 3221, 189, 1189, 2189, 3253, 1307, 1339, 3379, 3347, 1291, 1323, 3331, 3363, 1329, 1297, 3353, 3385, 1281, 1313, 3337, 3369, 1295, 1327, 3335, 3367, 1311, 1343, 3383, 3351, 1285, 1317, 3341, 3373, 1333, 1301, 3357, 3389, 392, 1416, 2440, 3464, 395, 1427, 2459, 3491, 427, 1459, 2491, 3459, 398, 1438, 2478, 3518, 393, 1441, 2489, 3473, 425, 1409, 2457, 3505, 396, 1452, 2444, 3500, 399, 1463, 2463, 3463, 431, 1431, 2495, 3495, 394, 1466, 2474, 3482, 397, 1413, 2493, 3509, 429, 1445, 2461, 3477, 184, 1208, 2232, 3256, 190, 1198, 2206, 3214, 188, 1180, 2236, 3228, 186, 1162, 2202, 3242, 424, 1448, 2472, 3496, 430, 1470, 2446, 3486, 428, 1420, 2476, 3468, 426, 1434, 2442, 3514],
  [3076, 3108, 1028, 1060, 160, 1184, 2208, 3232, 164, 1156, 2212, 3204, 1316, 3332, 1284, 3364, 416, 1440, 2464, 3488, 420, 1412, 2468, 3460],
  [3124, 3092, 1044, 1076, 162, 1202, 2178, 3218, 166, 1174, 2182, 3254, 1328, 3376, 1296, 3344, 422, 1462, 2438, 3478, 418, 1426, 2434, 3506],
  [3078, 3126, 3110, 3094, 1026, 1074, 1058, 1042, 176, 1200, 2224, 3248, 182, 1190, 2198, 3206, 180, 1172, 2228, 3220, 178, 1154, 2194, 3234, 1334, 3366, 1302, 3334, 1314, 3378, 1282, 3346, 400, 1424, 2448, 3472, 406, 1446, 2486, 3462, 404, 1460, 2452, 3508, 402, 1410, 2482, 3490],
  [2048, 256, 2304],
  [2104, 2088, 2072, 2056, 257, 2313, 273, 2329, 289, 2345, 305, 2361, 2058, 2074, 2090, 2106, 259, 2315, 275, 2331, 291, 2347, 307, 2363, 2076, 2108, 2060, 2092, 261, 2317, 277, 2333, 293, 2349, 309, 2365, 2062, 2078, 2094, 2110, 263, 2319, 279, 2335, 295, 2351, 311, 2367],
  [2096, 2064, 258, 2322, 290, 2354, 2068, 2100, 262, 2326, 294, 2358],
  [2080, 260, 2340],
  [2049, 2057, 2065, 2073, 2081, 2089, 2097, 2105, 2051, 2059, 2067, 2075, 2083, 2091, 2099, 2107, 2053, 2061, 2069, 2077, 2085, 2093, 2101, 2109, 2055, 2063, 2071, 2079, 2087, 2095, 2103, 2111, 264, 2312, 265, 2321, 281, 2337, 297, 2353, 313, 2305, 266, 2330, 298, 2362, 267, 2339, 315, 2323, 299, 2307, 283, 2355, 268, 2348, 269, 2357, 285, 2309, 301, 2325, 317, 2341, 270, 2366, 302, 2334, 271, 2311, 319, 2359, 303, 2343, 287, 2327, 280, 2328, 282, 2314, 314, 2346, 284, 2364, 286, 2350, 318, 2318, 296, 2344, 300, 2316, 312, 2360, 316, 2332],
  [2050, 2066, 2082, 2098, 2054, 2070, 2086, 2102, 272, 2320, 274, 2338, 306, 2306, 276, 2356, 278, 2310, 310, 2342, 304, 2352, 308, 2324],
  [2052, 2084, 288, 2336, 292, 2308]
]

theorem pair_partition_evaluates : pairPartition = pairBlocks := by decide

theorem pair_representatives_count : pairRepresentatives.length = 44 := by decide
/-- Structural merge/sort keeps the certificate reducible in the kernel. -/
def mergeFuel : Nat → List Nat → List Nat → List Nat
  | 0, xs, ys => xs ++ ys
  | _ + 1, [], ys => ys
  | _ + 1, xs, [] => xs
  | fuel + 1, x :: xs, y :: ys =>
    if x ≤ y then x :: mergeFuel fuel xs (y :: ys)
    else y :: mergeFuel fuel (x :: xs) ys

def sortFuel : Nat → List Nat → List Nat
  | 0, xs => xs
  | fuel + 1, xs =>
    if xs.length ≤ 1 then xs
    else
      let n := xs.length / 2
      mergeFuel xs.length (sortFuel fuel (xs.take n)) (sortFuel fuel (xs.drop n))

theorem mergeFuel_mem (fuel : Nat) (xs ys : List Nat) (p : Nat) :
    p ∈ mergeFuel fuel xs ys ↔ p ∈ xs ++ ys := by
  induction fuel generalizing xs ys with
  | zero => rfl
  | succ fuel ih =>
    cases xs with
    | nil => simp [mergeFuel]
    | cons x xs =>
      cases ys with
      | nil => simp [mergeFuel]
      | cons y ys =>
        simp only [mergeFuel]
        split <;> simp [ih, or_assoc, or_comm, or_left_comm]

theorem sortFuel_mem (fuel : Nat) (xs : List Nat) (p : Nat) :
    p ∈ sortFuel fuel xs ↔ p ∈ xs := by
  induction fuel generalizing xs with
  | zero => rfl
  | succ fuel ih =>
    simp only [sortFuel]
    split
    · rfl
    · simp only [mergeFuel_mem, List.mem_append, ih]
      rw [← List.mem_append, List.take_append_drop]

/-- Sorted equality establishes coverage and multiplicity one simultaneously. -/
theorem pair_partition_exact :
    sortFuel 13 pairPartition.flatten = List.range 4096 := by
  rw [pair_partition_evaluates]
  decide


theorem pair_partition_total_size : pairPartition.flatten.length = 4096 := by
  rw [pair_partition_evaluates]
  decide

theorem pair_partition_covers (p : Nat) (h : p ∈ List.range 4096) :
    p ∈ pairPartition.flatten := by
  rw [← pair_partition_exact] at h
  exact (sortFuel_mem 13 pairPartition.flatten p).mp h

def generatorClosureCheck (g : Nat) : Bool :=
  sl2.all (fun m => decide (multiply g m < 4096) && determinantOne (multiply g m))
theorem s_closure_checked : generatorClosureCheck generatorS = true := by decide
theorem t_closure_checked : generatorClosureCheck generatorT = true := by decide

theorem s_preserves_enumeration (m : Nat) (h : m ∈ sl2) :
    multiply generatorS m ∈ sl2 := by
  have hc := (List.all_eq_true.mp s_closure_checked) m h
  have hb : multiply generatorS m < 4096 ∧ determinantOne (multiply generatorS m) = true := by
    simpa [generatorClosureCheck] using hc
  simpa [sl2] using hb

theorem t_preserves_enumeration (m : Nat) (h : m ∈ sl2) :
    multiply generatorT m ∈ sl2 := by
  have hc := (List.all_eq_true.mp t_closure_checked) m h
  have hb : multiply generatorT m < 4096 ∧ determinantOne (multiply generatorT m) = true := by
    simpa [generatorClosureCheck] using hc
  simpa [sl2] using hb

theorem word_in_enumeration (w : List Bool) : wordMatrix w ∈ sl2 := by
  induction w with
  | nil => decide
  | cons bit rest ih =>
    cases bit with
    | false => exact s_preserves_enumeration _ ih
    | true => exact t_preserves_enumeration _ ih

theorem generated_iff_enumerated (m : Nat) :
    (∃ w : List Bool, wordMatrix w = m) ↔ m ∈ sl2 := by
  constructor
  · rintro ⟨w, rfl⟩
    exact word_in_enumeration w
  · exact every_enumerated_matrix_generated m

/-- Each partition block is stable under both generating permutations. -/
def partitionStable (g : Nat) : Bool :=
  pairBlocks.all (fun block =>
    sortFuel 9 (block.map (pairAct g)) == sortFuel 9 block)
theorem pair_partition_s_stable : partitionStable generatorS = true := by decide
theorem pair_partition_t_stable : partitionStable generatorT = true := by decide

end Dragon64
