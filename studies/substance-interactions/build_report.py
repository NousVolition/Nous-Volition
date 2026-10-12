"""Generate the complete interaction matrix and a self-contained HTML report."""
import base64,csv,html,itertools,json
from pathlib import Path
from model import saturation, R

ROOT=Path(__file__).resolve().parent; RES=ROOT/'results'
CFG=json.loads((ROOT/'config.json').read_text());REF=json.loads((ROOT/'references.json').read_text())
def readcsv(name):
    with open(RES/name,encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def writecsv(path,rows):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader();w.writerows(rows)
def fmt(x):return f'{float(x):.5g}'
def esc(s):return html.escape(str(s))


def matrix():
    names=['CO','CO2','N2','O2','air','acetone','isoprene','H2O2','water_vapor','liquid_water','fog','mist','ice','smoke']
    gas=set(names[:9]);liquid={'liquid_water','fog','mist'}
    parts={(r['species'],r['medium']):r for r in readcsv('partition_results.csv')}
    cs={r['medium']:r for r in readcsv('carbonate_results.csv')}
    rows=[]
    conc='CO 1 ppm; CO2 420 ppm; acetone/isoprene 1 ppm each; H2O2 1 ppb (separate dilute pair tests). N2/O2 dry fractions 0.78084/0.20946. Water vapor from RH.'
    for i,(a,b) in enumerate(itertools.combinations_with_replacement(names,2),1):
        pair={a,b}
        z=dict(case_id=f'P{i:03}',substance_A=a,substance_B=b,scenario='baseline_pair',
            T_K=298.15,P_Pa=101325,RH_water_percent=50,timescale_s=600,
            concentrations=conc,geometry='1 m3 gas; when present: 1 L bulk water or 0.5 g suspended water; fog radius10um, mist25um; smoke surrogate100nm radius,1e9/m3',
            dominant_mechanism='',chemical_transformation='No reaction included under specified clean, dark, catalyst-free conditions',
            explicit_reaction='none',partition_or_transport_metric='',metric_value='',metric_unit='',
            rate_or_timescale='',force_attraction_or_repulsion='No imposed net electrostatic force; neutral does not imply absence of microscopic interactions',
            transient_or_equilibrium='',status='ASSESSED_NOT_SIMULATED',result_file='',
            limitations='No flames, UV, OH, ozone, catalytic contaminants, biological activity or reactive surface specification',source_ids='')
        if a in gas and b in gas:
            z.update(dominant_mechanism='advection/diffusion/gas mixing',
                partition_or_transport_metric='benchmark tracer diffusivity (assumed, not measured for every pair)',
                metric_value=2e-5,metric_unit='m2/s',rate_or_timescale='L=0.1m: L^2/D=500s; advective crossing L/u=10s at u=0.01m/s',
                transient_or_equilibrium='Concentration gradients relax; species remain mixed',
                limitations=z['limitations']+'; gas diffusion coefficients depend on pair and T. Same-species diagonal denotes transport of a label only.')
            if 'CO' in pair and ('air' in pair or 'water_vapor' in pair):
                z.update(status='SIMULATED_PASSIVE_TRANSPORT',timescale_s=2,RH_water_percent='0;50;100',
                    result_file='results/transport_controls.csv',source_ids='model.py analytic Fourier solution',
                    limitations='Fixed D and flow across RH controls; no reaction law for CO+water is introduced; no condensation in gas-only case')
            if 'O2' in pair and pair & {'CO','acetone','isoprene'}:
                z['chemical_transformation']='No oxidation on modeled short ambient timescale without an initiator/catalyst; thermodynamic favorability does not determine rate'
            if 'H2O2' in pair:
                z['chemical_transformation']='No reaction in inert benchmark; reactive pathways require specified light, radicals, catalysts or solution chemistry'
        elif (a in gas and b in liquid) or (b in gas and a in liquid):
            s=a if a in gas else b;med=b if b in liquid else a;mode='bulk' if med=='liquid_water' else med
            z['RH_water_percent']=100
            if s in ['CO','CO2','N2','O2','acetone','isoprene','H2O2']:
                r=parts[(s,mode)]
                z.update(dominant_mechanism='gas-to-liquid absorption / reversible Henry partitioning',
                    partition_or_transport_metric='equilibrium solute inventory in liquid',metric_value=r['equilibrium_aqueous_percent'],metric_unit='percent',
                    rate_or_timescale=f"relaxation {fmt(r['relaxation_rate_s_1'])} s^-1; t90 {fmt(r['t90_s'])} s (assumed film model)",
                    transient_or_equilibrium='Transient integrated to600s and equilibrium solved',status='SIMULATED_PARTITION',
                    result_file='results/partition_results.csv',source_ids='Sander2023;'+s+'_H',
                    limitations='Initially solute-free liquid; fixed volume and T; dilute solution; no salt; prescribed film coefficients. Film transient is a reduced closure, not a resolved internal droplet diffusion solution.')
                if s=='CO2':
                    c=cs['bulk' if mode=='bulk' else 'fog']
                    z.update(dominant_mechanism='absorption + carbonate acid-base equilibrium',
                        chemical_transformation='Yes: hydration/acid-base redistribution after dissolution',
                        explicit_reaction='CO2* + H2O <=> H+ + HCO3-; HCO3- <=> H+ + CO3^2- (CO2* lumps CO2(aq)+H2CO3)',
                        metric_value=c['aqueous_percent'],
                        rate_or_timescale=f"pH {fmt(c['pH'])}; carbonate equilibrium only. Physical transfer t90 {fmt(r['t90_s'])}s excludes reaction enhancement/hydration delay.",
                        status='SIMULATED_PHYSICAL_TRANSFER_AND_SEPARATE_EQUILIBRIUM',result_file='results/partition_results.csv;results/carbonate_results.csv',
                        source_ids='CO2_H;USGS2012',limitations=z['limitations']+'; no coupled carbonate transient or alkalinity buffer. Mist equilibrium inferred from same water volume, not separately solved.')
                if s=='H2O2':
                    z['chemical_transformation']='Dissolution/dilution preserves H2O2 identity in control; catalytic decomposition is a separate conditional case'
            elif s=='water_vapor':
                z.update(dominant_mechanism='condensation/evaporation at liquid interface',RH_water_percent='50;95;100;105',
                    geometry='Flat-interface benchmark:0.001m3 gas,0.01m2 water area,10g condensed reservoir; no individual fog/mist droplet resolution',
                    partition_or_transport_metric='saturation vapor pressure at298.15K',metric_value=saturation(298.15),metric_unit='Pa',
                    rate_or_timescale='Flat-interface benchmark relaxation0.01s^-1; droplet lifetime not modeled',
                    transient_or_equilibrium='Transient vapor approaches saturation if condensed water remains',
                    status='SIMULATED_FLAT_INTERFACE_ONLY',result_file='results/water_phase_results.csv',source_ids='MurphyKoop2005',
                    limitations='Thermostatted flat interface; no Kelvin curvature, solute effects, evolving droplet size or nucleation. Benchmark is not a fog evaporation-time prediction.')
            else:
                z.update(dominant_mechanism='carrier-gas mixing + componentwise dissolution',
                    partition_or_transport_metric='N2/O2/CO2 separate solubilities',rate_or_timescale='See component rows; no single Henry constant for air',
                    transient_or_equilibrium='Component-specific approach to partition equilibrium',status='COMPONENT_MODELS_RUN',
                    result_file='results/partition_results.csv',source_ids='N2_H;O2_H;CO2_H',
                    limitations='Air is a mixture; vapor evaporation and species exchange require separate balances; bulk air is not one reactant')
        elif 'ice' in pair:
            other=b if a=='ice' else a
            z.update(T_K=263.15,RH_water_percent=95,
                dominant_mechanism='surface encounter/possible reversible sorption',
                rate_or_timescale='No transferable sorption coefficient available for this surface/species',
                transient_or_equilibrium='Sorption may be transient or equilibrium; unquantified',
                source_ids='Crowley2010',limitations='Ice is solid water. Liquid-water Henry constants do not specify ice sorption; surface area, impurities and temperature required.')
            if other in ['water_vapor','air']:
                z.update(dominant_mechanism='vapor deposition/sublimation at ice surface',
                    geometry='0.001m3 gas,0.01m2 planar ice,10g initial ice reservoir',
                    partition_or_transport_metric='ice saturation vapor pressure',metric_value=saturation(263.15,True),metric_unit='Pa',
                    rate_or_timescale='Flat-interface relaxation0.01s^-1; RHice exceeds100% here',
                    status='SIMULATED_INTERFACE',result_file='results/water_phase_results.csv',source_ids='MurphyKoop2005',
                    transient_or_equilibrium='Deposition until vapor reaches ice saturation',
                    limitations='0.001m3 gas,0.01m2 planar ice,transfer velocity0.001m/s; thermostatted. Air case acts through its water vapor.')
            elif other=='acetone':
                ice=next(r for r in readcsv('ice_adsorption_results.csv') if float(r['T_K'])==210 and float(r['surface_area_m2'])==1)
                z.update(T_K=210,RH_water_percent=100*saturation(210,True)/saturation(210),
                    geometry='1m3 perfectly mixed gas,1m2 ice surface; fixed ice temperature and geometry',
                    concentrations='Acetone1ppb in1m3 gas, ice area1m2; two site capacities1e18 and6e18 per m2',
                    dominant_mechanism='two-site physical adsorption/desorption',
                    partition_or_transport_metric='initial acetone inventory adsorbed at600s',metric_value=ice['final_adsorbed_percent'],metric_unit='percent',
                    rate_or_timescale=f"kdes1={fmt(ice['k_des1_s_1'])}s^-1; kdes2={fmt(ice['k_des2_s_1'])}s^-1; full kads in results",
                    status='SIMULATED_SURFACE_KINETICS',result_file='results/ice_adsorption_results.csv',source_ids='IceAcetone2006',
                    transient_or_equilibrium='Adsorption transient reaches kinetic equilibrium',
                    limitations='190-220K fit only; site1 capacity assumed at reported upper bound; no gas boundary layer; well-mixed surface-access upper-limit model; preparation/aging important')
            elif other in liquid:
                z.update(T_K=273.15,RH_water_percent=100,dominant_mechanism='freezing/melting and optional contact collection',
                    geometry='10g seeded condensed-phase inventory at its melting point; no spatial collision geometry',
                    partition_or_transport_metric='converted water mass at600s under +/-5W',metric_value=5*600/334000,metric_unit='kg',
                    concentrations='10g pure water/ice, seeded interface, prescribed heat removal/addition5W',
                    rate_or_timescale='334kJ/kg rounded latent heat; full10g transition668s',
                    transient_or_equilibrium='Energy-limited phase conversion',status='CALCULATED_PHASE_CHANGE_ONLY',
                    result_file='results/freezing_melting_results.csv',source_ids='model.py energy balance',
                    limitations='At melting point; excludes nucleation and supercooling. Fog/mist riming collision efficiency and freezing probability not simulated.')
            elif other=='ice':
                z.update(dominant_mechanism='collision, possible aggregation/sintering; vapor redistribution',
                    chemical_transformation='No new molecular species from joining ice crystals',
                    limitations='Crystal habit, collision efficiency, surface temperature and sintering kinetics unspecified')
            elif other=='smoke':
                z.update(dominant_mechanism='particle interception/attachment; possible heterogeneous ice nucleation',
                    chemical_transformation='No generic smoke+ice reaction can be assigned',
                    limitations='Smoke composition and ice-nucleating activity unspecified; no rate or nucleation prediction')
        elif 'smoke' in pair:
            other=b if a=='smoke' else a
            z.update(dominant_mechanism='gas/aerosol transport and surface encounters',
                chemical_transformation='Composition-dependent; inert surrogate has none',
                rate_or_timescale='Not quantified without surface area, composition, sticking and reaction data',
                transient_or_equilibrium='Transport transient; surface residence may be reversible',
                source_ids='Gilardoni2014;Depee2021',
                limitations='Smoke is heterogeneous particles plus gases; no universal smoke molecule, Henry constant or adsorption coefficient')
            if other in ['fog','mist']:
                drop=1e-5 if other=='fog' else 25e-6
                sc=next(r for r in readcsv('smoke_scavenging.csv') if float(r['smoke_radius_m'])==1e-7 and float(r['drop_radius_m'])==drop and float(r['sticking'])==1)
                z.update(RH_water_percent=100,dominant_mechanism='diffusion-only aerosol scavenging by droplets',
                    partition_or_transport_metric='particle material captured after600s',metric_value=100*float(sc['captured_fraction_600s']),metric_unit='percent',
                    rate_or_timescale=f"idealized capture rate={fmt(sc['rate_s_1'])}s^-1; K={fmt(sc['kernel_m3_s'])}m3/s",
                    status='CALCULATED_KERNEL_AND_TRANSPORT_PILOT',result_file='results/smoke_scavenging.csv',
                    limitations='Perfect sticking upper comparison for diffusion channel only; no activation, impaction, hydrodynamic shielding, phoresis, charge or evolving water inventory. Not an upper bound on total real scavenging.')
            elif other=='smoke':
                z.update(dominant_mechanism='Brownian agglomeration/coagulation',
                    rate_or_timescale='Smoluchowski constant-kernel N(t)=N0/(1+KN0t/2); assumed sticking0,0.1,1',
                    status='ANALYTIC_POPULATION_BALANCE',result_file='results/agglomeration_coalescence.csv',
                    transient_or_equilibrium='Particle number falls; particle material mass conserved',
                    limitations='Monodisperse inert surrogate; constant kernel ignores evolving geometry, restructuring and chemical aging')
            elif other in ['acetone','isoprene','H2O2','CO','CO2']:
                z['dominant_mechanism']='possible surface adsorption/desorption or absorption into particle organic/water phase'
            elif other=='water_vapor':
                z['dominant_mechanism']='hygroscopic water uptake/condensation or evaporation depending on composition and RH'
            elif other in ['air','N2','O2']:
                z.update(dominant_mechanism='advection, diffusion and drag; gravitational settling',
                    status='SURROGATE_TRANSPORT_ONLY',result_file='results/transport_controls.csv;results/conservation_budgets.csv')
            elif other=='liquid_water':
                z['dominant_mechanism']='wetting, deposition, flotation/sedimentation and dissolution of soluble smoke components'
        elif a in liquid and b in liquid:
            z.update(RH_water_percent=100,dominant_mechanism='same-phase liquid mixing or droplet collision/coalescence',
                chemical_transformation='No new molecule when water combines with water',
                rate_or_timescale='Coalescence requires encounter and successful liquid-film drainage; same-size Brownian kernel comparison provided',
                transient_or_equilibrium='Transient redistribution of water mass and droplet size',
                    status='ANALYTIC_SAME_SIZE_KERNEL_COMPARISON' if a==b and a=='fog' else 'ASSESSED_NOT_SIMULATED',
                    result_file='results/agglomeration_coalescence.csv' if a==b and a=='fog' else '',
                limitations='Fog/mist are suspended liquid water. Names alone do not set size or collision efficiency. Charge variants are separate rows; mist-size coalescence kernel not separately run.')
        rows.append(z)
    charge=readcsv('charge_summary.csv')
    for r in charge:
        regime=r['regime'];label=r['charge_case'];isdrop=regime=='droplet'
        q=1000 if isdrop else 100;a=10 if isdrop else 1
        rows.append(dict(case_id='E_'+regime+'_'+label,substance_A='water_droplet' if isdrop else 'aerosol_surrogate',
            substance_B='water_droplet' if isdrop else 'aerosol_surrogate',scenario='charge_'+label,
            T_K=298.15,P_Pa=101325,RH_water_percent=100 if isdrop else 50,timescale_s=10 if isdrop else 1,
            concentrations=f'Independent pair ensemble,1280 pairs; radius{a}um. Charge0/0' if label=='neutral' else f'Independent pair ensemble,1280 pairs; radius{a}um. Charges+{q}e/{"+" if label=="like" else "-"}{q}e',
            geometry='3D unbounded air, comoving frame; initial separation200um' if isdrop else '3D unbounded air; initial separation20um',
            dominant_mechanism='Coulomb drift + Stokes/Cunningham drag + Brownian motion',chemical_transformation='none',explicit_reaction='none',
            partition_or_transport_metric='ensemble mean final center separation',metric_value=float(r['mean_m'])*1e6,metric_unit='um',
            rate_or_timescale='Deterministic r(t)^3=r0^3+6 b ke q1 q2 t; stochastic ensemble is separate',
            force_attraction_or_repulsion={'like':'Net Coulomb repulsion','opposite':'Net Coulomb attraction','neutral':'Zero imposed Coulomb force; Brownian separation is not repulsion'}[label],
            transient_or_equilibrium='Transient; no confining equilibrium',status='SIMULATED_3D_PARTICLE_PAIRS',
            result_file='results/charge_summary.csv;results/charge_refinement.csv',source_ids='NIST2006;Coulomb/Stokes analytic derivation',
            limitations='Stop at6 radii center separation; no contact/coalescence prediction, polarization, lubrication or collective many-body cloud. Fixed charge and radius.'))
    rows.append(dict(case_id='E_charged_neutral',substance_A='charged_droplet',substance_B='neutral_droplet',scenario='monopole_control',
        T_K=298.15,P_Pa=101325,RH_water_percent=100,timescale_s=1,concentrations='q1=1000e,q2=0',geometry='far-separated pair',
        dominant_mechanism='No direct q1q2 Coulomb term',chemical_transformation='none',explicit_reaction='none',
        partition_or_transport_metric='deterministic separation change',metric_value=0,metric_unit='m',rate_or_timescale='zero monopole drift',
        force_attraction_or_repulsion='Real induced-polarization attraction is possible; not modeled. Zero direct Coulomb force is not proof of zero total force.',
        transient_or_equilibrium='no direct electrostatic drift in control',status='UNIT_TESTED_CONTROL',result_file='test_models.py',source_ids='Coulomb monopole approximation',limitations='Neglects induced dipoles and image charges'))
    rows.append(dict(case_id='K_CO_OH',substance_A='CO',substance_B='OH_radical',scenario='low_pressure_elementary_kinetics',
        T_K=298.15,P_Pa=100,RH_water_percent=0,timescale_s=600,concentrations='CO1ppm; OH1e6 molecules/cm3 initially, finite reservoir; N2 bath',geometry='closed1m3 homogeneous gas',
        dominant_mechanism='chemical oxidation by explicit OH',chemical_transformation='Yes',explicit_reaction='CO+OH -> CO2+H (low-pressure channel)',
        partition_or_transport_metric='CO converted after600s',metric_value=json.loads((RES/'summary.json').read_text())['CO_OH_converted_percent'],metric_unit='percent',
        rate_or_timescale='k0=1.44e-13 cm3 molecule^-1 s^-1; finite OH is consumed',
        force_attraction_or_repulsion='Reaction encounters; no net macroscopic repulsion',transient_or_equilibrium='Transient finite oxidant consumption',
        status='SIMULATED_REDUCED_KINETICS',result_file='results/kinetics_results.csv',source_ids='IUPAC_CO_OH',
        limitations='100Pa benchmark is not ambient air. Omits <0.06% combined-pressure correction/HOCO stabilization, radical termination and wall losses. No extrapolation to complete atmospheric chemistry.'))
    rows.append(dict(case_id='K_H2O2_catalyst',substance_A='H2O2_aqueous',substance_B='MnO2_pyrolusite',scenario='published_catalytic_comparison',
        T_K='not recovered from accessible abstract',P_Pa='not recovered from accessible abstract',RH_water_percent='not applicable',timescale_s=600,
        concentrations='pH7; reported initial H2O2/surface-site ratio11.8; full loading not recovered',geometry='published aqueous catalyst suspension',
        dominant_mechanism='catalytic decomposition',chemical_transformation='Yes, conditional on catalyst',explicit_reaction='2H2O2 -> 2H2O + O2 (net)',
        partition_or_transport_metric='published maximum observed first-order rate (not transferred to pilot)',metric_value=.741,metric_unit='min^-1',
        rate_or_timescale='Rate depends on catalyst loading/sites, pH and temperature; missing inputs prevent transferable calculation',
        force_attraction_or_repulsion='Surface encounters; no generic repulsion claim',transient_or_equilibrium='Irreversible decomposition on experimental timescale',
        status='LITERATURE_ONLY_NOT_SIMULATED',result_file='',source_ids='Do2009',
        limitations='No numerical reaction-time prediction. Do not apply this rate to clean water or generic smoke. Stoichiometry separately unit-tested.'))
    for r in rows:
        r['sources']='; '.join(REF[x]['url'] for x in r.get('source_ids','').split(';') if x in REF and 'url' in REF[x])
    writecsv(ROOT/'interaction_matrix.csv',rows)
    return rows


def figure(name,caption):
    data=base64.b64encode((RES/(name+'.png')).read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{data}" alt="{esc(caption)}"><figcaption>{esc(caption)}</figcaption></figure>'
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in r)+'</tr>' for r in rows)+'</tbody></table></div>'


def build():
    m=matrix();s=json.loads((RES/'summary.json').read_text());p=readcsv('partition_results.csv');carb=readcsv('carbonate_results.csv')
    def part(name,med):return next(x for x in p if x['species']==name and x['medium']==med)
    sections=[]
    sections.append('<p><strong>New completed supplement:</strong> <a href="../mechanisms-switching-memory/report.html">Mechanisms, switching and memory</a> — spring hysteresis and an explicitly hypothetical chemical-feedback model; 18 verification tests and 168 seeded runs. <a href="../mechanisms-switching-memory/README.md">Reproducible package</a>.</p>')
    sections.append('''<h1>When substances meet</h1><p class="subtitle">NousVolition / My-Sources-Project-ALL · Reproducible multiphase interaction pilot · 10 October 2026 UTC</p>
    <p class="lead">Mixing, dissolution, surface attachment, reaction and electrostatic motion are different processes. This study runs separate models to identify which process is present, with explicit controls and limits.</p>
    <p><strong>Completed:</strong> 21 gas/liquid partition runs, two carbonate equilibrium solves, a CO–OH chemical kinetic benchmark with oxidant/rate sensitivities, 2D transport and refinement, 7,680 independent Brownian charged/neutral pair trajectories, 28 vapor/interface cases, nine acetone–ice adsorption runs, and analytic scavenging, coagulation and freezing/melting comparisons. All 27 verification tests passed; the delivered test log records the completed run.</p>
    <p><strong>Evidence level:</strong> published constants plus numerical verification against analytic limits. There is no new laboratory dataset, field calibration, or validation of a complete smoke/fog environment. Calculations here are not exposure predictions. No physical generation of CO, smoke or VOC vapors was performed or proposed.</p>''')
    sections.append('<h2>What was found</h2>'+table(['Solute','In 1 L bulk water: equilibrium (%)','In 0.5 g fog water: equilibrium (%)','Fog uptake at 600 s (%)'],[
        [x,fmt(part(x,'bulk')['equilibrium_aqueous_percent']),fmt(part(x,'fog')['equilibrium_aqueous_percent']),fmt(part(x,'fog')['aqueous_percent_600s'])]
        for x in ['CO','CO2','acetone','isoprene','H2O2']]))
    sections.append('''<p>The table uses a closed 1 m³ gas compartment at 298.15 K and 101,325 Pa, initially solute-free pure water, and fixed liquid inventory. Initial wet gas mole fractions are CO, acetone and isoprene 1 ppm each, CO₂ 420 ppm and H₂O₂ 1 ppb, tested separately. Fog radius is 10 µm, mist radius 25 µm; both contain 0.5 g water/m³. These radii are scenario choices, not definitions of fog and mist. The table’s CO₂ row is <em>physical dissolution only</em>.</p>
    <p>At these conditions the selected Henry concentration ratios, c<sub>liquid</sub>/c<sub>gas</sub>, are approximately 0.024 for CO, 0.843 for CO₂, 669 for acetone, 0.322 for isoprene and 2.13 million for H₂O₂. A tiny fog water volume can limit total uptake despite favorable water affinity. The values use the explicitly stated H<sup>cp</sup> convention; inverse Henry constants would reverse their numerical ordering. <a href="https://doi.org/10.5194/acp-23-10901-2023">Sander (2023)</a>.</p>''')
    sections.append(figure('partitioning','Calculated inventories and uptake transients. Large percentages do not mean chemical conversion. Fog and bulk compartments are different geometries.'))
    sections.append(f'''<p>CO₂ also redistributes chemically among CO₂* (dissolved CO₂ plus H₂CO₃), bicarbonate and carbonate. With zero initial alkalinity, the closed bulk-water equilibrium gives pH <strong>{float(carb[0]['pH']):.4f}</strong> and aqueous carbon inventory <strong>{float(carb[0]['aqueous_percent']):.5f}%</strong>. The fog case gives pH {float(carb[1]['pH']):.4f}. These are unbuffered pure-water values, not predictions for rain, drinking water, seawater or real fog. Acid-base equilibrium is solved separately; its transient is not claimed to follow the physical-only uptake curve. <a href="https://water.usgs.gov/water-resources/memos/memo.php?id=2098">USGS carbonate constants</a>.</p>
    <p>CO in clean water, humid air and fog has no modeled conversion to CO₂. A separate, deliberately low-pressure chemical benchmark at 100 Pa in N₂ adds a finite OH inventory (10⁶ molecules/cm³) and the evaluated low-pressure channel CO + OH → CO₂ + H. After 600 s, <strong>{s['CO_OH_converted_percent']:.6f}%</strong> of the initial 1 ppm CO has reacted. The small conversion is limited by available OH. No-OH control conversion is exactly zero. This benchmark is not a full ambient-air reaction mechanism. <a href="https://iupac-aeris.ipsl.fr/datasheets/pdf/HOx_VOC10.pdf">IUPAC evaluated kinetics</a>.</p>''')
    sections.append('''<p>H₂O₂ mixed with water is dissolution/dilution in the clean control. Catalytic decomposition, 2 H₂O₂ → 2 H₂O + O₂, is a different case. The cited pyrolusite study reports a maximum observed rate of 0.741 min⁻¹ at pH 7 and a specified peroxide/site ratio, but sufficient temperature/loading information was not recovered to transfer that rate. No catalytic time curve is presented. The scripts do verify elemental conservation at a prescribed reaction extent; this is explicitly a stoichiometric test, not predicted conversion. <a href="https://doi.org/10.1016/j.chemosphere.2008.11.075">Do et al. (2009)</a>.</p>''')
    sections.append('<h2>Transport is distinct from chemical identity</h2>'+figure('mixing_fields','CO passive-scalar transport at 0, 1 and 2 s. Periodic domain, prescribed uniform flow and diffusion. No chemical source term.'))
    sections.append(f'''<p>The 2D equation is ∂c/∂t + ∇·(u c) = D∇²c − λc. In the inert test λ = 0, D = 2×10⁻⁵ m²/s and u = (0.01, 0.003) m/s. These are specified benchmark inputs, not measured CO diffusion or room ventilation data. A sinusoidal initial field provides an exact Fourier solution, making numerical error measurable. The grid study reduced relative L² error from <strong>{100*s['grid_errors'][0]:.3f}%</strong> at 24² cells to <strong>{100*s['grid_errors'][-1]:.3f}%</strong> at 192² cells. First-order upwind advection causes numerical diffusion; remaining spatial error is reported, not hidden.</p>
    <p>Gas-only CO controls at 0%, 50% and 100% relative humidity use identical prescribed D and flow and therefore give identical transport. This demonstrates absence of an inserted CO–vapor reaction; it does not establish that humidity never changes real transport coefficients. Uniform gas buoyancy, temperature evolution, turbulence and Navier–Stokes momentum are not solved. Gravity can move droplets relative to air without molecular repulsion. All particle-pair plots use a frame moving with their common settling velocity.</p>
    <p>A smoke surrogate is a 100 nm radius inert spherical aerosol population, not smoke chemistry. A diffusion-only Smoluchowski collection model with 10 µm droplets, 0.5 g/m³ water and unit sticking captures <strong>{s['smoke_diffusion_capture_percent_600s']:.4f}%</strong> of particle material in 600 s. This is a restricted mechanism estimate. Real activation, impaction, phoresis, hygroscopicity and surface composition can dominate. A captured-material reservoir accompanies the 2D sink. <a href="https://acp.copernicus.org/articles/21/6945/2021/">Measured collection-efficiency study</a>, <a href="https://acp.copernicus.org/articles/14/6967/2014/">field fog scavenging study</a>.</p>''')
    sections.append('<h2>Repulsion requires a specified force</h2>'+table(['10 µm radius droplets, starting 200 µm apart','Mean separation at 10 s (µm)','Between-realization SD (µm)','Standard error of ensemble mean (µm)'],[
        [label, f"{v['mean_m']*1e6:.3f}",f"{v['sd_m']*1e6:.3f}",f"{v['sem_m']*1e6:.3f}"] for label,v in s['charge_droplet'].items()]))
    sections.append('''<p>Like and opposite cases use charges +1000e/+1000e and +1000e/−1000e. The neutral case has zero charge on both droplets. Each mean includes 1,280 independent pairs across five recorded seeds. Opposite charge attracts, like charge repels, and the neutral ensemble has no imposed Coulomb drift. A small increase in mean neutral radial distance is compatible with Brownian spreading and the geometry of measuring distance; it is not evidence of repulsion.</p>''')
    sections.append(figure('charged_droplets','Illustrative simulated paths, projected from 3D into a common-settling frame. Axes have different scales to make Brownian excursions visible.'))
    sections.append(figure('charge_separation','Stochastic sample trajectories compared with the analytic deterministic separation law. Ensemble statistics use many more pairs than the plotted examples.'))
    sections.append('''<p>The overdamped equation is dxᵢ = bᵢFᵢdt + √(2Dᵢ) dWᵢ, with b = Cc/(6πµa), D = kBTb, and Coulomb force F = kₑq₁q₂r/r³. For equal mobilities and no noise, r³(t) = r₀³ + 6b kₑq₁q₂t. Deterministic timestep refinement matches this limit. A separate Brownian mean-square-displacement test checks ⟨|Δx|²⟩ = 6Dt. Slip coefficients follow the <a href="https://nvlpubs.nist.gov/nistpubs/jres/111/4/V111.N04.A01.pdf">NIST aerosol reference</a>.</p>
    <p>These are independent pairs, not a collective many-particle charged cloud. Simulations stop a pair when its center separation reaches six radii. That stop records entry into an unmodeled near-field region; it is not a collision, sticking event or coalescence. Fixed charges, rigid spherical geometry, constant radius and independent drag omit polarization, hydrodynamic interactions and lubrication. A charged particle can attract a neutral polarizable object even though q₁q₂ = 0; the monopole control cannot predict that attraction. The aerosol charge/size sensitivity results that reach this boundary are censored and should not be interpreted as final contact distances.</p>
    <p>Electron-cloud overlap produces short-range quantum repulsion between molecules at close contact. Attractive dispersion, electrostatics and bonding also contribute at molecular scales. None of that means ordinary neutral gases refuse to mix. Droplet-scale Coulomb separation is a different, explicitly modeled force. Buoyancy, drag, settling and limited solubility can create spatial separation without a repulsive pair force.</p>''')
    sections.append('<h2>Water phase changes and ice surfaces</h2>'+figure('ice_and_water','Independent phase and sorption tests. The ice sorption model uses 210 K; it is not extrapolated to the −10 °C vapor exchange case.'))
    sections.append(f'''<p>At −10 °C, saturation over ice is {saturation(263.15,True):.2f} Pa, below {saturation(263.15):.2f} Pa over supercooled liquid water. A parcel initially at 95% RH relative to liquid is supersaturated relative to ice. Thus the separate thermostatted tests deposit vapor on ice while evaporating supercooled liquid. Water remains H₂O throughout. The interface model uses 1 L gas, 0.01 m² area, 0.001 m/s transfer velocity and a 10 g condensed reservoir. Water inventory is conserved; latent heat is recorded as thermostat heat, not ignored or used to predict free temperature evolution. <a href="https://doi.org/10.1256/qj.04.94">Murphy and Koop (2005)</a>.</p>
    <p>A separate seeded melting/freezing energy balance at 273.15 K converts 8.982 g of a 10 g inventory in 600 s under ±5 W. It uses a rounded 334 kJ/kg heat of fusion. It does not predict spontaneous freezing, nucleation delays, crystal habit or riming probability.</p>
    <p>At 210 K, the two-site published acetone–ice adsorption model puts <strong>{s['ice_acetone_adsorbed_percent']:.3f}%</strong> of a closed 1 ppb acetone inventory onto an assumed 1 m² ice surface by 600 s. This depends strongly on surface area and site density. Site 1 uses the reported capacity upper bound, and gas supply is assumed perfectly mixed without a boundary-layer resistance. The source describes preparation/aging effects and fits only 190–220 K. This result is a conditional surface-kinetics calculation, not a prediction for ordinary frost at room pressure. <a href="https://doi.org/10.1021/jp0563742">Published two-site adsorption model</a>.</p>''')
    sections.append('''<h2>Equations, assumptions and verification</h2>
    <p><strong>Compartment partitioning:</strong> ṅl = kLa Vl(Hcp RT ng/Vg − nl/Vl), ṅg = −ṅl. The independent analytic equilibrium is fl = Hcp RT Vl/(Vg + Hcp RT Vl). The relaxation rate is kLa(1 + Hcp RT Vl/Vg). Bulk kLa = 0.01 s⁻¹ is assumed. For droplets kL = Dl/a, kg = Dg/a, KL = (1/kL + Hcp RT/kg)⁻¹ and kLa = 3KL/a, with Dl = 2×10⁻⁹ and Dg = 2×10⁻⁵ m²/s as engineering inputs. This is a two-film closure, not a resolved liquid diffusion field. No accommodation resistance or curvature correction is fitted.</p>
    <p><strong>Chemical kinetics:</strong> the CO–OH benchmark explicitly accounts for CO, OH, CO₂ and H. It uses finite oxidant, an evaluated rate and separate C/O/H balances. At 100 Pa the evaluated combined-rate pressure correction is below 0.06%; that small correction and stabilization branch are omitted as a stated low-pressure approximation. Radical chain closure, wall chemistry and external OH production are absent. No rate for CO + water is invented.</p>
    <p><strong>Numerics:</strong> adaptive Radau or Runge–Kutta integration for the small compartments, a scalar root solve for carbonate, conservative periodic flux differences with SSPRK3 for transport, and Euler–Maruyama for Brownian particle pairs. The transport timestep is checked against a positive forward-Euler bound. Gas/liquid inventory, carbonate carbon, kinetic C/O/H, water phase inventory and captured particle material are tracked. Total chemical-species moles are not assumed conserved across arbitrary reactions: the H₂O₂ decomposition audit conserves atoms while producing O₂.</p>
    <p><strong>Refinement and controls:</strong> 24², 48², 96² and 192² transport grids; fixed-grid time refinement; charge drift timestep refinement; stochastic timestep distributions; zero flow/diffusion, no uptake, no sticking, no oxidant and no-charge controls; fixed seeds; Brownian Einstein and Coulomb/Stokes checks; carbonate electroneutrality; pure-water and saturation-reference limits. Agreement with these benchmarks verifies implementation of the reduced equations. It does not validate all omitted physics.</p>''')
    sections.append(f'<p>The largest reported relative inventory residual across the completed budgets is <strong>{s["max_relative_inventory_error"]:.3g}</strong>. Some residuals are small by construction because complementary reservoirs are used; independent analytic solutions, charge balance and physical invariants provide additional checks. Unit test output is saved in <a href="test_log.txt">test_log.txt</a>.</p>')
    sections.append('''<p><strong>Sensitivity:</strong> water partitioning spans 278.15–308.15 K, water loading 0.1–1 g/m³ and droplet radii 5–25 µm. Gas-only RH controls span 0–100%; phase exchange spans RHwater 50–105% and −15 to 25 °C. Flow spans 0–0.03 m/s. Charge simulations vary 0–3000 elementary charges, 5–20 µm radius and temperature. Smaller-particle scavenging spans 50 nm–1 µm radius. Five repeated seeds distinguish Brownian variability from deterministic drift. Isoprene Henry values span the retrieved literature spread 1.3×10⁻⁴ to 3.4×10⁻⁴ mol/(m³ Pa).</p>
    <p>The 4,000-draw-per-solute uncertainty exercise uses selected distributions: lognormal Henry variability (geometric SD 1.3, except uniform literature range for isoprene), uniform water loading and radius, and lognormal gas/liquid diffusivity variability (geometric SD 2). Reported 5th–95th percentiles are assumption-driven ranges, not measured confidence intervals. Temperature sweeps use local van’t Hoff slopes; they are not an uncertainty model. CO–OH rate multipliers use the source’s ±0.05 log10 reliability range. No equivalent rate distribution is invented for unspecified smoke adsorption or catalysis.</p>
    <p><strong>Scope limits:</strong> no molecular-dynamics or electronic-structure calculation, no universal smoke chemistry, no VOC oxidation network, no live CFD pressure/velocity/buoyancy solve, no evolving droplet population coupled to evaporation, and no experimental exposure or smell test. Neutral molecules mix through thermal motion and collisions. Identity, intermolecular affinity, phase availability, charge, size, surface composition and environment control outcomes more directly than molecular mass alone. Navier–Stokes remains a continuum momentum equation; reactive transport and molecular chemistry supply additional equations and constitutive data. This study proposes no new Navier–Stokes law.</p>''')
    sections.append(f'''<h2>Complete interaction matrix ({len(m)} cases)</h2>
    <p>The 105 baseline rows cover every unordered pair, including self-pairs, among 14 named species or material systems. Air overlaps N₂/O₂, and fog/mist overlap liquid water; those intentional overlaps are not extra thermodynamic phases. Nine additional cases resolve charge and reaction conditions. <strong>ASSESSED_NOT_SIMULATED</strong> means a mechanism assessment, not numerical evidence. Missing surface rates are left unquantified rather than set to zero. Full conditions and provenance are in <a href="interaction_matrix.csv">interaction_matrix.csv</a>.</p>
    <label>Filter matrix <input id="filter" placeholder="e.g. CO, ice, smoke, SIMULATED"></label><p id="count"></p><div class="scroll matrix"><table id="matrix"><thead><tr><th>Pair / case</th><th>Mechanism and chemistry</th><th>Measured or calculated quantity</th><th>Force / time behavior</th><th>Status and limits</th></tr></thead><tbody>''')
    for r in m:
        sections.append('<tr><td>'+esc(r['substance_A']+' + '+r['substance_B'])+'<small>'+esc(r['case_id']+' · '+r['scenario'])+'</small></td><td>'+esc(r['dominant_mechanism'])+'<small>'+esc(r['chemical_transformation'])+'</small></td><td>'+esc(r.get('partition_or_transport_metric',''))+'<small>'+esc(str(r.get('metric_value',''))+' '+r.get('metric_unit',''))+'</small><small>'+esc(r['rate_or_timescale'])+'</small></td><td>'+esc(r['force_attraction_or_repulsion'])+'<small>'+esc(r['transient_or_equilibrium'])+'</small></td><td>'+esc(r['status'])+'<small>'+esc(r['limitations'])+'</small></td></tr>')
    sections.append('</tbody></table></div><h2>Reproduce and inspect</h2><p>Read <a href="README.txt">README.txt</a>. Install requirements, run the tests, run run_study.py, then build_report.py. The complete archive includes the Python sources, frozen inputs, CSV tables, PNG/SVG figures, numeric concentration arrays and hashes. Nothing needs a connected account or external service after dependencies are installed.</p>')
    sections.append('<h2>Data provenance</h2><p>Constants were transcribed from the following public references. Accessed 10 October 2026 UTC. Scenario choices are marked as assumptions; they are not disguised as measured inputs.</p><ul class="refs">')
    for key,r in REF.items():
        if 'url' in r:
            sections.append('<li><a href="'+r['url']+'">'+esc(key+': '+r.get('title',r['url']))+'</a> — '+esc(r.get('use',r.get('origin','')))+ '</li>')
    sections.append('</ul>')
    document='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>NousVolition chemical interaction study</title><style>
    body{font:16px/1.65 system-ui,Segoe UI,sans-serif;color:#202c3e;background:#f4f6fa;margin:0}main{max-width:1140px;margin:auto;padding:48px 36px;background:white}h1{font-size:46px;line-height:1.15;letter-spacing:-1px}h2{margin-top:46px;border-top:1px solid #ccd3df;padding-top:24px;font-size:26px}.subtitle{color:#58667b;font-size:14px}.lead{font-size:22px;max-width:950px}p{max-width:1020px}a{color:#244fab}figure{margin:30px 0}img{width:100%;height:auto}figcaption{font-size:13px;color:#576375}table{border-collapse:collapse;width:100%;font-size:14px}th{text-align:left;background:#edf1f8;padding:12px;vertical-align:top}td{border-bottom:1px solid #dbe0e8;padding:11px;vertical-align:top}.scroll{overflow:auto}.matrix{max-height:700px}.matrix table{min-width:1080px}.matrix th{position:sticky;top:0}small{display:block;font-size:12px;line-height:1.55;color:#596579;margin-top:8px}input{font:inherit;padding:8px 12px;margin-left:12px;width:300px;border:1px solid #8896af;border-radius:4px}.refs{font-size:13px}li{margin-bottom:10px}@media(max-width:650px){main{padding:24px 16px}h1{font-size:34px}input{width:180px}}@media print{body{background:white}main{max-width:none;padding:0}.matrix{max-height:none}.scroll{overflow:visible}input,label{display:none}figure,table{break-inside:avoid}}
    </style></head><body><main>'''+''.join(sections)+'''</main><script>
    const input=document.getElementById('filter'),rows=[...document.querySelectorAll('#matrix tbody tr')];
    function filter(){let n=0;for(const r of rows){let show=r.textContent.toLowerCase().includes(input.value.toLowerCase());r.hidden=!show;if(show)n++;}document.getElementById('count').textContent=n+' cases shown';}input.addEventListener('input',filter);filter();
    </script></body></html>'''
    (ROOT/'research_report.html').write_text(document,encoding='utf-8')
    print(f'Wrote {len(m)} matrix rows and self-contained report.')


if __name__=='__main__':build()
