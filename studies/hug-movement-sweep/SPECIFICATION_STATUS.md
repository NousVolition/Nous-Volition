# What has been specified, and what has not

The completed runs test a **declared reduced surrogate**, not the complete Hug field system in the corrected corpus. Saying that the sweep kept "the user's equations unchanged" was too broad. It kept the preceding surrogate unchanged while varying its movement parameters. The corpus accumulator and selected threshold response are retained, but the capped source, expression relaxation, angular reduction, pair exchange, active oscillator and Burgers mechanics are additional modeling choices.

The source reference is the corrected corpus with SHA-256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf` and the previously read mathematical sections of the [Miro board](https://miro.com/app/board/uXjVEXBJz3k=/). This clarification does not claim a new review of the entire board.

## Three distinct parts

1. **Corpus field laws.** The source describes velocity, pressure and a signed status/context field S; an accumulated source A'=gamma_source(U-U_baseline), J=kappa A; and a fixed-direction response to gradient excess. Its Newtonian momentum analogy is not a Burgers clay constitutive law.
2. **User's spatial design intent.** Mimetic interaction belongs in the upper physical region, with graded strength. Direct mimetic interaction is off in the lower region. Height selection is distinct from the corpus's gradient threshold.
3. **Assistant-added surrogate mechanisms.** The current code supplies an angular field, prescribed affine shear kinematics, a Burgers mechanical mode, capped source, expression relaxation and a particular pair-exchange rule. Their numerical behavior has been tested. Neither the corpus nor the read board sections supplies that pair-exchange evolution law or its clay coupling.

## Specification register

| Required item | What the existing surrogate actually uses | What remains to be specified for a full Hug field model |
|---|---|---|
| Domain | A periodic angular field on a reference ring of radius .05 m; one mechanical shear mode with L=.1 m and an assigned volume | The spatial fluid/solid regions, dimension, geometry, thickness and interfaces |
| Boundary conditions | Periodicity for S around the ring; the shape follows an affine map. There is no independently solved pressure/velocity boundary problem | Velocity or traction conditions, pressure constraint, S flux/value conditions, and external/interface conditions |
| Initial u and S | S=0 and A=0; mechanical velocity and internal Burgers strains start at zero. Displacement is .025 mm or -.14 mm times the movement setting; u=(d_dot Y/L,0) follows the mode | Spatial initial fields compatible with the chosen domain, boundaries, incompressibility and body geometry; pressure treatment |
| Meaning of S | A synthetic signed expressed-context variable, treated as dimensionless by convention | An operational definition, observable or measurement map, units and reference scale. No identification with clay strain, pressure, neurological memory or material microstructure has been established |
| U and accumulated input | Three fictional input-rate channels and a later pulse; A integrates these prescribed rates without decay or reset | What U measures, its units and baseline, gamma_source, spatial support and how observations determine them. The event rates do not separately identify U and gamma_source |
| Kernel K_h | Three material-label kernels proportional to exp[4(cos(theta-centre)-1)], normalized to angular mean one | Corpus K_h has unit spatial integral. The surrogate's dimensionless mean-one kernels are not that same normalization. Specify the domain measure, bandwidth h, source positions, physical normalization and any conversion of source strength |
| Source amplitude | j_r=jmax tanh(kappa A_r/jmax), combined with fixed route weights | This capped j_r replaces the corpus's linear J=kappa A in the surrogate. A full source-law run must preserve J or explicitly declare and test a revised law; the two are not interchangeable |
| Constants and units | Numerical coefficients are frozen in protocol.json; D is assigned m²/s, relaxation/exchange rates s^-1, and S/A are dimensionless conventions | An independently justified dimensional specification and calibration. Source strength units depend on S and the normalized spatial kernel |
| Force direction | Fixed negative horizontal direction: body force density b=-sigma_response a(q_excess)e_x, projected onto the shear mode | The physical meaning/orientation of e_k, density and force-versus-acceleration conventions. This force is not automatically opposite velocity |
| Response branch | Smooth exact-off: a(q)=0 for q<=0; q exp[-(epsilon/q)²] otherwise. Gamma=epsilon=1 m^-1 under the surrogate's dimensionless-S convention | Explicit choice between sharp exact-off, original signed tanh and smooth exact-off for the intended field run. These branches have different below-threshold behavior |
| Gradient regularization | Unregularized magnitude: q_excess=sqrt(g)|partial_s S|-Gamma; no delta regularization | Choose original magnitude, shifted-cutoff regularization, or cutoff-preserving regularization, and state delta and its units. Epsilon smooths the scalar response; it is not delta |
| Clay constitutive law | An added linear Burgers element with assigned moduli/viscosities, plus a spring, effective inertia and powered feedback | A stated material law with its strain range, state variables and calibration. The effective oscillator mass is not a material density inferred from the assigned volume |
| Fluid/body coupling | Affine x=X+(d/L)Y, y=Y; u follows d_dot. A projected field force drives the mechanical mode. There is no resolved fluid traction/contact solution | Kinematic interface conditions, stress/traction balance, possible slip/permeability, transport across the interface and an energy-consistent coupling to the chosen solid law |
| Mimetic evolution and material coupling | The added exchange term below acts on S and influences motion indirectly through the projected field force | A separately stated doubling state, pairing rule, graded physical-position weighting, evolution law and coupling. The user's spatial intent alone does not specify these mechanisms |

The source force coefficient sigma_response is distinct from clay stress tau. With the surrogate's dimensionless S, a has units m^-1 and its assigned sigma_response in Pa makes b a force density (N/m³); the mode force is its weighted volume projection. This is a dimensional convention for the surrogate, not a physical identification of S or a derivation of a clay material law from the corpus.

## Keep mimetic interaction separate from the source and force

The existing assistant-added exchange is

    I_pair,i = k_pair w_i S_pair tanh((S_partner(i)-S_i)/S_pair)
    w_i = max(sin(theta_i),0)^2,

with reflected angular partners and positive exchange sign in this sweep. It is graded in the upper region and exactly zero at each lower location for arbitrary finite local states. Both directed terms of a lower pair are zero. The tests establish this property of this proposed exchange rule; they do not establish that it is a Girardian doubling law.

Here y=Y, so upper/lower membership is unchanged by the affine shear. A different motion, including rigid rotation, would require an explicit rule based on current physical position and a defined "up" direction. The existing material-label weight cannot silently be reused for that geometry.

I_pair is a **separate added interaction operator**, not K_h J, not the source's accumulated-input variable, and not the gradient-threshold force. Expression relaxation -lambda S is another added term. Pair exchange and diffusion redistribute S; the source and relaxation can change its mean. Retaining A and the event catalog is different from conserving every value of S.

## Consequence for the testing structure

Before describing a new run as the full corpus Hug field simulation, complete the missing field/material/interface specification and keep every added mechanism labeled separately. Choices can be proposed and tested as hypotheses, but should not be attributed to the document or board without support.

The existing plots and recovery results remain valid as numerical results of their stated surrogate. They do not establish the behavior of an unspecified full Hug field model, a physical clay sample, or a validated theory of mimetic doubling. This clarification changes documentation, not equations, parameters or saved numerical outcomes.
