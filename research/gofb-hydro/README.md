# GOFB-HYDRO Core v0.1

Corrected mathematical and computational slice of the uploaded acoustics/water plates.
No experiments have been performed by this package.

## Run
```sh
python -m unittest discover -s research/gofb-hydro -v
python research/gofb-hydro/hydro.py
cd formal/efmw-core
lake update
lake exe cache get
lake build Hydro
lake env lean HydroAudit.lean
```

## Corrections
- For the assumed amplitude absorption law alpha=25e-15*f^2 Np/m: 1 MHz gives 0.00217147 dB/cm; 2 MHz gives 0.00868589 dB/cm.
- At assumed sound speed 1480 m/s, half wavelength at 4 MHz is 185 micrometres. Counting half wavelengths across a width does not establish resonant mode existence or an exact node count.
- A 10-micrometre diameter sphere has volume 0.523599 pL.
- Conventional contrast factor includes 1/3; peak radiation force uses 4*pi*a^3*k*E*abs(Phi), without another 1/3.
- No universal freezing temperature is assigned to a mineral or organism.

## Mathematical model
cap(c)=(2-3c+c^3)/4=(2+c)(1-c)^2/4; factor(theta)=cap(cos(theta)).
Lean angles are radians. Python interface angles are degrees.
Theorems cover algebraic equivalence, complements, bounds, endpoints, antitonicity in cosine, monotonicity in angle on [0,pi], and nonnegative barrier reduction.
The spherical-cap factor assumes classical cap geometry; proofs do not establish applicability to real nucleating surfaces.

## Acoustic scope
Coefficient 25e-15 is an explicit reference-model assumption, not a temperature-dependent calibration.
Amplitude exp(-alpha*L), intensity exp(-2*alpha*L), loss=20/ln(10)*alpha*L dB.
No wall losses, scattering, cavitation, heating, viscous radiation corrections or streaming solution.
Force comparison uses a small-sphere inviscid peak formula and low-Re Stokes drag. Selected gates ka<=0.1 and Re<=0.1 do not establish all approximation assumptions.
Relative speed is supplied; this calculator does not predict acoustic streaming.
Source: Bruus, Acoustofluidics 7, DOI 10.1039/C2LC21068A; Scientific Reports 2021, DOI 10.1038/s41598-021-86985-7.

## Evidence
Numerical tests establish implementation behavior on specified examples. Lean proofs establish mathematical consequences of the model. SHA-256 receipts bind canonical model inputs/outputs; they are unsigned, not measurements, not independent witness evidence.
Real Lean arithmetic is not a proof of Python floating-point correspondence.
