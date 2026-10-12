"""Reanalyze saved water-study outputs; no new xTB/PIMD/CFD run is claimed.

Default: use the bundled, hashed source snapshot. To replace it explicitly:
python audit_water_figures.py --source PATH_TO_QUANTUM_WATER_OUTPUTS
"""
import argparse,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
SNAPSHOT=ROOT/'prior_water_data'
FILES=['vibration_comparison.csv','vibration-summary.json','molecular-data/summary.json',
       'molecular-summary.json','molecular-protocol.json','channel_results.csv',
       'fluid-summary.json','flow-protocol.json','channel-error-budget.json',
       'protocol.json','sources.json','provenance.json','followup-amendments.json']


def readj(name):return json.loads((SNAPSHOT/name).read_text(encoding='utf-8-sig'))


def records(name):
    with (SNAPSHOT/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def run(source=None):
    if source:
        original=Path(source).resolve();SNAPSHOT.mkdir(exist_ok=True)
        hashes={}
        for name in FILES:
            src=original/name;target=SNAPSHOT/name
            target.parent.mkdir(parents=True,exist_ok=True)
            raw=src.read_bytes();target.write_bytes(raw)
            hashes[name]=hashlib.sha256(raw).hexdigest()
        (SNAPSHOT/'source_manifest.json').write_text(json.dumps(dict(
            source_directory=str(original),meaning='Snapshot of existing completed outputs; source study was not modified or rerun',
            sha256=hashes),indent=2),encoding='utf-8')
    hashes=readj('source_manifest.json')['sha256']
    for name,expected in hashes.items():
        assert hashlib.sha256((SNAPSHOT/name).read_bytes()).hexdigest()==expected,name
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    freq=records('vibration_comparison.csv');fs=readj('vibration-summary.json')
    predicted=np.array([float(r['predicted_cm1']) for r in freq])
    observed=np.array([float(r['observed_IR_cm1']) for r in freq])
    residual=predicted-observed
    check('Frequency residuals reproduce the saved table',np.allclose(residual,[float(r['error_cm1']) for r in freq],rtol=1e-12,atol=1e-12))
    check('Frequency RMSE and mean absolute error reproduce the saved summary',
        np.isclose(np.sqrt(np.mean(residual**2)),fs['RMSE_cm1']) and np.isclose(np.mean(abs(residual)),fs['MAE_cm1']))
    freq_summary=dict(RMSE_cm1=float(np.sqrt(np.mean(residual**2))),
        minimum_absolute_mismatch_cm1=float(min(abs(residual))),maximum_absolute_mismatch_cm1=float(max(abs(residual))),
        reported_max_numerical_spread_cm1=fs['primary_gate']['max_numerical_spread_cm1'],
        max_mismatch_over_reported_spread=float(max(abs(residual))/fs['primary_gate']['max_numerical_spread_cm1']),
        harmonic_reference_max_error_percent=fs['H2O_harmonic_reference_max_error_percent'],
        caveat='Harmonic predictions compared with fundamental bands; mismatch includes anharmonic/reference and electronic-model effects. Numerical spread is a sensitivity diagnostic, not a certified error bound.')

    molecular=readj('molecular-data/summary.json');ms=readj('molecular-summary.json')
    main=[r for r in molecular['runs'] if r['n']==64 and r['beads'] in [1,32] and r['T_K']==300 and r['dt_ps']==.0005 and r['mobility_NVE_ps']==5]
    group_rows=[];allmeans=True;allintervals=True
    metrics=['bond_mean_A','intramolecular_RDF_peak_A','hydrogen_bond_degree','tetrahedral_order']
    for iso in ['H2O','D2O']:
        for beads in [1,32]:
            subset=[r for r in main if r['isotope']==iso and r['beads']==beads]
            out=dict(isotope=iso,beads=beads,independent_seeds=[r['seed'] for r in subset])
            for key in metrics:
                vals=np.array([r[key] for r in subset]);n=len(vals)
                mean=float(vals.mean());half=float(student_t.ppf(.975,n-1)*np.std(vals,ddof=1)/np.sqrt(n))
                interval=[mean-half,mean+half]
                saved=molecular['groups'][f'{iso}-P{beads}'][key]
                allmeans &= np.isclose(mean,saved['mean'],rtol=1e-12,atol=1e-12)
                allintervals &= np.allclose(interval,saved['CI95'],rtol=1e-12,atol=1e-12)
                out[key]=dict(mean=mean,CI95=interval)
            group_rows.append(out)
    check('All selected liquid group means reproduce from independent run summaries',bool(allmeans))
    check('95 percent Student-t intervals reproduce using three runs per condition',bool(allintervals))
    counts=dict(main_runs=len(main),diffusion_window_passes=sum(r['diffusion_window_pass'] for r in main),
        energy_drift_passes=sum(r['NVE_energy_drift_pass'] for r in main),
        structural_control_passes=sum(r['structural_screen_pass'] for r in molecular['controls']),
        structural_controls=len(molecular['controls']))
    check('Liquid sampling/energy/control counts match the recorded audit',
        counts['main_runs']==ms['completed_main_runs'] and counts['diffusion_window_passes']==ms['main_window_passes']
        and counts['energy_drift_passes']==ms['main_energy_passes'] and counts['structural_control_passes']==ms['structural_controls_passes'])

    channel=records('channel_results.csv');steady_res=[];tau_res=[]
    for row in channel:
        mu,rho,h,G=[float(row[k]) for k in ['mu','rho','H_m','G_Pam']]
        steady=G*h*h/(12*mu);tau=rho*h*h/(mu*np.pi**2)
        steady_res.append(abs(float(row['steady_mean_ms'])/steady-1))
        tau_res.append(abs(float(row['tau_s'])/tau-1))
    check('Steady channel means match pressure-driven Poiseuille identity',max(steady_res)<1e-12)
    check('Channel relaxation times match the lowest Laplacian mode',max(tau_res)<1e-12)
    chosen=[r for r in channel if abs(float(r['T_K'])-298.15)<1e-8 and abs(float(r['G_Pam'])-10)<1e-8]
    bymaterial={r['material']:r for r in chosen}
    H=bymaterial['H2O'];D=bymaterial['D2O'];flow=readj('fluid-summary.json')
    ratio=float(H['mu'])/float(D['mu'])
    check('Recorded D2O/H2O steady-flow ratio equals the inverse viscosity ratio',abs(ratio-flow['steady_channel_D_over_H'])<1e-12)
    property_rows=[dict(material=r['material'],rho_kg_m3=float(r['rho']),mu_Pa_s=float(r['mu']),
        steady_mean_mm_s=1000*float(r['steady_mean_ms']),
        relative_to_H2O=float(r['steady_mean_ms'])/float(H['steady_mean_ms']),
        tau_s=float(r['tau_s']),lambda1_per_s=-1/float(r['tau_s'])) for r in chosen]

    out=dict(status='Completed reanalysis of saved outputs; no new molecular or CFD trajectories',
        source_manifest='prior_water_data/source_manifest.json',consistency_checks=checks,
        vibration=freq_summary,molecular_groups=group_rows,molecular_screens=counts,
        liquid_limitations=dict(bulk_diffusion_validated=ms['bulk_diffusion_validated'],viscosity_computed=ms['viscosity_computed']),
        channel=dict(T_K=298.15,pressure_gradient_Pa_m=10,full_gap_m=float(H['H_m']),
            max_steady_identity_relative_residual=max(steady_res),max_tau_identity_relative_residual=max(tau_res),
            D_over_H_steady_velocity=ratio,D_velocity_reduction_percent=100*(1-ratio),properties=property_rows),
        interpretation='Linearization predicts small molecular normal modes and selected channel perturbation decay when the corresponding physical operator is specified. Accurate integration alone does not validate potentials, sampling or micro-to-macro property transfer.')
    (ROOT/'water_figures_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')

    fig,ax=plt.subplots(1,3,figsize=(14,4.7),layout='constrained')
    names=[r['isotope']+' '+r['mode'].replace('symmetric stretch','sym. stretch').replace('antisym.','asym.') for r in freq]
    ax[0].barh(names,residual,color=['#226e97']*3+['#c66a30']*3)
    ax[0].axvline(0,color='black',lw=.7)
    ax[0].set(title='Model/reference mismatch remains',xlabel=f"Prediction − measurement (cm⁻¹)\nTested numerical spread ≤ {freq_summary['reported_max_numerical_spread_cm1']:.3f} cm⁻¹")
    ax[0].xaxis.label.set_fontsize(9)
    for iso,col,offset in [('H2O','#226e97',-.03),('D2O','#c66a30',.03)]:
        rows=[r for r in group_rows if r['isotope']==iso]
        ys=[r['bond_mean_A']['mean'] for r in rows]
        errs=[r['bond_mean_A']['CI95'][1]-r['bond_mean_A']['mean'] for r in rows]
        ax[1].errorbar(np.array([0,1])+offset,ys,yerr=errs,fmt='o-',capsize=3,color=col,label=iso)
    ax[1].set(xticks=[0,1],xticklabels=['Classical','32-bead'],ylabel='Mean covalent bond (Å)',title='A molecular structural change')
    ax[1].legend(fontsize=8)
    ordered=[next(r for r in property_rows if r['material']==name) for name in ['H2O','density_only','viscosity_only','D2O']]
    ax[2].bar(range(4),[r['relative_to_H2O'] for r in ordered],color=['#226e97','#65a8c4','#ddb48f','#c66a30'])
    ax[2].set(xticks=range(4),xticklabels=['H₂O','D density','D viscosity','D₂O'],ylabel='Steady flow / H₂O steady flow',title='Bulk flow uses supplied properties',ylim=(0,1.15))
    ax[2].tick_params(axis='x',labelsize=8)
    fig.suptitle('Three different checks; the molecular runs did not supply viscosity',fontsize=14)
    fig.savefig(ROOT/'water_evidence_audit.png',dpi=180,bbox_inches='tight')
    fig.savefig(ROOT/'water_evidence_audit.svg',bbox_inches='tight');plt.close(fig)
    print(json.dumps(out,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path);args=ap.parse_args()
    run(args.source)
