from pathlib import Path
import json
import numpy as np
from scipy.signal import find_peaks
from shape_model import mechanics,geometry,evolve,MAT

P=Path(__file__).resolve().parent
checks=[]
def check(name,value,tolerance):
    checks.append(dict(name=name,value=float(value),tolerance=tolerance,passed=bool(abs(value)<tolerance)))

D=.004;R=D/2;m=MAT['rho_water_kg_m3']*np.pi*D**3/6
omega=np.sqrt(8*MAT['surface_tension_N_m']/(MAT['rho_water_kg_m3']*R**3));period=2*np.pi/omega
vol=[4*np.pi*np.prod(geometry(s,D))*geometry(s,D)[1]/3 for s in np.linspace(-1,1,101)]
check('spheroid preserves exact water volume',max(abs(np.array(vol)/(np.pi*D**3/6)-1)),1e-14)
check('sphere surface area',mechanics(0,D)[2]/MAT['surface_tension_N_m']/(4*np.pi*R**2)-1,1e-13)
check('sphere zero capillary force',mechanics(0,D)[3]/(MAT['surface_tension_N_m']*D**2),1e-13)
check('sphere kinetic mass',mechanics(0,D)[0]/(2*m*R*R/15)-1,1e-13)
eps=1e-5
curvature=(mechanics(eps,D)[3]-mechanics(-eps,D)[3])/(2*eps)
check('Rayleigh l=2 linear stiffness',curvature/mechanics(0,D)[0]/omega**2-1,1e-7)
for s in [-.6,-.2,.2]:
    numerical=(mechanics(s+eps,D)[2]-mechanics(s-eps,D)[2])/(2*eps)
    check('surface energy derivative at '+str(s),numerical/mechanics(s,D)[3]-1,1e-7)
free=evolve(D,initial=(1e-3,0),duration=8*period,dt=period/300,mu=0)
peak=find_peaks(free[:,1])[0]
check('numerical free oscillation frequency',np.mean(np.diff(free[peak,0]))/period-1,.002)
amplitude_energy=free[0,4]-mechanics(0,D)[2]
check('unforced energy conservation',np.max(abs(free[:,-1]))/amplitude_energy,1e-5)
damped=evolve(D,initial=(1e-3,0),duration=8*period,dt=period/300)
peak=find_peaks(damped[:,1])[0]
beta=-np.polyfit(damped[peak,0],np.log(damped[peak,1]),1)[0]
exact_beta=5*MAT['mu_water_Pa_s']/MAT['rho_water_kg_m3']/R**2
check('Lamb small amplitude damping',beta/exact_beta-1,.003)
check('viscous energy-work balance',np.max(abs(damped[:,-1]))/amplitude_energy,1e-5)
step_load=-.04*MAT['rho_air_kg_m3']*8**2*D**3
forced=evolve(D,load=lambda s,t:step_load*(t>=.02),initial=(0,0),duration=.12,dt=1e-4)
fine=evolve(D,load=lambda s,t:step_load*(t>=.02),initial=(0,0),duration=.12,dt=5e-5)
check('forced timestep refinement aspect',np.max(abs(forced[:,3]-fine[::2,3])),2e-5)
check('forced energy-work balance',np.max(abs(fine[:,-1]))/(MAT['surface_tension_N_m']*D**2),1e-7)
report=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks,
            analytic_frequency_Hz=omega/(2*np.pi),numerical_damping_per_s=beta,analytic_damping_per_s=exact_beta)
(P/'shape_verification.json').write_text(json.dumps(report,indent=2))
np.savez_compressed(P/'shape_verification_traces.npz',free=free,damped=damped,forced=forced,forced_fine=fine)
print(json.dumps(report,indent=2));assert report['status']=='passed'
