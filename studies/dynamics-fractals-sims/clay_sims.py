"""Current SIMS Hug: Burgers clay response, with explicitly specified coupling."""
import argparse
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from sims_response import graph_cases, operators, initial_state, measurements
from bridge_checks import compare_saved

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('located_clay',ROOT/'clay_source/clay_model.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)


def protocol():return json.loads((ROOT/'clay_sims_protocol.json').read_text())


def initial(seed,n=20):
    z=np.zeros((n,2));q=initial_state(seed,n)[:,0]
    z[:,1]=protocol()['initial_retained_scale']*(q-q.mean())
    return z


class ClayNetwork:
    """Internal states: recoverable Kelvin strain u and retained dashpot strain w."""
    def __init__(self,material,laplacian,coupling=2.):
        self.m=material;self.l=np.asarray(laplacian,dtype=float)
        self.gm=material['G_M_Pa'];self.gk=material['G_K_Pa']
        self.em=material['eta_M_Pa_s'];self.ek=material['eta_K_Pa_s']
        if min(self.gm,self.gk,self.em,self.ek)<=0 or coupling<0:raise ValueError('Positive coefficients and nonnegative coupling required')
        if self.l.ndim!=2 or self.l.shape[0]!=self.l.shape[1] or not np.allclose(self.l,self.l.T):raise ValueError('Symmetric Laplacian required')
        self.k=coupling*self.gm
        lam,self.vectors=np.linalg.eigh(self.l)
        if min(lam)<-1e-12 or not np.allclose(self.l.sum(axis=1),0,atol=1e-12):raise ValueError('Positive semidefinite Laplacian with zero row sums required')
        lam[np.abs(lam)<1e-12]=0
        self.h=1/(1+coupling*lam)
        self.b=(self.vectors*self.h)@self.vectors.T
        resistance=self.gm*(1-self.h)
        matrices=np.zeros((len(lam),2,2))
        matrices[:,0,0]=-(resistance+self.gk)/self.ek
        matrices[:,1,1]=-resistance/self.em
        matrices[:,0,1]=matrices[:,1,0]=-resistance/np.sqrt(self.ek*self.em)
        self.rates,self.rotation=np.linalg.eigh(matrices)
        self.root_eta=np.sqrt([self.ek,self.em])

    def gamma(self,z,load):
        return (np.asarray(load)/self.gm+np.sum(z,axis=-1))@self.b.T

    def stress(self,z,load):return np.asarray(load)-self.k*(self.gamma(z,load)@self.l.T)

    def rhs(self,z,load):
        stress=self.stress(z,load)
        return np.stack(((stress-self.gk*z[...,0])/self.ek,stress/self.em),axis=-1)

    def evolve(self,z,load,times):
        """Affine modal solution, including the exact zero-rate Maxwell mode."""
        z=np.asarray(z);times=np.atleast_1d(times).astype(float)
        modal=np.einsum('ij,...jk->...ik',self.vectors.T,z)*self.root_eta
        y=np.einsum('mji,...mj->...mi',self.rotation,modal)
        drive=np.einsum('ij,...j->...i',self.vectors.T,np.broadcast_to(load,z.shape[:-1]))
        drive=drive[...,None]*self.h[:,None]/self.root_eta
        drive=np.einsum('mji,...mj->...mi',self.rotation,drive)
        a=times[:,None,None]*self.rates
        phi=np.divide(np.expm1(a),self.rates,out=np.broadcast_to(times[:,None,None],a.shape).copy(),where=self.rates!=0)
        shape=(len(times),)+(1,)*(z.ndim-2)+self.rates.shape
        evolved=np.exp(a).reshape(shape)*y+phi.reshape(shape)*drive
        rotated=np.einsum('mij,t...mj->t...mi',self.rotation,evolved)/self.root_eta
        return np.einsum('ij,t...jk->t...ik',self.vectors,rotated)

    def energy(self,z,load):
        gamma=self.gamma(z,load);elastic=gamma-z.sum(axis=-1)
        return (.5*self.gm*np.sum(elastic**2,axis=-1)+.5*self.gk*np.sum(z[...,0]**2,axis=-1)
                +.5*self.k*np.sum(gamma*(gamma@self.l.T),axis=-1))


def sample_grid():return source.sample_times()


def path(net,z):
    """One-second observations and both limits of the prescribed load jumps."""
    n=z.shape[-2];s=np.full(n,net.m['stress_Pa'])
    at_start=net.evolve(z,np.zeros(n),[source.START])[0]
    at_release=net.evolve(at_start,s,[source.HOLD])[0]
    states=[];loads=[]
    for t,side in sample_grid():
        if t<source.START or (t==source.START and side=='left'):
            state=net.evolve(z,np.zeros(n),[t])[0];load=np.zeros(n)
        elif t<source.RELEASE or (t==source.RELEASE and side=='left'):
            state=net.evolve(at_start,s,[t-source.START])[0];load=s
        else:
            state=net.evolve(at_release,np.zeros(n),[t-source.RELEASE])[0];load=np.zeros(n)
        states.append(state);loads.append(load)
    values=np.array(states);loads=np.array(loads)
    gamma=np.array([net.gamma(v,s) for v,s in zip(values,loads)])
    return values,gamma,loads


def adaptive(net,z,method='DOP853'):
    """Independent full-coordinate ODE, splitting exactly at applied-load jumps."""
    n=len(z);states=[];loads=[];grid=sample_grid();times=np.array([t for t,_ in grid]);sides=[s for _,s in grid]
    out=np.zeros((len(times),n,2));start=z.copy()
    for a,b,s in [(0,source.START,0),(source.START,source.RELEASE,net.m['stress_Pa']),(source.RELEASE,source.END,0)]:
        load=np.full(n,s)
        sol=solve_ivp(lambda t,y:net.rhs(y.reshape(n,2),load).ravel(),(a,b),start.ravel(),
                      method=method,rtol=1e-10,atol=1e-13,max_step=2.,dense_output=True)
        if not sol.success:raise RuntimeError(sol.message)
        mask=(times>=a)&(times<=b)
        out[mask]=sol.sol(times[mask]).T.reshape(-1,n,2)
        start=sol.y[:,-1].reshape(n,2)
    loads=np.array([np.full(n,net.m['stress_Pa'] if source.START<=t<=source.RELEASE and
                           not(t==source.START and side=='left') and not(t==source.RELEASE and side=='right') else 0) for t,side in grid])
    return out,np.array([net.gamma(v,s) for v,s in zip(out,loads)])


def energy_control(net,z,order=64):
    """Constant-load work from endpoints; independent Gaussian dissipation quadrature."""
    nodes,weights=np.polynomial.legendre.leggauss(order)
    previous=np.zeros(z.shape[-2]);e0=net.energy(z,previous);work=np.zeros_like(e0);loss=np.zeros_like(e0)
    for duration,magnitude in [(source.START,0),(source.HOLD,net.m['stress_Pa']),(source.END-source.RELEASE,0)]:
        load=np.full(z.shape[-2],magnitude)
        old_gamma=net.gamma(z,previous);new_gamma=net.gamma(z,load)
        work+=np.sum(.5*(previous+load)*(new_gamma-old_gamma),axis=-1)
        samples=net.evolve(z,load,(nodes+1)*duration/2)
        f=net.rhs(samples,load)
        rates=np.sum(net.ek*f[...,0]**2+net.em*f[...,1]**2,axis=-1)
        loss+=np.einsum('t,t...->...',weights*duration/2,rates)
        final=net.evolve(z,load,[duration])[0]
        work+=np.sum(load*(net.gamma(final,load)-new_gamma),axis=-1)
        z=final;previous=load
    return {'max_budget_error':float(np.max(np.abs(net.energy(z,previous)-e0-work+loss))),
            'min_dissipation':float(np.min(loss))}


def run():
    cfg=protocol();runs=[];traces=[];controls=[];aggregates=[];uncoupled=[]
    if cfg['schedule_seconds']!={'rest':source.START,'hold':source.HOLD,'recovery':source.END-source.RELEASE}:
        raise ValueError('Protocol schedule must match the pinned clay source.')
    if [m['stress_Pa'] for m in source.materials()]!=cfg['material_rows_stress_Pa']:
        raise ValueError('Protocol material rows must match the pinned clay source.')
    seeds=cfg['seeds'];initials=np.array([initial(seed) for seed in seeds]);times=np.array([t for t,_ in sample_grid()])
    baseline={}
    for m in source.materials():
        net=ClayNetwork(m,np.zeros((20,20)),0);_,g,_=path(net,initials)
        baseline[m['stress_Pa']]=np.std(g[-1],axis=-1)
        for i,seed in enumerate(seeds):uncoupled.append({'stress_Pa':m['stress_Pa'],'seed':seed,'final_spread':float(baseline[m['stress_Pa']][i]),'final_strain':g[-1,i].tolist()})
    for name,graph in graph_cases():
        _,l=operators(graph)
        for m in source.materials():
            net=ClayNetwork(m,l,cfg['coupling_ratio_K_over_G_M']);z,g,loads=path(net,initials)
            star=m['stress_Pa']*source.HOLD/m['eta_M_Pa_s']
            exact=np.array([source.state_at(m,t,side)['total'] for t,side in sample_grid()])
            mean_error=float(np.max(np.abs(g.mean(axis=-1)-exact[:,None])))
            for i,seed in enumerate(seeds):
                measured=measurements(times,g[:,i]/star)
                runs.append({'graph':name,'stress_Pa':m['stress_Pa'],'seed':seed,
                    'normalization_strain':star,'initial_retained_strain':initials[i,:,1].tolist(),
                    'final_strain':g[-1,i].tolist(),'final_kelvin_strain':z[-1,i,:,0].tolist(),
                    'final_retained_strain':z[-1,i,:,1].tolist(),**measured,
                    'final_absolute_spread':float(np.std(g[-1,i])),
                    'final_spread_ratio_to_uncoupled':float(np.std(g[-1,i])/baseline[m['stress_Pa']][i]),
                    'final_mean_strain':float(g[-1,i].mean()),'peak_sampled_abs_strain':float(np.max(np.abs(g[:,i])))})
            rows=runs[-len(seeds):]
            aggregates.append({'graph':name,'stress_Pa':m['stress_Pa'],'runs':len(rows),
                'mean_final_spread_ratio_to_uncoupled':float(np.mean([x['final_spread_ratio_to_uncoupled'] for x in rows])),
                'mean_final_absolute_spread':float(np.mean([x['final_absolute_spread'] for x in rows])),
                'final_response_sign_unanimous':sum(x['final_choice_unanimity'] for x in rows),
                'mean_final_strain':float(np.mean([x['final_mean_strain'] for x in rows]))})
            traces.append({'graph':name,'stress_Pa':m['stress_Pa'],'seed':seeds[0],
                'time':times.tolist(),'side':[side for _,side in sample_grid()],
                'mean_total':g[:,0].mean(axis=-1).tolist(),'absolute_spread':g[:,0].std(axis=-1).tolist(),
                'mean_kelvin':z[:,0,:,0].mean(axis=-1).tolist(),'mean_retained':z[:,0,:,1].mean(axis=-1).tolist(),
                'mean_elastic':(g[:,0]-z[:,0].sum(axis=-1)).mean(axis=-1).tolist()})
            checks=[]
            for method in ('DOP853','Radau'):
                az,ag=adaptive(net,initials[0],method)
                checks.append({'method':method,'max_strain_error':float(max(np.max(np.abs(az-z[:,0])),np.max(np.abs(ag-g[:,0]))))})
            energy=energy_control(net,initials)
            controls.append({'graph':name,'stress_Pa':m['stress_Pa'],'seed':seeds[0],
                'mean_source_error':mean_error,**energy,'independent_solvers':checks})
    gate=cfg['gates'];passed=all(c['mean_source_error']<gate['max_mean_source_error'] and
        c['max_budget_error']<gate['max_energy_budget_error_J_m3'] and c['min_dissipation']>=0 and
        all(s['max_strain_error']<gate['max_solver_strain_error'] for s in c['independent_solvers']) for c in controls)
    return {'model':'Current clay Burgers SIMS','main_runs':len(runs),'uncoupled_runs':len(uncoupled),
        'independent_solver_runs':24,'accuracy_gates_passed':passed,'runs':runs,'uncoupled':uncoupled,
        'aggregates':aggregates,'representative_traces':traces,'controls':controls}


def reproduction_check(a,b):
    # Solver error diagnostics reapply fixed gates; main observations compare tightly.
    import copy
    a,b=copy.deepcopy(a),copy.deepcopy(b)
    for d in (a,b):
        if not d['accuracy_gates_passed']:return False
        for c in d.pop('controls'):
            gate=protocol()['gates']
            if c['mean_source_error']>=gate['max_mean_source_error'] or c['max_budget_error']>=gate['max_energy_budget_error_J_m3'] or c['min_dissipation']<0:return False
            if any(s['max_strain_error']>=gate['max_solver_strain_error'] for s in c['independent_solvers']):return False
    return compare_saved(a,b)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=run();dest=ROOT/'clay_sims_results.json'
    if args.check:
        if not reproduction_check(result,json.loads(dest.read_text())):raise SystemExit('Clay reproduction failed')
    else:dest.write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('main_runs','uncoupled_runs','independent_solver_runs','accuracy_gates_passed')}))
    if not result['accuracy_gates_passed']:raise SystemExit('Clay accuracy gate failed; all outcomes retained')
