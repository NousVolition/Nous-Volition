# Hug memory continuity: equations and limits

This is a synthetic, explicitly extended Hug model. It tests persistent records and bounded expression during a drive interruption. It does not model a person's trauma, infer inherited autobiographical memories, or calibrate any coefficient from adoption counts. The user's distinction between biological ancestry and the family providing care is preserved. Gender, adoption status, conformity and moral worth are not numerical model inputs.

## What is retained from the corrected corpus

Source: `Plain_Language_Corpus_Math_and_Logic_Corrected.docx`, SHA256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf`; Contents 5 and 10. Relevant Miro frames: [13, memory-to-force chain](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687916065203), [16, persistence after input stops](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055185), and [20, distinct activation laws](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055189).

The source has A'=gamma*(U-Ubaseline), J=kappa*A, and S_t+u.grad(S)=D Lap(S)+K_h J. Its force density is b=-sigma*a(|grad(S)|-Gamma)*e_k. The source does not require A or S to decay. With continuing excess input, its total field can grow quadratically. The requested finite limit therefore requires an explicit extension, not a claim that the unchanged source already guarantees bounded memory.

We retain accumulated input A separately for three routes, the original localized-source/transport/diffusion structure, and one explicitly selected source activation: smooth exact-off a(q)=0 for q<=0 and q*exp[-(epsilon/q)^2] otherwise. The signed-tanh and sharp laws are different alternatives, not silently combined. The force direction stays e_x. Source q is gradient excess, while mechanical displacement below is d.

## Persistent record and bounded expressed influence

The immutable event ledger records an event's origin, timing, channel, and whether the modeled recipient was directly present or received a communicated account. Children/descendants receive route-weighted influences, never a relabeling of someone else's event as their own direct experience. A is an accumulator, not the complete record: opposite inputs may cancel in A while both records remain in the ledger.

For each origin route r, A_r'=input_r. For the demonstrated hypothetical scenarios, the expressed source is

    j_r = j_max*tanh(kappa*A_r/j_max)
    D_t S = D*S_ss + sum_r w_r*K_r*j_r - lambda*S + I_pair.

The source cap and -lambda*S are **new choices authorized by the request for a limit**. They limit expressed influence; they do not delete the ledger or decay A. Stored input can sustain expression after current input stops. This is not literal conservation of an amount of human memory. If a path's communicated weight declines over generations, its present influence declines while its origin record remains. Re-exposure adds a separately identified event. No neurological timescale is assigned to simulation seconds.

Each K has spatial mean 1 on the ring. In the original dimensional normalization K_phys=K/V, J_r=V*j_r, so their product is unchanged. S and A are dimensionless declared model quantities; j, lambda, kappa and exchange rates have inverse-second units. Gamma and epsilon are in m^-1. The response coefficient sigma is in Pa, giving b units N/m^3. It is not the Burgers shear stress.

Route weights before budget normalization are (r_generation^g, caregiver_weight, neighbor_weight), then divided by max(1,sum(abs(weights))). The main generation-2 case uses r_generation=.55. A .9 sensitivity represents stronger persistence; neither is an estimated human inheritance rate. Altered caregiving changes an exposure sign, without changing ancestry. Both signs label modeled inputs, not good/bad people. Biological/epigenetic transmission is explicitly disabled: adoption reference data do not identify that mechanism or a usable coefficient.

## Doubling in the upper physical region

The reference Hug is a ring of radius .05 m. Upper/lower refer to its y coordinate. The pairing is reflection across the vertical axis. For equal-volume paired locations i and p(i),

    I_i = k*sign*sin(theta_i)_positive^2*s0*tanh((S_p(i)-S_i)/s0).

This is a **declared new bounded mirroring law**, not a formula extracted from the corpus. It is zero at and below the centreline for any finite states. Positive sign aligns paired fields; negative sign is an opposing-exchange sensitivity. It represents alternative feedback rules, not a claim that trauma causes harmful behavior. Pairwise terms sum to zero because the pairing and weights are symmetric. Ordinary diffusion still reaches the lower region. Lower motion and similarity do not establish a lower mimetic channel.

For |A| arbitrarily large, |j|<=j_max. With nonnegative discrete diffusion, zero initial S and lambda>0,

    |S| <= B = (j_max*max(K)+abs(k)*s0)/lambda.

At a positive maximum beyond B the derivative points inward; at a negative minimum it points inward as well. This includes the opposing sign. There is no clipping of computed states. This bound limits field amplitude; it does not imply all continuum gradients are bounded independently of spatial resolution. Spatial-force convergence is checked separately.

Reversing all S signs preserves |grad(S)| and therefore this force. The source law cannot on its own distinguish a beneficial from a harmful interpretation. That limitation remains visible rather than being repaired with a hidden sign rule.

## Clay coupling and declared reduction

The source's Newtonian momentum equation is not silently described as a Burgers clay law. This experiment uses its specified force density in a separately declared mechanical projection. Reference points (x,y) move by r=(x+d*y/L,y), with displacement mode phi=(y/L,0). Virtual work gives

    F_memory = integral(phi dot b) dV = -sigma*V*mean[(y/L)*a(q)].

This is a one-mode mechanical realization, not a solution of the complete moving-boundary Navier-Stokes equations or a contact/fracture model. S is represented along material coordinates, where D_t S becomes a time derivative. Diffusion and gradients use the reference arc length (a small-strain approximation). There is no extra strain feedback on the reference field, so equal exposure histories give equal material-coordinate S under different orbital inputs. The displayed deformation is magnified and cannot establish preserved physical contact.

The mechanical equations retain the earlier synthetic Burgers clay:

    tau = G_M*(d/L-e_K-e_M)
    e_K' = (tau-G_K*e_K)/eta_K; e_M'=tau/eta_M
    m*d'' + k_spring*d + (V/L)*tau
      = F_orbit + F_memory + (a-b*d^2)*d' - c_brake*d'.

During the intervention a=b=0 and c_brake=.8 N s/m. Otherwise c_brake=0 and the old active coefficients are restored. Stored clay strains, displacement, velocity, source A and field S are carried continuously across switches. The reset control alone sets working A and S to zero at release; its deleted values are recorded, and the external audit ledger is retained. This deliberately incorrect control is never applied to retained-history cases.

The force can supply or remove mechanical energy. Its work is integrated explicitly alongside orbital work, active work, brake loss and Burgers loss. It is not called a damper. The previous guard damper is not added; this is a new source-force realization, not an isolated test of the old guard coefficient.

The synthetic material values and force scale are in protocol.json. Published wet-kaolin Burgers fits motivated the earlier material class, but these parameters are not a calibration of the user's clay: [Cooke and van der Elst 2012](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2011GL050186).

## Protocol, controls and outcomes

Nine scenarios, three orbital conditions and two initial mechanical states give 54 main trajectories, including generations 0, 1, 2 and 3. These are matched hypothetical recipients, not a demographic simulation or measured parent-child dyads. Main grid 32, refined grid 64, and an independent time-refinement run at grid 32. A 128-cell check covers retained, opposing and stronger-transmission scenarios under all three inputs for the first start. Orbit period is always 5.7 s; force RMS is 6 micronewtons. The signed waveform is sin(2*true_anomaly)/(r/a)^3, preserving the previous Hug convention. Eccentricity .212 selects Elara-shaped forcing, not its real orbit, period or force. The orbit clock never resets.

Drive/braking intervention: 480–720 s. Later neighbor exposure: 950–970 s. End: 1800 s. No-pause controls receive the same exposures. Solver segments split exactly at every switch and event, preserving full state. DOP853 tolerances and step caps are specified before outcome analysis. Fine runs repeat initial conditions and exposures, not restart from main outputs.

Amplitude is displacement half-range over a trailing 57 s window. Baseline is the median over 350–450 s. Quiet means less than 10% of that path's baseline, and amplitude recovery means at least 80% sustained through the pre-reminder interval. These are operational finite-horizon diagnostics, not proofs of an autonomous limit cycle. Residual orbitally forced motion may persist while the active drive is off. A literal complete stop is not claimed.

For forced paths, sample scaled mechanical state once per orbit and compare to one orbit earlier over ten comparisons. Report repeat error and finite-horizon confirmations at tolerance .01; field drift is reported separately. This is a mechanical repeat diagnostic, not the earlier full-state four-lag criterion, so previous published confirmation times are not compared as equivalent measurements. No-orbit paths have no orbital synchronization label. Recovery after a later reminder is evaluated separately. Finite horizon, two starts and synthetic parameters do not establish universal recovery or behavior of people.

Numerical checks report actual temporal/spatial discrepancies, energy residuals, field bounds and retained-accumulator errors. Outcome changes and non-recovery are results, not test failures to hide. A scientific acceptance threshold is not tuned to force synchronization.

## Reproduce

Install requirements, then run `python -m unittest -v`, `python run.py --kind main --cache NEW_DIRECTORY`, followed by fine, timefine and spatial in that same new cache root. Run `python analyze.py --cache NEW_DIRECTORY`, `python render.py --cache NEW_DIRECTORY`, and `python verify_saved.py`. Run directories are not overwritten. The published display data are projections/downsamples of these saved numerical trajectories; the code and protocol regenerate full states. The reference adoption table is never read by model.py.
