# Dragon-64 finite certificates

This module translates the finite modulo-eight permutation model into Lean 4.19.0 using Std only. It does not model the separate complex 64-by-64 modular representation.

Matrices are encoded by a + 8b + 64c + 512d, with entries in 0..7. Points are encoded by 8x + y. The determinant test uses ad + 7bc modulo eight. S = (0,7,1,0), T = (1,0,7,1), and I = (1,0,0,1).

## Checked statements

The 15 declarations establish:

- Exactly 384 of the 4096 entry combinations satisfy determinant one.
- I, S and T satisfy the determinant condition.
- I acts identically; S applied four times and T applied eight times act identically on every one of the 64 points. These are power identities, not proofs of minimal order.
- Images of representatives 0, 4, 2 and 1 under the enumerated matrices have sizes 1, 3, 12 and 48 and cover the 64 points without overlap.
- The sum of squared fixed-point counts is exactly 16896, and 16896 / 384 = 44.

Every proof uses kernel reduction with `decide`; none uses `native_decide`, `sorry`, or a custom axiom. DragonAudit.lean reports axiom dependencies for every declaration. CI builds both Dragon64 and WNSKernel and retains build and audit logs.

## Reproduce

Install the toolchain in the parent lean-toolchain file, then run from formal/wns-kernel:

```sh
lake build
lake env lean DragonAudit.lean
```

## Boundaries

The enumeration and image calculations are proved against these Lean definitions. Generated-subgroup equality, matrix composition/action laws, and the application of Burnside's theorem remain to be formalized. Therefore the quotient theorem alone is not a formal proof of 44 pair orbits or commutant dimension. The exact rational Wedderburn decomposition, spectral assertions, and physical interpretations are outside this module.

The definitions were manually translated from the existing Dragon-64 exact permutation certificate (modulus 8, S and T as above). No theorem yet establishes equivalence to that Python implementation. GitHub CI is a reproducible automated check, not an independent external witness.
