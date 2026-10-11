"""Plot clearly synthetic calibration verification, not measured Hug results."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def build_figures():
    report=json.loads((ROOT/'calibration/synthetic_results.json').read_text())
    truth=json.loads((ROOT/'calibration/synthetic_truth.json').read_text())
    assert report['data_origin']=='synthetic' and not report['physical_calibration_established']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,3,figsize=(13,7.3),constrained_layout=True)
    fig.suptitle('Hug calibration software check — SYNTHETIC measurements only',fontsize=17)
    for ax,kind,label in zip(axes.flat,['creep','passive','feedback','autonomous','circular','eccentric'],['Clay load and recovery','Passive release','Actuator force law','Active Hug, no orbit','Circular applied waveform','Eccentric applied waveform']):
        row=next(r for r in report['validation'] if r['kind']==kind)
        ax.plot(row['time_s'],row['observed'],color='#236783',lw=2,label='Synthetic held-out recording')
        ax.plot(row['time_s'],row['predicted'],color='#dd7e37',ls='--',lw=1.4,label='Fitted-model prediction')
        ax.set_title(label+'\nRMSE '+format(row['rmse'],'.2g')+' '+row['units']);ax.set_xlabel('Time (s)');ax.set_ylabel('Actuator force (N)' if kind=='feedback' else 'Displacement (mm)')
        ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=8,loc='upper right');fig.savefig(ROOT/'figures/hug_calibration_validation.png',dpi=165);plt.close(fig)
    labels=[];ratios=[]
    for group,fit in [('material','creep'),('mechanics','passive'),('feedback','feedback')]:
        for key,value in truth[group].items():
            if value==0:continue
            labels.append(key);ratios.append(report['fits'][fit]['parameters'][key]/value)
    fig,ax=plt.subplots(figsize=(11,4.5),constrained_layout=True);ax.bar(np.arange(len(labels)),ratios,color='#236783');ax.axhline(1,color='#dd7e37',ls='--',label='Known synthetic value')
    ax.set_xticks(np.arange(len(labels)),['G M','η M','G K','η K','Mass','Stiffness','Gain a','Saturation b']);ax.set_ylim(0,1.2);ax.set_ylabel('Fitted value / known value');ax.set_title('Synthetic coefficient recovery\nStarting guesses differ from the known coefficients');ax.legend();fig.savefig(ROOT/'figures/hug_calibration_parameters.png',dpi=165);plt.close(fig)


def html_section():
    return '''<section id="hug-calibration"><h2>Batch 13 · calibrate the Hug with measurements</h2>
<p><a href="calibration/measurements.html">Open the local measurement notebook</a> to enter force and motion recordings, import sensor rows, and export a private measurement file. Download the study folder to use the page locally; it sends nothing to a server. The blank form contains no observations.</p>
<p>The calibration tool fits clay, passive mechanics and powered feedback using fit-labelled trials. It tests new recordings without changing those fitted parameters: clay recovery, passive release, actuator force, autonomous motion, circular forcing and eccentric forcing. Starting clay memory, sensor units, controller delay and separate force channels are explicit.</p>
<figure><img src="figures/hug_calibration_parameters.png" alt="Synthetic calibration recovers eight known material, mechanical and actuator coefficients"><figcaption>Simulated measurements verify coefficient recovery. These are not physical measurements of your Hug.</figcaption></figure>
<figure><img src="figures/hug_calibration_validation.png" alt="Six types of held-out synthetic recording overlaid with fitted-model predictions"><figcaption>Fourteen synthetic recordings check the pipeline. All reserved prediction gates pass; no physical calibration or physical rhythm is established. Different starts and orbital waveforms are represented.</figcaption></figure>
<p><a href="HUG_CALIBRATION_METHODS.md">Measurement procedure and assumptions</a> · <a href="calibration/blank_session.json">Empty session template</a> · <a href="calibration/measurement_template.csv">Empty sensor table</a> · <a href="calibration/synthetic_results.json">Synthetic calibration results</a></p>
<p>Export before closing the entry page. Keep actual measurements outside the published study folder; the analysis tool writes results only to your chosen folder and never uploads them. Passed finite-record predictions support the tested mode and loads; additional disturbance, energy, contact and uncertainty checks are needed for a physical rhythm claim.</p></section>'''


if __name__=='__main__':
    build_figures();print('Built two synthetic calibration figures')
