# Hug calibration: measurements before a physical rhythm claim

Open the [local measurement notebook](calibration/measurements.html) after downloading the study folder. It has an embedded empty session, CSV import/paste, trial selection, checks, JSON import and export. It sends nothing to a server and does not save automatically: export before closing. Keep your measurement files outside this published study directory. GitHub shows HTML source; download it with its companion script to use the form locally.

The [blank JSON session](calibration/blank_session.json) and [header-only CSV](calibration/measurement_template.csv) contain **no observations**. Published starting clay values are guesses, not a calibration of your specimen. All completed example recordings and their plots are explicitly **synthetic**. This batch adds no SIMS participant runs and no physical measurements. It does not change the earlier active Hug parameters automatically.

## Recording plan

Use one consistent signed displacement coordinate and synchronized force/motion channels. Record specimen identity, water mass fraction, temperature, conditioning, sensor resolution and sample timing. Choose prediction error limits before inspecting validation results, based on the intended use and measurement precision. Twelve rows is a file minimum, not an adequate sampling recommendation; choose sampling and duration to resolve the fastest motion, response delay, slow recovery and drift. Velocity needs its own measurement or a documented noise-aware estimate, rather than an unexamined difference of noisy positions.

| Recording | Fit measurements | Reserved prediction test |
|---|---|---|
| Clay coupon | Several small-strain shear load/hold/unload histories; measured force and displacement; measured area and gap | A different load level/hold duration and recovery history |
| Passive Hug | Actuator and orbital input off; releases in the chosen mode; force, displacement and initial velocity | Another displacement/velocity and documented clay memory |
| Actuator feedback | Actual actuator force, displacement, velocity and separately measured delay; several amplitudes | Independent motion/force recording using the same controller |
| Autonomous active Hug | No parameter fitting here | Different starts with external/orbit forces off; separate disturbance and recovery recordings |
| Circular orbital forcing | Keep fitted parameters fixed | Measured applied waveform, amplitude, period and phase, alongside motion |
| Eccentric orbital forcing | Keep fitted parameters fixed | Repeat separate waveforms/eccentricities; measure actual force rather than assuming a command was delivered |

Use fresh/conditioned specimens or track the accumulated Burgers memory explicitly. An unloaded specimen can retain permanent strain. `initial.known=true` is a declaration supported by the recording notes, not an instruction to fill unknowns with zero. For nonzero controller delay, this implementation requires a documented constant position/velocity history over the preceding delay interval. Other histories need an extended session format and delay solver before prediction.

Force columns separate measured **external force excluding actuator/orbit**, **actual active actuator force**, and **actual applied orbital waveform force**, all in newtons. Displacement and velocity are millimetres and millimetres per second; time is seconds. Align sensor signs and timestamps before entry. Empty cells remain null. Passive tests reject active/orbital force; autonomous tests reject continued external/orbital load. Put a push in a separate interval and document the state at its end.

## Physical-unit equations and assumptions

Clay follows the same Burgers internal law as the updated Hug:

```text
gamma = sigma/G_M + u + w
u_dot = (sigma - G_K u)/eta_K
w_dot = sigma/eta_M
```

For coupon calibration, `sigma = measured_force / coupon_area` and `gamma = displacement / coupon_gap`. The exact propagation uses piecewise-linear measured stress, retaining initial delayed strain u and permanent strain w. Four positive coefficients are fitted in log space. A normalized sensitivity rank/condition check rejects uninformative fits; it is a local diagnostic, not proof of global identifiability or an uncertainty interval.

For the assembled Hug, declare an **effective shear length L** and **effective sheared volume V** for the measured mode. These need a defensible geometric/mechanical mapping; arbitrary total specimen volume is not automatically an effective mode volume. The reduced model is:

```text
sigma = G_M (q/L - u - w)
m q_ddot + k q + (V/L) sigma = F_external + F_orbit + F_active
F_active = (a - b q(t-delay)^2) q_dot(t-delay)
```

Here q is metres, m is an effective mass in kilograms and k is parallel restoring stiffness in N/m. Actuator gain a is N·s/m; saturation b is N·s/m³. The transition amplitude is sqrt(a/b). No repeating actuator trajectory is imposed. Calibration does not assume the nondimensional 45.95-second rhythm from the earlier chosen model.

Fit clay first; then fit m and k using passive data with the clay fixed; then fit a and b from separately recorded feedback. Delay is a measured input, **not an estimated parameter**. The passive optimization warms up on the first tenth of fitting records (at least 12 samples) to reduce phase-basin errors, then fits all fitting rows. This is still a local optimization; wrong guesses or an inadequate model can fail. Parameter limits and rank failures remain errors, not passed tests.

Validation uses entire separate recordings. Creep and passive predictions use measured external loads; active predictions generate actuator force from predicted state, **never replay measured actuator force**. Orbital predictions are conditional on the measured applied waveform. They do not calibrate actual astronomical tides. Positive delays use a method-of-steps solver with declared history. Missing tolerances produce `tolerance_not_set`, not a pass. Empty templates produce `awaiting_measurements`.

Recorded crossing periods, displacement error and integrated measured actuator work are diagnostics. Work is over the whole recording, not automatically a cycle. Finite repeatable motion and passed displacement predictions alone do not prove a physical limit cycle. Check disturbance return, amplitude/period consistency across starts, bounded accumulated deformation, contact constraints and cycle energy with independent recordings before that stronger claim. Friction, drying, slip, changing geometry or actuator limits may require additional dynamics. Measurement uncertainty and parameter confidence intervals are not implemented; repeat trials and review residuals before applying fitted values outside the observed domain.

## Run privately

From the study folder with the pinned requirements installed:

```sh
python hug_calibration.py PATH_TO_MEASUREMENTS.json --output PATH_TO_PRIVATE_RESULTS
```

This writes `calibration_results.json` to the chosen folder, containing fit-trial IDs, local fit quality, coefficients, held-out predictions, errors and pending reasons. It does not edit `active_hug.py`, upload data, or publish any entered measurements. The origin is user-declared; software cannot authenticate that a recording came from a physical sensor. `physical_calibration_established` remains false for every synthetic session; for a declared physical session it means all specified prediction gates passed in this restricted mode, not independent authentication or proof of a physical cycle.

## Software verification with simulated measurements

[Synthetic session](calibration/synthetic_demo.json) · [known coefficients](calibration/synthetic_truth.json) · [saved calibration output](calibration/synthetic_results.json) · [automated tests](test_hug_calibration.py).

Fourteen independently generated, noiseless synthetic recordings include clay, passive motion, actuator characterization, two autonomous starts, circular input and two eccentric laboratory waveforms. Clay data use independent RK45 integration; passive/active motion use a separately written physical ODE. Fitted coefficients differ from starting guesses. Held-out corruption leaves fits unchanged and fails prediction; zero-load/equilibrium inputs fail identification; changed delays, unknown memory, missing force channels and invalid times are rejected. A delayed-control first interval is checked against an exact matrix-exponential solution. Measured active force is deliberately corrupted to verify that it is not a forward-motion input.

```sh
python calibration_demo.py
python -m unittest test_hug_calibration -v
node calibration/test_entry.cjs
python calibration_report.py
```

The entry conversion/validation logic and its HTML field/template contract are tested; an interactive browser preview is not part of these automated checks. A synthetic pass verifies this software pipeline for the selected fixtures, not noisy-data reliability or a physical Hug calibration.

The clay calibration approach is based on the [Cooke and van der Elst small-strain creep/recovery study](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2011GL050186). Measuring assembled dynamics and evaluating predictions connects to [MIT's system identification lab](https://ocw.mit.edu/courses/2-003-modeling-dynamics-and-control-i-spring-2005/pages/labs/lab_3/). The powered saturation law is a proposed [van der Pol-type feedback mechanism](https://www.scholarpedia.org/article/Van_der_Pol_model); these sources do not supply measurements for this Hug.
