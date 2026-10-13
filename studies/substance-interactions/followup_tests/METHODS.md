# Methods and limits of the follow-up tests

This batch tests three specific gaps in the earlier substance study: evolving fog-water inventory, polarization of a neutral droplet, and the empirical adequacy of the diffusion-only capture kernel. They are separate computational regimes. The particle calculation does not inherit evaporation or flow from the fog calculation.

## Evaporating fog and gas uptake

The compartment initially contains 1 m³ gas at 101325 Pa, liquid water at 0.5 g/m³ and monodisperse droplets of radius 5, 10 or 25 µm. Gas temperatures are 283.15, 298.15 and 308.15 K; initial relative humidities are 50, 90, 99, 99.5, 100 and 100.5%. The gas temperature is externally maintained. Rigid gas volume and background gas inventory are held fixed, so water vapor transfer changes the total pressure slightly; output pressure is diagnostic. Droplet volume is negligible compared with 1 m³. The gas is treated as well mixed and dilute, and droplets have no relative ventilation.

The water model is the quasi-steady Maxwell diffusion law:

`dm_drop/dt = −4π a Dv [rho_v,s(Td,a) − rho_v,gas]`.

For a constant liquid density, `d(a²)/dt = −2 Dv [rho_v,s − rho_v,gas]/rho_l`. A closed vapor reservoir receives exactly the water lost by the drops. Water vapor density uses the original Murphy–Koop saturation expression and the ideal-gas law. The optional Kelvin factor is `exp[2 sigma Mw/(rho_l R Td a)]`. Sigma = 0.072 N/m, rho_l = 1000 kg/m³ and latent heat Lv = 2.45 MJ/kg are rounded, fixed assumptions. Dv = 2.5e−5 (T/298.15)^1.8 m²/s and k_air = 0.026 (T/298.15)^0.8 W/(m K) are assumed transport approximations, with Dv sensitivity included.

Two thermal closures are compared: droplet temperature held equal to gas temperature, or quasi-steady conduction balancing latent heat:

`k_air (Tgas − Td) = Lv Dv [rho_v,s(Td,a) − rho_v,gas]`.

The second closure solves for Td at every evaluation. Integrated latent heat is supplied by or returned to the external temperature-control reservoir. This is a **quasi-steady energy accounting**, not a resolved transient heat equation: initial cooling, liquid sensible-heat storage, radiation and gas cooling are omitted. It also neglects Stefan flow, accommodation resistance, changes of water activity and changes in diffusivity caused by composition. Source: [Maxwell and thermal evaporation theory](https://doc.comsol.com/6.4/doc/com.comsol.help.particle/particle_ug_fluid_flow.08.54.html). The thermal balance is derived by equating spherical Fourier conduction with the stated mass flux.

Integration stops when radius reaches 2 µm. Remaining water and solute stay recorded at that boundary; the program does not force them to evaporate or become a dry residue. At high humidity a run can reach 30 s without hitting this cutoff. This is not a nucleation model; supersaturated runs start with existing drops.

CO, acetone, isoprene and H₂O₂ begin in the gas at 1, 1, 1 and 0.001 ppm. Their liquid and gas mole inventories are integrated separately with opposite transfer fluxes. For each species, `m = Hcp(Td) R Tgas`, `k_l = Dl/a`, `k_g = Dg/a`, `K_L = (1/k_l + m/k_g)^−1`, and `kLa = 3 K_L/a`. The transfer law is:

`dn_liquid/dt = kLa [m Vl n_gas/Vgas − n_liquid]`.

Henry constants and temperature slopes are the previously frozen [Sander compilation](https://doi.org/10.5194/acp-23-10901-2023) values. Dg = 2e−5 and Dl = 2e−9 m²/s remain assumed common diffusivities. This extends the original two-film closure, not a resolved radial liquid-diffusion calculation. The gas-temperature/interface-temperature use in this dilute closure is explicit; it is not a full nonisothermal multicomponent diffusion model. Henry constants and transfer coefficients are separately varied by factors 0.5, 1 and 2 to expose assumption dependence; these are scenario ranges, not confidence intervals.

No reactions or adsorption occur in this module. H₂O₂ is a soluble comparison; it is not assigned a decomposition rate. CO retains its identity. CO₂'s earlier equilibrium calculation is retained separately; a hydration/carbonate reaction transient is still pending.

Radau and BDF solutions are compared, with maximum steps 0.2, 0.1 and 0.05 s and tighter tolerances. There is no spatial grid in this compartment. Tests recover the analytic open-reservoir radius-squared law and the original fixed-water Henry transient, as well as saturation, no-transfer, condensation and conservation controls.

## Polarization, Brownian motion and drag

The electrostatic extension uses a point-charge aerosol outside a conducting sphere, from [Dépée et al. (2021), Part II, Eq. 10](https://doi.org/10.5194/acp-21-6963-2021). For aerosol charge q, droplet charge Q, droplet radius A and separation r, positive force points outward:

`F(r) = ke qQ/r² − ke q² A³ (2r² − A²) / [r³ (r² − A²)²]`.

The second term is induced polarization and is attractive even when Q = 0. The associated potential is:

`U(r) = ke qQ/r − ke q² A³ / [2r² (r² − A²)]`.

The image-force formula is exact for a point charge and an isolated conducting sphere; its use for a finite aerosol and liquid drop is an approximation. The finite aerosol's own polarization is omitted. Conductivity and charge relaxation are idealized, and the charges are prescribed. This model does not justify assigning these charges to actual fog or smoke.

Main cases use A = 10 µm, aerosol radius a = 100 nm, T = 298.15 K, pressure 101325 Pa, initial separation 30 µm and duration 1 s. Aerosol/droplet charges are (0,0), (50,0), (100,0), (100,1), (100,100) and (100,−100), in elementary-charge units. An extra (100,0) control disables polarization. The 100/1 case tests the competition between weak like-charge repulsion and induced attraction. The 100/100 case tests stronger repulsion. This does not generalize to arbitrary charged droplets or equal-sized particles.

The relative 3D stochastic equation is `dr_vector = (b_a+b_A) F(r) rhat dt + sqrt[2(D_a+D_A)] dW`. Mobilities use the original Stokes/slip implementation; D = kBT b. Air is quiescent; gravity, imposed flow, hydrodynamic coupling and evaporation are disabled. Constant spherical droplet size is a separate idealization. Like the original module, this is a force-isolation test rather than a cloud prediction.

Trajectories stop at r = 2A = 20 µm, well before physical contact at A+a = 10.1 µm. The crossing is located along the numerical displacement segment. The stop fraction is an **outer-boundary encounter statistic**, never a collision, capture or coalescence efficiency. Brownian crossings between sampled points can still be missed; step refinement quantifies sensitivity without proving exact first-passage convergence.

Each of seven main cases has six seeds and 512 independent paths per seed. Confidence intervals use Student's t across the six seed estimates. Paired differences use the same random increments as the neutral control. Refinement uses six additional seeds, q = 0 and 100, and steps 0.002, 0.001 and 0.0005 s, summing common fine Brownian increments for the coarser paths. These are paired refinements, not additional independent realizations at every step. Deterministic sensitivity spans T = 283.15–308.15 K, a = 50–200 nm and q = 20–100e.

Tests independently check the published image-charge expression, the negative potential gradient, charge-sign symmetry, the far-field dipole limit, the analytic Coulomb/Stokes trajectory, relative Einstein diffusion, and potential-energy loss against integrated drag dissipation. Stochastic thermal energy accounting is not claimed by the deterministic dissipation check.

## Published aerosol-capture measurements

[Dépée et al. (2021), Part I, Table 3](https://doi.org/10.5194/acp-21-6945-2021) supplies 18 central collection-efficiency values and wet aerosol radii, with three humidity groups. Values are transcribed in `measured_collection.json`, with attribution and source notes. This is sodium fluorescein aerosol, not a universal smoke composition. Group temperatures and droplet radii come from section 4.2; nominal droplet speed 0.25 m/s is approximate.

The unmodified physical closure from the old pilot is `K = 4π(Da+DA)(a+A) s`. It is converted to the experiment's swept-volume convention by `CE = K/(π A² U)`. Nominal sticking s = 1. This is deliberately an **adequacy challenge of a stagnant diffusion-only kernel against a falling-droplet experiment**. It does not reproduce the authors' full model, which includes additional mechanisms. The normalization does not insert ventilation, phoresis, interception or inertial impaction into our kernel.

No measurement is used to fit a rate, sticking factor or correction. Sensitivity varies speed from 0.2 to 0.3 m/s, temperature by ±0.5 K, droplet radius by ±1.3 µm and sticking from 0.5 to 1. This envelope is not a statistical confidence interval. Table 3 lacks the individual numerical error bars in this transcription, so chi-square and significance tests are not computed. Humidity ratios match the same dry-size selection, using the different measured wet radii. A mismatch identifies the limit of this closure, not a unique estimate of the omitted forces.

## Work still needed

1. Replace the failed collection closure with a falling-droplet model including flow, phoretic effects and finite-particle interception; compare to independent humidities and sizes before calling it validated for smoke.
2. Resolve liquid internal diffusion and test the evolving-fog/solute predictions against independent uptake and evaporation measurements under matching conditions.
3. Add CO₂ hydration/carbonate kinetics with validated forward/reverse rates and specified alkalinity; equilibrium pH alone does not validate the transient.
4. Use a fully specified catalyst, loading, temperature and pH before simulating H₂O₂ decomposition. Generic water or smoke cannot supply those parameters.
5. Obtain species- and surface-specific VOC adsorption data for soot/organic aerosol and ice, including aging and temperature limits.
6. Treat real charge distributions, charge relaxation, particle–particle hydrodynamics and near-contact physics before interpreting outer encounters as collisions or coalescence. Collective electrostatics, buoyancy and turbulence remain separate work.

All work here is computational or reanalysis of published data. These tests add no new chemical reaction law or Navier–Stokes law.
