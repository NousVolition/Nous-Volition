# Nous Volition · Streams and Rocks

This repository, **Streams and Rocks**, preserves the original stream-function report and a separate social-organization experiment.

## SIMS: names, memory, and group boundaries

**[Read the completed six-group SIMS study →](studies/social-organization/README.md)**

Ice, Water, Fog, Mist, Gas (water vapor), and Smoke are symbolic group labels in a
social analogy. **SIMS** are the simulated participants. The study includes 6,444 main/control simulations, 72 additional
diagnostic trajectories, numerical results, six charts, runnable Python scripts,
tests, and a proposed optional group-decision game.

- [Results and reproduction guide](studies/social-organization/README.md)
- [Accessible report](studies/social-organization/report.html) — download and open locally
- [Model and measurement specification](studies/social-organization/methods.html)
- [Optional group-decision game — proposed](studies/social-organization/human_protocol.html)
- [Recorded numerical outcomes](studies/social-organization/analysis/run_phase_metrics.csv)

Names alone changed nothing when semantic perception was disabled. In the full
model, combined stress reduced cooperation by 18.43 percentage points; memory
delayed rigidity recovery. These results describe the specified model's responses to stress and memory.

![Stress and recovery in the social model](studies/social-organization/analysis/recovery.png)

Current Navier–Stokes math, code, papers, and project status remain organized in
the separate project linked below.

## Start here

**[Open the organized project →](https://github.com/NousVolition/My-Sources-Project-ALL/tree/main)**

The project guide on the main branch leads to the corrected smooth field, finished results, and next steps. The organization changes were merged in [pull request #1](https://github.com/NousVolition/My-Sources-Project-ALL/pull/1).

## Original report

[Read the Stokes stream-function report](stokes_stream_report.pdf).

The stream function constructs an initial velocity field. The original radial Gaussian has an axis cusp when the ring radius is positive. The [corrected smooth-field derivation](https://github.com/NousVolition/My-Sources-Project-ALL/blob/main/math/notes/smooth-initial-field.md) supplies the smooth replacement and exact energy formula.

The maintained implementation lives in the shared workspace. The original PDF is preserved here as a record of the earlier construction.

## One position always fights back

[Open the resisting-position experiment](studies/one-resisting-position/README.md) for runnable simulations, saved results, assumptions, and volunteer-testing considerations. It compares a position that holds its initial color with one that actively opposes its neighbors, including ring and star networks and the difference between first and lasting agreement.

The study explores human coordination through nine **SIMS**, its simulated participants, using a Streams and Rocks analogy. The experiment runs independently using Python 3.12 and no third-party dependencies.

## Dynamics, fractals, and SIMS

[Open the dynamics and fractals test suite](studies/dynamics-fractals-sims/README.md) for three batches of mathematical experiments and 10,240 matched SIMS runs. It covers Lorenz sensitivity, phase space, damping, numerical integration, laser thresholds, Menger-sponge and Koch-snowflake networks, cusp hysteresis, the tilted-wire bead, budworm outbreaks, pitchforks, the rotating hoop, limit cycles, Sel’kov oscillations, van der Pol and Duffing, and averaging tests for damping, pendulums, and a pumped swing.

The package includes 59 automated tests, nine original scientific figures, saved numerical results, and an [illustrated report](studies/dynamics-fractals-sims/report.html) to download and open locally. Equations, selected parameters, and links to sources are documented alongside the code.
