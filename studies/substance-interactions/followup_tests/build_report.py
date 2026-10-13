"""Build readable outputs from completed numeric results, without rerunning them."""
from pathlib import Path
import csv,html,json,hashlib,re
ROOT=Path(__file__).resolve().parent
def read_csv(name):
    with (ROOT/'results'/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def build():
    s=json.loads((ROOT/'results/summary.json').read_text(encoding='utf-8'))
    f,p,m=s['fog'],s['particles'],s['measurements']
    by={r['case']:r for r in p['summary']};neutral=by['neutral'];polar=by['charged_neutral_100e']
    text=f'''# Substance follow-up: evaporation, polarization and measured capture

Three previously open assumptions have now been tested. **{s['unit_tests_passed']} new unit tests passed.** The batch completed 108 main fog scenarios, 28 further fog/control/refinement solves, 21,504 main Brownian paths, 18,432 paired refinement paths, 34 deterministic particle solves and a comparison with 18 published measurements. The refinement paths reuse random increments across steps; they are not independent replications of every comparison.

[Illustrated report](report.html) · [Methods and remaining gaps](METHODS.md) · [Family and community analogy](COMMUNITY.md) · [Numerical summary](results/summary.json) · [Updated interaction cases](interaction_updates.csv)

## Results that change how the original pilot should be read

**Evaporation changes gas retention.** At 25 °C, 90% initial RH, 0.5 g water in 1 m³ air and 10 µm initial radius, droplets reached the 2 µm model cutoff after {f['RH90_cutoff_s']:.3f} s. H₂O₂ uptake peaked at {f['RH90_H2O2_peak_aqueous_percent']:.2f}% of its initial inventory and fell to {f['RH90_H2O2_final_aqueous_percent']:.2f}% at cutoff. Holding water volume fixed instead gave {f['RH90_H2O2_fixed_water_same_time_percent']:.2f}% at the same time. This is modeled absorption and release, with no chemical conversion. The remaining water is retained at cutoff; full drying is not modeled.

At 50% RH, allowing conductive cooling increased the time from 10 to 2 µm radius from {f['RH50_isothermal_cutoff_s']:.3f} to {f['RH50_cooled_cutoff_s']:.3f} s. The liquid and gas share a closed water inventory; the gas temperature is externally maintained. The calculation uses a quasi-steady thermal balance and an assumed two-film solute transfer model.

![Evaporation and solute uptake](results/evaporating_fog.png)

**A neutral conducting droplet can attract a charged aerosol through polarization.** In the specified quiescent 25 °C scenario with a 100 nm aerosol and a 10 µm droplet, {100*polar['mean_stop_fraction']:.2f}% of paths with a 100e aerosol charge reached the 20 µm separation boundary within 1 s, compared with {100*neutral['mean_stop_fraction']:.2f}% for neutral Brownian controls. Disabling polarization while keeping the droplet neutral exactly recovered the neutral result. These are outer encounters, not collisions or coalescence. Both objects being neutral still provides no electrostatic repulsion in this model.

The same-sign 100e/1e case was attracted at the initial separation because polarization exceeded its weak Coulomb repulsion; the 100e/100e case was repelled. Thus the sign of the net interaction depends on geometry and both terms, not just the sign of charge or a separating trajectory. The point-aerosol/conducting-sphere approximation is not a general two-droplet solution.

![Polarization and controls](results/polarization_controls.png)

**The old diffusion-only capture kernel fails this published-data challenge.** The 18 sodium-fluorescein aerosol measurements exceed its predicted collection efficiency by factors {m['min_measured_over_prediction']:.1f}–{m['max_measured_over_prediction']:.1f} (median {m['median_measured_over_prediction']:.1f}). All 18 remain above the tested sensitivity envelope. This directly rules out using that incomplete stagnant-kernel calculation as a quantitative description of this falling-droplet experiment. It does not invalidate diffusion itself, and the data are not universal smoke measurements.

The comparison uses [Dépée et al. (2021), Part I, Table 3](https://doi.org/10.5194/acp-21-6945-2021), including measured wet sizes and reported group conditions. No correction factor was fitted. Ventilation, phoretic effects, interception and inertia require a fuller model before a matched validation claim is justified.

![Measured capture comparison](results/measured_capture_challenge.png)

## What still needs testing

- A fuller falling-droplet capture model against independent measurements, followed by composition-specific smoke tests using existing data.
- Resolved diffusion inside droplets and independent measurements of coupled evaporation and solute uptake.
- CO₂ hydration and carbonate reaction transients with stated alkalinity and validated rates.
- H₂O₂ decomposition with a specified catalyst, loading, pH and temperature.
- VOC adsorption on defined smoke/soot/organic and ice surfaces, including aging.
- Real charge distributions, charge relaxation, hydrodynamic coupling, near-contact collisions, coalescence and collective cloud behavior.

The [community guide](COMMUNITY.md) explains how Water, Fog, Mist, Gas, Smoke, Clay and Ice can represent family roles with their own contact, boundary and memory rules. That proposed family extension has not been run as part of these physical tests; the existing SIMS community studies are linked there.

## Numerical checks and reproducibility

The maximum main-sweep water-inventory residual was {f['max_water_error']:.3g} of initial liquid water; maximum solute inventory residual was {f['max_solute_error']:.3g}. Step/tolerance and Radau/BDF comparisons changed the final liquid inventory fractions by at most {f['max_refinement_liquid_fraction_difference']:.3g} in the selected checks. Deterministic electrostatic potential plus drag dissipation had relative residual below {p['max_energy_error']:.3g}. Halving the Brownian step from 0.001 to 0.0005 s changed mean boundary-stop fractions by up to {p['dt001_max_mean_stop_change_percentage_points']:.3f} percentage points in the selected paired ensembles.

Particle intervals in the tables are descriptive 95% Student-t intervals across six seed estimates. They are unbounded at rare-event extremes and can have zero width when all seed estimates coincide; they do not establish exact zero or unit population probabilities. Measurement sensitivity envelopes are assumed parameter ranges, not confidence intervals. Numerical verification and the capture-model failure are separate findings.

From this folder with Python 3.12 and the listed dependencies:

```text
python -m pip install -r requirements.txt
python -m unittest -v test_followup.py
python run_followup.py
python build_report.py
python verify_package.py --write-manifest
python verify_package.py
```

Before regeneration, `python verify_package.py` checks the delivered hashes. After an intentional rerun, `--write-manifest` records the new output hashes. The runner writes its own test log. To capture console output, run `python run_followup.py > run_log.txt 2>&1`. It overwrites this folder's generated numerical files. The completed run took {s['seconds']:.1f} s on the recorded environment. No network is used after dependency installation. [Source references](references.json), [data transcription](measured_collection.json), [input hashes](results/input_hashes.json), [test log](test_log.txt), [all file hashes](manifest.json), [saved trajectories](results/trajectories.npz) and CSV results are included. Original substance-study results are retained separately.

[Earlier substance study](../README.md) · [Streams and Rocks](../../../README.md)
'''
    (ROOT/'README.md').write_text(text,encoding='utf-8')
    # Simple offline report, keeping numeric descriptions generated from the JSON.
    body=[];lines=text.splitlines();in_code=False;in_list=False
    def inline(t):
        t=html.escape(t)
        t=re.sub(r'!\[([^]]*)\]\(([^)]+)\)',r'<figure><img alt="\1" src="\2"></figure>',t)
        t=re.sub(r'\[([^]]*)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
        t=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t)
        t=re.sub(r'`([^`]+)`',r'<code>\1</code>',t)
        return t
    for line in lines:
        if line.startswith('```'):
            body.append('</code></pre>' if in_code else '<pre><code>');in_code=not in_code;continue
        if in_code:body.append(html.escape(line)+'\n');continue
        if line.startswith('- '):
            if not in_list:body.append('<ul>');in_list=True
            body.append('<li>'+inline(line[2:])+'</li>');continue
        if in_list:body.append('</ul>');in_list=False
        if line.startswith('# '):body.append('<h1>'+inline(line[2:])+'</h1>')
        elif line.startswith('## '):body.append('<h2>'+inline(line[3:])+'</h2>')
        elif line:body.append('<p>'+inline(line)+'</p>')
    html_doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Substance follow-up results</title><style>body{font:18px/1.65 system-ui,sans-serif;margin:0;background:#f1f5f7;color:#182d38}main{max-width:1050px;margin:28px auto;background:white;padding:35px 48px;border-radius:12px}h1{line-height:1.15;color:#174762;font-size:38px}h2{margin-top:40px;font-size:25px}a{color:#086c93}img{width:100%;height:auto}figure{margin:24px -10px}pre{background:#edf3f6;padding:18px;overflow:auto}code{font-size:15px}li{margin:8px 0}@media(max-width:700px){main{padding:22px;margin:0}h1{font-size:29px}}</style><main>'''+''.join(body)+'</main></html>'
    (ROOT/'report.html').write_text(html_doc,encoding='utf-8')
    # Supplement, not a replacement for the original 114-row matrix.
    matrix=[]
    common='Tgas=298.15 K; initial P=101325 Pa; Vg=1 m3; LWC=0.5 g/m3; a0=10 um; initial RH=90%; cooling+Kelvin; stop at a=2 um'
    row=next(r for r in read_csv('fog_cases.csv') if r['T']=='298.15' and r['RH']=='0.9' and float(r['radius'])==1e-5 and r['cooling']=='True')
    for sp in ['CO','acetone','isoprene','H2O2']:
        matrix.append(dict(pair=sp+' / evolving fog',conditions=common,mechanism='Gas/liquid absorption and release coupled to water evaporation',chemical_conversion='No',force='No added interspecies force',
            numerical_measure=f"peak aqueous {100*float(row[sp+'_peak_liquid_fraction']):.9g}%; end {100*float(row[sp+'_final_liquid_fraction']):.9g}% of initial solute",timescale=f"{float(row['actual_end_s']):.9g} s to radius cutoff",behavior='Transient',status='Simulated compartment',limits='Assumed film diffusivities; no resolved internal diffusion or reaction',evidence='results/fog_cases.csv'))
    for name,q,Q in [('charged_neutral_100e',100,0),('charged_neutral_monopole',100,0),('weak_like_charge',100,1),('strong_like_charge',100,100),('opposite_charge',100,-100),('neutral',0,0)]:
        r=by[name]
        matrix.append(dict(pair=name,conditions=f'T=298.15 K; P=101325 Pa; aerosol a=100 nm, q={q}e; drop A=10 um, Q={Q}e; initial separation=30 um; quiescent air',mechanism='Brownian motion and Stokes/slip drag; conducting-sphere polarization and Coulomb terms as enabled',chemical_conversion='No',force={'charged_neutral_100e':'Attraction','charged_neutral_monopole':'No electrostatic force','weak_like_charge':'Net attraction at initial separation','strong_like_charge':'Repulsion at initial separation','opposite_charge':'Attraction','neutral':'No electrostatic force'}[name],numerical_measure=f"{100*r['mean_stop_fraction']:.9g}% reach outer 20 um boundary",timescale='1 s',behavior='Transient; stopped at boundary',status='Simulated 3D pair ensemble',limits='Point aerosol/conducting droplet; no gravity or hydrodynamic interaction; boundary is not collision',evidence='results/particle_summary.csv'))
    matrix.append(dict(pair='Sodium-fluorescein aerosol / falling water droplets',conditions='18 published points; RH 71.1/82.4/93.5%; group T=273.41/273.42/274.35 K; drop radii 49.3/50.8/48.8 um; nominal speed .25 m/s',mechanism='Challenge of original Brownian diffusion-only capture kernel',chemical_conversion='Not assessed',force='Kernel excludes phoresis, flow, inertia and electrostatics',numerical_measure=f"Measured/model ratios {m['min_measured_over_prediction']:.6g} to {m['max_measured_over_prediction']:.6g}",timescale='Measured collection efficiency under published chamber conditions',behavior='Empirical comparison',status='18 published central values reanalyzed; no fitting',limits='Not all smoke compositions; incomplete model fails this challenge',evidence='results/published_data_comparison.csv'))
    with (ROOT/'interaction_updates.csv').open('w',newline='',encoding='utf-8') as out:
        writer=csv.DictWriter(out,fieldnames=list(matrix[0]));writer.writeheader();writer.writerows(matrix)
    print('Wrote README.md, report.html and',len(matrix),'interaction updates')

if __name__=='__main__':build()
