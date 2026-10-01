# CP8 Verified Search Core v0.1

Derived from user-supplied CP8 Snake Hypercube Lab v1.1 and ES-HyperNEAT v4.0. Original upload files remain unchanged. The HyperNEAT source retains its supplied attribution to Igor A. Holt / genesisconductor.io and Risi & Stanley (2012).

## Reproduce
```sh
cd research/cp8
node test_core.js
python -m unittest test_topology -v
npm install --no-save playwright@1.62.1
npx playwright install chromium
node test_browser.js
```
Open lab.html locally; core is embedded for offline use.
Formal: cd formal/efmw-core; lake update; lake exe cache get; lake build; lake env lean CP8Audit.lean.
Pinned Lean 4.19.0 and mathlib c44e0c8ee63ca166450922a373c7409c5d26b00b.

## Corrections
The uploaded raster poster's 255-edge induced path claim is false. A Hamiltonian path on Q8 uses 255 of 1024 graph edges; additional edges are nonconsecutive chords. Gray codes are valid adjacent traversals but fail this induced-path verifier.
The supplied SVG has different text from the raster poster; it is not automatically evidence of the displayed raster's claim.

## Runtime changes
Shared standalone/browser/worker verifier rejects empty paths, out-of-range states, repeats, nonadjacent steps and chords.
Imports require the v1.1 schema, exact numeric states, matching counts/binary representation and a SHA-256 seal. Candidate is validated before installation; asynchronous state changes abort import. Imported auxiliary claims remain untrusted.
Fixed expansion budget replaces wall-clock stopping. Each counted expansion is one DFS stack-loop iteration; neighbor evaluation remains bounded by dimension (3..10). Timing is descriptive only. Stopped searches are partial results.
CP8 score, harmonic labels and semantic glyphs never establish validity or authority.
SHA-256 is an unsigned content digest, not identity authentication or an optimality certificate.
Fixed-budget tests reproduce results in the same JS runtime; cross-engine floating-point tie-order equivalence remains unproved.

## HyperNEAT repairs and bounds
Optional-dependency fallback permits importing data structures; full substrate construction still explicitly requires JAX/Flax.
Tree allocations count root plus every allocated child. Reserve 8 before subdivision, enforce depth/child-size gates and reset counters between builds.
Initial resolution uses a documented isotropic octree depth ceil(log2(max(resolution))); it can overshoot requested anisotropic resolution.
Legacy topology cache is disabled because its key omitted parameter binding.
Batched CPPN output now uses trailing feature indices and stack(axis=-1); full JAX inference remains untested here.
Topology tests use a synthetic variance source, not a trained CPPN. They validate resource limits, not learned usefulness.
This is not a complete evolutionary training pipeline or ASI result.

## Formal scope
Nine declarations prove soundness/completeness of an abstract decidable path check, state preservation on invalid paths/seals, empty-path denial, no revisits, range binding, valid import commit and score inertness.
JS/Lean refinement and a general extension theorem remain open. Seal truth is supplied as a Boolean assumption in the model; cryptographic correctness is not proved.

## Biological boundary
The VMAT2 note is not included as validated biology. Gate-overload and permissiveness tests can be motivated by its metaphor, without identifying approval monitoring with psychiatric monitoring.
