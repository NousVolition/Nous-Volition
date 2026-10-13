# Methods and evidence boundaries

This batch advances all six items in the follow-up backlog, but does not close all six validation gaps. Computations are separate regimes. Rates, phase properties and particle populations are not silently shared between them. Everything is computational or a reanalysis of published information.

## Falling droplets and aerosol collection

`falling_capture` samples uniform-area incoming particles in the droplet frame and weights them by the local incoming advective flux. The stationary sphere has radius A; far-field air speed is U. Its prescribed incompressible creeping-flow solution is

`u/U = (1 - 3A/(4r) - A^3/(4r^3)) ez + (-3A/(4r) + 3A^3/(4r^3)) cos(theta) er`.

The overdamped particle drift adds thermophoresis and diffusiophoresis from [Dépée Part I, Eq.12](https://doi.org/10.5194/acp-21-6945-2021), using spherical thermal/vapor gradients. Stokes-Cunningham mobility converts force to velocity, and Einstein diffusion supplies Brownian increments. Midpoint stepping treats deterministic drift; random increments are Gaussian. Interception is at centre distance A+a, with unit sticking as an explicit absorbing-boundary assumption. A line-segment intersection detects crossings between step endpoints, although unresolved Brownian excursions can still be missed.

CE is incoming captured flux divided by `pi A² U`. Injection is at z=-8A, with a disk radius0.6A. Escape occurs at z=8A. Main runs terminate at250A/U; uncaptured/unescaped trajectories are censored, and their entire incoming flux gives a conservative unresolved contribution for that disk. Four seeds with4096 paths each are used per observed condition. CIs are Student-t intervals across four estimates, describing sampling error only. Refinement runs reuse seed numbers but changing active sets/steps means they are **not paired Brownian paths**.

All18 Table3 observations are held out from fitting, though they already motivated this model's structure in the earlier batch. Calling them untouched model-selection holdouts would be incorrect. Wider injection disk, more distant planes, longer time, smaller/larger steps, U=0.2/0.3m/s, no-phoresis, no-Brownian and zero-size interception controls are included. These finite controls cannot prove that all tails and first passages are resolved.

**This candidate is not the authors' validated solver.** At their measured sizes/speeds our Reynolds numbers are order unity, outside the strict creeping-flow limit. Particle inertia, settling relative to air, droplet deformation/internal circulation, evolving radius during encounter, and flow-distorted temperature/vapor fields are omitted. Default ventilation factors are1; equal1.2 factors are an explicitly assumed sensitivity, not a fitted correction. The thermal conductivity0.43W/(m K) applies to sodium fluorescein. A separate10micrometre-drop,0.012m/s pilot probes a lower Reynolds number but has no matched observations. Successful absorption at A+a is a capture assumption; this is not a coalescence prediction.

## Resolved liquid diffusion in evolving fog

Initial gas volume1m³, pressure101325Pa, T298.15K, liquid water0.5g/m³, droplet radius10micrometres; RH50,90,99%. Water geometry follows the earlier closed-reservoir evaporation model and stops at2micrometres or10s. The thermal closure balances spherical conduction with latent heat. Gas temperature is externally maintained. It does not resolve initial thermal relaxation, sensible heat, gas transients or composition-dependent water activity. Solutes remain dilute and do not alter water properties.

For each solute, the sphere is divided into40 radial shells with boundaries `r_j=A(t)j/N`. State variables are independent shell and gas inventories, each normalized to the initial total number of solute moles. Shell concentrations are obtained by division by the changing physical shell volumes. With zero bulk liquid velocity, the outward flux relative to each moving internal face is

`J = -Dl dc/dr - rdot_face c_upwind`.

Flux times face area is transferred with opposite signs between adjacent shells. Central differencing resolves diffusion; upwinding resolves mesh-relative advection. At the outer surface the relative flux equals the negative incoming gas flux, giving

`cs = [(Dl/delta)c_last + kg cg] / [Dl/delta + Adot + kg/m]`,

`incoming = 4 pi A² N_d kg (cg - cs/m)`.

Here `m=Hcp(Td)RTgas`; `delta=A/(2N)` and `kg=[A/Dg + 4/(alpha*cbar)]^-1`. The accommodation correction is a simple gas/interface series resistance; no full transition-regime gas solver is claimed. Main alpha=1; Dl=2e-9 and Dg=2e-5m²/s are assumed, with Dl and acetone-alpha sensitivities. CO/acetone/isoprene start at1ppm, H2O2 at0.001ppm; linear normalized calculations use the same fractions for any sufficiently dilute loading. There is no chemical conversion in this module.

The fixed-surface sphere benchmark is `mean(c)=1-(6/pi²)sum exp(-n²pi²Dt/A²)/n²`. Grid checks use20,40,80,160 shells. A nonvolatile receding-boundary test preserves dissolved inventory. Opposite gas/liquid flux accounting and an independently integrated transfer total are audited.

The acetone accommodation range comes from the authors' [single-drop report, p73](https://www.tropos.de/fileadmin/user_upload/Aktuelles/Publikationen_Berichte/Berichte/Daten_PDF/IFT_JB2003.pdf). That experiment used helium at10kPa and suppressed evaporation; it cannot validate this air/fog transient. [Hardy2023](https://doi.org/10.1021/acs.jpcb.2c08909) identifies suitable independent water measurements, but measured time series with complete matching metadata were not recovered. The related Zenodo6396580 profiles are simulated and were rejected as experimental evidence. Matched solute uptake and evaporation validation remain open.

## CO2 hydration/carbonate transient

Four ideal dilute closed-liquid scenarios start with0.2mmol/L dissolved CO2 and alkalinity0,0.05,0.10,0.20mmol/L at25C. No gas transfer is modeled here. Reversible water and hydroxide routes are

`CO2(aq) <-> H2CO3`, `CO2(aq)+OH- <-> HCO3-`.

Forward/reverse rates from [Wang2010 Table1](https://doi.org/10.1021/jp909019u) are0.037/s,24.8/s,12100L/(mol s),0.00040/s. These are literature-constrained rates, not rates fitted here. The0.037/s value already incorporates bulk water concentration: do not multiply it by55.6 again.

We independently integrate CO2 and the hydrated pool B=H2CO3+HCO3-+CO3--. At every RHS evaluation, fast acid-base equilibria and the specified alkalinity determine pH and B's speciation. Kw=1e-14(mol/L)² and bicarbonate dissociation K2=10^-10.33mol/L. True carbonic-acid K1 is derived from the four rounded rates to enforce detailed balance, giving pKa close to the published3.70; it is **not** the apparent CO2-star pKa6.35. The two chemical routes are separately accumulated.

Rate sensitivities multiply each forward/reverse pair together by0.5/2, keeping equilibrium unchanged. They are scenarios, not confidence intervals. Individual routes and both routes can be disabled. Analytic fixed-pH relaxation, alkalinity, carbon conservation, stationarity and step refinement are checked. Actual stopped-flow data/indicator absorption are not reproduced; activity corrections, catalysts, salinity and T dependence are not included. Thus this establishes a verified implementation of published kinetics, not new independent experimental validation of the transient.

## H2O2: specified catalyst, rejected source consistency

[Akhtar2012](https://jcsp.org.pk/ArticleUpload/4144-20045-1-CE.pdf) supplies washed Merck MnO2, BET6.5m²/g, loading0.333g/L,303.15K, initial H2O2 .020mol/L, dark stirred water, HCl/NH4OH-adjusted pH. We reproduce only the unambiguous aqueous Table1 entries atpH3,5,8,10, without extrapolation. The net stoichiometry `2H2O2 -> 2H2O + O2` conserves H/O atoms.

**The rate audit fails:** atpH3 the table's0.009/min predicts4.4% loss at5min, whereas a coarse Fig4 reading is about45% (reading tolerance5 percentage points). The30min comparison also disagrees. These are within-source checks, not independent validation. Fig6 also labels increasing curves as log(a-x), and the text/table disagree on6.35/6.5. We exclude ambiguous pH/temperature entries. The four numeric curves demonstrate consequences of the tabulated rates; they are not accepted predictions for real peroxide decomposition. Generic water/smoke has no assigned catalyst rate. Heat and oxygen bubble dynamics are not simulated.

## VOC surface specificity and ice aging

[Behr2006](https://doi.org/10.1021/jp0563742) supplies acetone coefficients on vapor-deposited ice at190-220K. We compute reversible two-site equilibrium and relaxation rates using `ka/kd` consistently. Fresh ice uses the reported site1 upper capacity bound plus site2; aged ice retains site2. Twenty-one T/concentration combinations compare these endpoints. There is no invented aging clock and no extension to other VOCs or surfaces.

[Roth2005](https://doi.org/10.1021/es049204w) supplies diesel-soot and road-tunnel aerosol data. Nine numerical rows from the [official supporting information, Tables S2/S3](https://acs.figshare.com/articles/journal_contribution/3270178) were recovered and visually checked. At 15 C and 50% RH the acetone coefficients are 10^-5.08 m3/m2 on diesel soot and 10^-3.64 m3/g organic carbon on mixed road-tunnel aerosol. These normalizations are different: the second includes mixed sorption mechanisms and must not be represented as pure organic-phase absorption. The equilibrium closed-inventory fraction is capacity/(1+capacity), with capacity K*area/Vgas or K*grams_OC/Vgas, respectively. Forty-six loading scenarios propagate the source's reported log10 errors without assigning a new confidence interpretation. `surface_data.json` records the exact rows, units, conditions and source PDF checksum; the PDF is not redistributed.

The source also supports an ethanol humidity comparison at 50/70% RH. Acetone, 2-butanone, ethanol and isopropanol are included; **isopropanol is not isoprene**. The code rejects extrapolation outside each row's temperature/humidity and rejects mixed coefficient normalizations. No adsorption/desorption rate pair, soot-aging law, isoprene coefficient, or general temperature law was recovered. The [1997 oil-furnace study](https://doi.org/10.1016/S1352-2310(97)00048-4) concerns a different composition and is not transferred. Gas dissolution, surface adsorption and absorption into organic matter remain distinct mechanisms. These equilibrium calculations reuse measured coefficients; they are not independent predictive validation.

## Charge distribution, relaxation and approach to contact

A normalized discrete capacitive Boltzmann distribution is tested at50,100,200nm aerosol radius,298.15K and specified ion-mobility ratio0.875. It is a theoretical equilibrium scenario, not a measured smoke distribution or a full small-charge bipolar charging model. This prevents interpreting earlier arbitrarily prescribed50e/100e aerosol charges as typical atmospheric values.

Internal dielectric relaxation is `tau=epsilon_liquid/sigma_liquid`: it redistributes charge within a droplet but **does not remove its isolated net charge**. Conductivity scenarios5.5e-6,1e-4,1e-2S/m are assumptions. A separately specified Ohmic conducting ambient gives net-charge leakage `Q=Q0 exp(-sigma_air t/epsilon0)`; ambient conductivity is varied0-1e-12S/m. This idealization omits discrete ion attachment, corona, ion depletion and emission. No measured charge-relaxation time is inferred.

A separate two-sphere diagnostic has10micrometre radii, immobilized interfaces, viscosity1.84e-5Pa s and constant inward force1pN. We integrate pair Stokes resistance plus the leading normal [lubrication resistance](https://cronfa.swan.ac.uk/Record/cronfa26482/Download/0026482-22022016144620.pdf). Quadrature is checked against

`t = (6 pi mu a_eff/F)[h0-h1+a_eff ln(h0/h1)]`, `a_eff=aA/(a+A)`.

The smallest stop gap is0.67micrometre, about ten air mean-free paths. The no-slip interpolation is approximate even there and is not a complete mobility tensor. It never reaches contact. The applied force isolates drag physics; it is not an exact near-contact electrical force between conducting drops. Rarefied lubrication, finite-sphere polarization, surface chemistry, film drainage/rupture and deformation are still needed for collisions/coalescence. No collective electrostatics, buoyancy-driven flow or turbulence calculation is included.

## Reproduction and auditing

From this folder: `python test_advanced.py`, `python -m unittest surface_partition -v`, `python run_advanced.py`, `python surface_partition.py`, `python build_report.py`, then `python verify_package.py`. Runtime packages are pinned in requirements.txt; input SHA256 hashes and compressed trajectories accompany CSVs. Random seeds and case settings are in the driver. The source PDFs are not republished. Historical result packages remain unchanged. Passing unit tests establishes numerical checks within these models, not experimental validation.

The initial batch completed every numerical case and saved its CSVs, plots and trajectory archive, then failed while serializing a NumPy boolean into the headline JSON summary. The repaired driver supports `python run_advanced.py --finalize-existing`, which rebuilt the summary from saved CSVs. The original failure log is retained with local machine paths removed. Numerical cases were not silently rerun or replaced. `verify_package.py` separately audits saved results, links and the packaged hashes. The manifest records the delivered snapshot; after deliberately rerunning files, use `python verify_package.py --refresh-manifest` to create a new local snapshot.
