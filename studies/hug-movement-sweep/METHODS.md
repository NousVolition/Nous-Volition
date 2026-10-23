# Larger clay movements: paired feedback test

The [testing structure](TESTING_STRUCTURE.md) records the questions, controls, decision bands, literature support and future measurements. [protocol.json](protocol.json) freezes the immediate sweep. All physical and field parameters remain synthetic.

## Equations and provenance

The prior model is preserved as [baseline.py](baseline.py), the deformation-aware extension as [feedback.py](feedback.py), and its exact prior protocol as [source_protocol.json](source_protocol.json). SHA-256 hashes are pinned in the new protocol. The full source-law derivation is preserved in the [movement-feedback methods](../hug-memory-feedback/METHODS.md). These files implement the user's accumulated-source and transported-field equations under the declared angular-field and single-shear-mode reduction. They do not implement the full spatial momentum/pressure system.

For actual shear gamma=d/L, x=X+gamma Y, y=Y and det(F)=1. Material coordinates include advection through the chain rule. The angular field uses

    g(theta,gamma)=1+gamma sin(2theta)+gamma² sin²(theta)
    S_t = D partial_s(g partial_s S) + sum_r w_r K_r j_r - lambda S + I_pair
    j_r = jmax tanh(kappa A_r/jmax), A_r'=input_r
    F_memory = -sigma V mean[(Y/L) a(sqrt(g) |partial_s S| - Gamma)].

The source cap, expression relaxation and upper-only pairing are previously declared extensions. Accumulated A never decays or resets. A separate event catalog preserves provenance even if signed inputs cancel. g is positive and shared-face diffusion conserves the spatial mean; the existing source and relaxation terms can change that mean. The exact-off activation is zero for z<=0 and z exp[-(epsilon/z)²] for z>0. Direct pair exchange remains exactly zero in the lower half. Diffusion there is allowed.

## Movement intervention

The unchanged mechanical form is

    m d'' + k d + (V/L) tau = F_orbit + F_memory + (a-b d²)d' - c_brake d'
    tau = G_M(d/L-e_K-e_M)
    e_K'=(tau-G_K e_K)/eta_K, e_M'=tau/eta_M.

At movement factor r, change only b to b0/r² and the initial displacement to r d0. In the primary family also multiply orbital RMS by r. Without the memory force, these changes have an exact mechanical scaling symmetry: d, velocity and internal strains multiply by r, while the period stays unchanged. A unit test checks that identity at arbitrary states. This provides a useful counterfactual: a period change is not automatically built into the amplitude intervention. Keeping the original 0.1 mm numerical scale Q avoids changing the interpretation of state values.

The fixed-force family uses the same larger active mechanism and initial displacements, but keeps the orbital RMS at 6 micronewtons. Its normalized forcing becomes weaker as r grows. Compare moving and frozen spatial operators *within* each family to attribute changes to movement feedback. Differences *between* forcing families can arise from the external drive. No added memory gain was used to force a positive result.

Maximum tested shear is measured from trajectories. The affine geometry remains mathematically nonsingular, but the uncalibrated linear Burgers element is not a validated finite-strain, yielding, hydration or damage law. Large motion does not add those missing mechanisms.

## Numerical and rhythm definitions

Each path is integrated to 1800 s, with DOP853 and exact event boundaries. Main: 32 cells, maximum step .15 s, relative tolerance 2e-8, absolute tolerance 2e-10. Time refinement: 32 cells, maximum step .075 s, relative tolerance 2e-10, absolute tolerance 2e-12. Spatial refinements use 64 and selected 128 cells at the finer time settings. Output combines a .5 s grid with exact 5.7 s orbital checkpoints.

Half-amplitude is half the displacement range in a trailing 57 s window. The reference amplitude is the median at 350–450 s. Recovery is the first eligible value at or after 777 s whose amplitude remains above 80% of baseline through 949.5 s. Report delay from the 720 s release. A missing confirmation is censored at the end of this window. Late amplitude is the median at 1600–1800 s.

Cycle period uses all upward crossings of the late displacement mean. Cubic Hermite interpolation uses both saved displacement and its actual derivative; roots with negative derivative are rejected. At least three crossings are required. This interpolation is checked on a known sinusoid. The phase diagnostic is the maximum absolute wrapped difference of atan2(-v/omega,d-centre), using the fixed-operator period to set omega and each path's late mean as centre. It is a finite-window kinematic phase measure, not a Floquet or chaos calculation.

Mechanical orbit-repeat error uses one-orbit differences in all four mechanical states, then the maximum of ten consecutive comparisons. Divide the original scaled mechanical states by r before applying tolerance .01. This preserves the original relative resolution as movement increases. Confirmation cannot begin before 782.7 s and must persist through 949.5 s. Late repetition must hold at every checked checkpoint after 1700 s. It does not require the abstract field S itself to repeat; this distinction is explicit. No-orbit cases are never given an orbital synchronization result.

Energy accounting compares mechanical energy to active, orbital and memory work minus braking and Burgers dissipation. Residuals are divided by r² to keep relative numerical accuracy comparable. Moving memory force may supply or absorb work. No complete thermodynamics of S is claimed.

Refinement compares the paired field contrast separately from the absolute field error. Fine cell values are averaged to coarse cells before comparison. Mechanical discrepancies and the paired mechanical contrast are divided by r. Both starts are retained separately; they are not independent statistical samples or different family histories.

## Reproduction and files

Install [requirements.txt](requirements.txt), then run:

```
python -m unittest -v
python run.py --kind main --cache CACHE
python run.py --kind fine --cache CACHE
python run.py --kind timefine --cache CACHE
python run.py --kind spatial --scales 300 --cache CACHE
python run.py --kind main --scales 100 300 --orbit-policy fixed --cache CACHE
python run.py --kind fine --scales 100 300 --orbit-policy fixed --cache CACHE
python run.py --kind spatial --scales 100 300 --orbit-policy fixed --cache CACHE
python analyze.py --cache CACHE
python render.py
python verify_saved.py
node check_player.cjs
```

If a primary setting crosses a rhythm screening band, run its 128-cell check before concluding. Run folders refuse overwrite. Full double-precision state arrays are retained in the local simulation cache and can be regenerated. Published data retain full sampled mechanics/work for both starts, A, all field means and first-start field patterns for each condition. A matched field difference is calculated in double precision before storing as float32 alongside the fixed field. Main metrics are calculated before that quantization. Refinement metrics and source hashes are recorded separately.

Animations interpolate saved paths; they do not integrate another model. Shape closure is imposed by the affine drawing, not demonstrated contact stability. The common animation gain is identified on screen and never enters the dynamics. Short clips jump between labeled windows of the same saved trajectory. Offline player checks exercise finite coordinates and controls; they are not a browser layout test.

No source screenshots, DOCX, Miro exports or personal measurements are published. No adoption/ancestry values are used. GitHub publication updates this repository; it does not deploy a website.
