"""Quench a nine-state GLV unit from switching toward stable coexistence.

Selected deterministic experiment, motivated by Aravind & Meyer-Ortmanns (2023).
Noise, coupled-unit relaxation, and clinical extrapolations are outside this test.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from heteroclinic import competition_matrix


def relaxation_time(times,relative_errors,tolerance=.05,confirmation=100.):
    outside=np.flatnonzero(np.asarray(relative_errors)>tolerance)
    first=int(outside[-1]+1) if len(outside) else 0
    if first>=len(times) or times[-1]-times[first]<confirmation:return None
    return float(times[first])


def evolve(initial,matrices,duration=4000.,step=.05,sample=.5):
    x=np.asarray(initial).copy();B=np.asarray(matrices);saved=[x.copy()]
    stride=round(sample/step)
    def rhs(y):return y*(1-np.einsum('rij,rj->ri',B,y))
    for tick in range(round(duration/step)):
        a=rhs(x);b=rhs(x+step*a/2);c=rhs(x+step*b/2);d=rhs(x+step*c)
        x+=step*(a+2*b+2*c+d)/6
        if np.any(x<=0) or not np.all(np.isfinite(x)):raise ArithmeticError('Invalid quench trajectory')
        if (tick+1)%stride==0:saved.append(x.copy())
    return np.arange(len(saved))*sample,np.asarray(saved)


def results():
    root=Path(__file__).parent
    prior=json.loads((root/'heteroclinic_results.json').read_text())['nine_state']['conditions'][0]['runs'][0]['trajectory']
    phases=[50.,150.,300.]
    starts=[next(row[1:] for row in prior if row[0]==t) for t in phases]
    gammas=[1.47,1.55,1.8,2.5];initial=[];matrices=[];labels=[]
    for gamma in gammas:
        B=competition_matrix(gamma=gamma)
        for phase,x in zip(phases,starts):
            initial.append(x);matrices.append(B);labels.append((gamma,phase))
    times,data=evolve(initial,matrices);cases=[]
    for k,((gamma,phase),B) in enumerate(zip(labels,matrices)):
        equilibrium=1/sum(B[0]);eigen=np.linalg.eigvals(-np.asarray(B)*equilibrium)
        slow=max(eigen,key=lambda x:x.real)
        errors=np.max(abs(data[:,k]-equilibrium),axis=1)/equilibrium
        trace=(data[:,k,0]-equilibrium)/equilibrium
        signs=trace[np.abs(trace)>.05]
        crossings=int(np.sum(signs[1:]*signs[:-1]<0))
        row=dict(gamma_after=gamma,pre_quench_time=phase,initial=initial[k],equilibrium=equilibrium,
            slow_eigenvalue=[float(slow.real),float(slow.imag)],linear_envelope_time=-1/float(slow.real),
            relaxation_time=relaxation_time(times,errors),first_component_crossings_above_tolerance=crossings,
            final_relative_error=float(errors[-1]))
        if phase==50.:row.update(times=times[::4].tolist(),first_component_relative_deviation=trace[::4].tolist(),
                                max_relative_error=errors[::4].tolist())
        cases.append(row)
    chosen=list(range(0,len(initial),3));ft,fd=evolve([initial[i] for i in chosen],[matrices[i] for i in chosen],step=.025)
    refinements=[]
    for j,i in enumerate(chosen):
        equilibrium=cases[i]['equilibrium'];errors=np.max(abs(fd[:,j]-equilibrium),axis=1)/equilibrium
        refinements.append(dict(gamma_after=cases[i]['gamma_after'],fine_step=.025,
            max_state_error=float(np.max(abs(data[:,i]-fd[:,j]))),fine_relaxation_time=relaxation_time(ft,errors)))
    return dict(source='https://doi.org/10.1063/5.0166803',gamma_before=1.05,
        duration=4000.,step=.05,tolerance_relative=.05,minimum_confirmation_time=100.,noise=0.,
        main_trajectories=len(initial),cases=cases,refinements=refinements)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();data=results();path=Path(__file__).with_name('quench_results.json')
    if args.check:
        if data!=json.loads(path.read_text(encoding='utf-8')):raise SystemExit('FAIL: quench results differ')
        print('PASS: 12 quenches and four step refinements reproduced.')
    else:
        path.write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
        print('Saved 12 quenches and four step refinements.')
