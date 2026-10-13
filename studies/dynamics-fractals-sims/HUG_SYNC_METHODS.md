# Live loss and recovery of Hug synchronization

This experiment changes the restoring stiffness during continuous integrations of the existing synthetic active-clay Hug. It follows the earlier fixed-parameter robustness experiment. No physical clay observations or new SIMS participant runs are added.

## Intervention and controls

The orbital force, active feedback, material coefficients, mass and geometry remain fixed. The restoring stiffness is 0.7 N/m initially, rises to 1.4 N/m at elapsed 171 s, and returns to 0.7 N/m at 741 s. Each trajectory continues until 4,161 s. Two controls either retain baseline stiffness throughout or leave stiffness high after the first change.

Seven input shapes are tested: circular, Pasiphae (e = 0.412), Elara (0.212), Himalia (0.160), Europa (0.009), Callisto (0.007), and Thebe (0.018). All share a prescribed 5.7 s simulation orbit and force RMS of 6 μN. The names specify eccentricity; these are not real lunar periods or physical orbital loads.

Each arm continues both settled baseline histories from the verified robustness results at absolute simulation time 6,000 s. The 42 runs comprise 3 arms × 7 shapes × 2 histories. Those histories have already converged; they are not independent new basin samples. The orbital force uses absolute time 6,000 + elapsed time, preserving its phase.

At each stiffness step, displacement q, velocity, Kelvin strain u, and Maxwell dashpot strain w are continuous. There is no artificial reset, phase correction or forced return to a stored orbit. Acceleration changes. An external mechanism is assumed to change the spring; its work is included as ΔW = ½(k_after − k_before)q². Lowering stiffness can extract energy. The implementation tracks that work separately from active-feedback work, orbital work and clay dissipation.

## What counts as synchronization

States retain the existing normalization: [q/Q, qdot/Q, u/(Q/L), w/(Q/L)], where Q = 0.1 mm and L = 0.1 m. At one fixed orbital phase per orbit, compare all four state components with their values 1, 2, 3 and 4 orbits earlier. For each lag, the error is the maximum absolute difference over 20 successive comparisons, both histories and all components.

Synchronization is confirmed if at least one lag has error below 10⁻⁴, the two histories agree within 10⁻⁴ at the current orbital phase, and the motion is nontrivial. Each constant-stiffness stage starts a new confirmation window. Testing all four lags requires 24 stroboscopic states: the first assessment occurs 23 orbits, or 131.1 s, after a stage begins. Incomplete windows are marked **assessing**.

Reported loss and recovery times are confirmation times, not exact physical onset times. A recovery confirmation is the first assessed time after which every remaining assessment in the recovery stage passes. It is retrospectively checked through the full 4,161 s horizon. Times are resolved on the 5.7 s orbital grid and include the comparison-window delay. Brief shape overlap, a displacement-only repeat, or one passing sample does not establish synchronization. No 1–4 orbit repeat does not diagnose chaos or exclude longer repeats.

The saved summary distinguishes the restored arm from the controls. The unchanged arm is not described as “regaining” synchronization because it did not lose it. Resetting a diagnostic window does not change a simulated state.

## Numerical verification

Classical RK4 evaluates the orbital force at all four stages and splits exactly at both stiffness jumps. Sampling is every 0.05 s. The entire continuous path is compared at steps 0.00625 and 0.003125 s. The unchanged acceptance gates require full-state path differences below 2×10⁻⁴, scaled energy residual below 10⁻³, matching classifications, and confirmation-time agreement within one orbit.

Twenty-one independent physical-unit Radau checks span the raising step, the restoring step and late recovery for each orbital shape. Their four-component differences must remain below 2×10⁻⁵. Analytic tests also compare the passive, unforced piecewise linear system against exact matrix exponentials and check fourth-order convergence.

The initial 0.0125/0.00625 s calculation agreed on all classifications and confirmation times, but its maximum full-path difference was 9.2436×10⁻⁴, above the fixed 2×10⁻⁴ gate. The [initial audit](hug_sync_initial_audit.json) preserves this failure. The finer pair is used for the published results; thresholds and scientific parameters were not relaxed.

## Animation and plots

[Play the animation](hug_sync_player.html). It includes circular and all six eccentric inputs. The animation displays saved q values using the established shear display map x′ = x + 150(q/L)y, y′ = y. This magnifies deformation and preserves the original joins by construction; it is not a separate geometry/contact simulation. Numerical displacement labels are in actual model millimetres.

The faint outline is the same trajectory exactly one orbit earlier. The timeline shows the complete diagnostic, including waiting periods. Clips explicitly skip elapsed time to show the stiffness changes, confirmed loss and each recovery; transitions between clips are not physical jumps. There is no stitching of independently restarted dynamical runs. The status uses the most recent assessment; the GIF and player do not invent sub-orbit detection times. Errors below 10⁻¹² are shown at that plot floor.

- [Loss/recovery and control plot](figures/hug_sync_transitions.png)
- [Recovery confirmation delays](figures/hug_sync_recovery.png)
- [Protocol](hug_sync_protocol.json)
- [Numerical results](hug_sync_results.json)
- [Animation data](hug_sync_animation.json)
- [Executable tests](test_hug_sync.py)

## Reproduce

From the study folder with its requirements installed:

```sh
python hug_sync.py --cache-dir .sync-cache
python -m unittest test_hug_sync -v
python hug_sync_report.py --cache-dir .sync-cache
python hug_sync_report.py --cache-dir .sync-cache --gif-dir animation-export
```

The caches contain sampled full trajectories and are excluded from Git. Published animation data, source hashes, diagnostic timelines and control summaries are retained. The GIF export is optional; the repository includes the offline player. These tests establish behavior of this synthetic model under the selected intervention, not calibration of a physical Hug.
