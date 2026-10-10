"""Matched continuous-state SIMS experiments using the supplied dynamics."""
import argparse
import json
import math
import random
from pathlib import Path
import numpy as np
from models import menger_graph, ring_graph
from bridge_checks import references, linear_flow, compare_saved

ROOT=Path(__file__).resolve().parent


def protocol():
    return json.loads((ROOT/'sims_response_protocol.json').read_text())


def graph_cases():
    return [('Menger L1',menger_graph(1)),('Ring 20',ring_graph(20)),
            ('Complete 20',[[j for j in range(20) if j!=i] for i in range(20)])]


def operators(graph):
    n=len(graph)
    adjacency=np.zeros((n,n))
    for i,row in enumerate(graph):
        if len(set(row))!=len(row) or any(j==i or j<0 or j>=n for j in row):
            raise ValueError('Use simple undirected contacts without self loops.')
        adjacency[i,row]=1
    if not np.array_equal(adjacency,adjacency.T) or not np.max(adjacency.sum(axis=1)):
        raise ValueError('Undirected graph with at least one edge required.')
    w=adjacency/np.max(adjacency.sum(axis=1))
    return w,np.diag(w.sum(axis=1))-w


def initial_state(seed,n=20):
    rng=random.Random(seed)
    z=np.array([[rng.uniform(-.6,.6),rng.uniform(-.6,.6)] for _ in range(n)])
    return z-z.mean(axis=0)+np.array([.1,-.04])


def linear_path(initial,laplacian,matrix,times,coupling=2.):
    eigen,vectors=np.linalg.eigh(laplacian)
    modes=vectors.T@initial
    local=np.array([np.column_stack([linear_flow(matrix,e,t) for e in np.eye(2)]) for t in times])
    aligned=vectors@(np.exp(-coupling*np.outer(times,eigen))[:,:,None]*modes)
    return aligned@np.swapaxes(local,1,2)


def reverse_field(state,weights):
    return -(2*np.eye(len(state))+weights)@np.cos(state)


def reversal_path(initial,weights,reverse=False,step=.02,duration=8.,sample=.1):
    if duration!=8 or not math.isclose(round(sample/step)*step,sample,abs_tol=1e-12):
        raise ValueError('This protocol uses duration 8 and whole sample/step ratios.')
    mobility=2*np.eye(len(initial))+weights
    state=np.array(initial,dtype=float);rows=[state.copy()];times=[0.]
    tick=0;stride=round(sample/step)
    for length,sign in [(2.,1),(2.,-1 if reverse else 1),(4.,1)]:
        count=round(length/step)
        if not math.isclose(count*step,length,abs_tol=1e-12):
            raise ValueError('Every intervention segment needs whole time steps.')
        def rhs(z):return -sign*(mobility@np.cos(z))
        for _ in range(count):
            a=rhs(state);b=rhs(state+step*a/2);c=rhs(state+step*b/2);d=rhs(state+step*c)
            state=state+step*(a+2*b+2*c+d)/6;tick+=1
            if tick%stride==0:rows.append(state.copy());times.append(tick*step)
    return np.array(times),np.array(rows)


def response_parameters():
    p=references()['water_properties']['298.15'];h,d=p['H2O'],p['D2O']
    rows=[]
    for name,rho,mu in [('H2O reference',h['rho'],h['mu']),('density change',d['rho'],h['mu']),
                        ('viscosity change',h['rho'],d['mu']),('both changes',d['rho'],d['mu'])]:
        rows.append({'name':name,'r':(mu/rho)/(h['mu']/h['rho']),'q':h['rho']/rho})
    return rows


def rate_path(initial,laplacian,times,rate,gain,switch=4.,coupling=2.):
    if rate<=0 or gain<=0:
        raise ValueError('Positive response rate and input gain required.')
    eigen,vectors=np.linalg.eigh(laplacian)
    decay=rate*(1+coupling*eigen)
    drive=vectors.T@np.ones(len(initial))
    def evolve(z,t,sign):
        target=sign*gain*drive/decay
        return vectors@(target+(vectors.T@z-target)*np.exp(-decay*t))
    at_switch=evolve(initial,switch,1) if switch is not None else None
    return np.array([evolve(initial,t,1) if switch is None or t<=switch
                     else evolve(at_switch,t-switch,-1) for t in times])


def measurements(times,states):
    z=states[:,:,None] if states.ndim==2 else states
    centers=z.mean(axis=1)
    spread=np.sqrt(np.mean(np.sum((z-centers[:,None,:])**2,axis=2),axis=1))
    center_norm=np.linalg.norm(centers,axis=1)
    preference=z[:,:,0]
    unanimous=(np.all(preference>.02,axis=1)|np.all(preference<-.02,axis=1))
    hits=np.flatnonzero(unanimous)
    return {'final_spread':float(spread[-1]),'initial_spread':float(spread[0]),
            'final_mean_norm':float(center_norm[-1]),'peak_mean_norm':float(max(center_norm)),
            'first_choice_unanimity':float(times[hits[0]]) if len(hits) else None,
            'final_choice_unanimity':bool(unanimous[-1]),
            'final_positive_fraction':float(np.mean(preference[-1]>.02)),
            'final_negative_fraction':float(np.mean(preference[-1]<-.02)),
            'final_undecided_fraction':float(np.mean(np.abs(preference[-1])<=.02)),
            'choice_unanimity_sample_fraction':float(np.mean(unanimous)),
            'sampled_agreement_breaks':int(np.sum(unanimous[:-1]&~unanimous[1:]))}


def trace(times,states):
    z=states[:,:,None] if states.ndim==2 else states
    center=z.mean(axis=1)
    spread=np.sqrt(np.mean(np.sum((z-center[:,None,:])**2,axis=2),axis=1))
    return {'time':times.tolist(),'mean_preference':center[:,0].tolist(),
            'mean_response':center[:,1].tolist() if z.shape[2]==2 else None,
            'spread':spread.tolist(),'mean_norm':np.linalg.norm(center,axis=1).tolist()}


def settling_time(times,states,target,switch=4.,confirmation=1.):
    within=np.max(np.abs(states-target),axis=1)<=.05*abs(target)
    remains=np.logical_and.accumulate(within[::-1])[::-1]
    candidates=np.flatnonzero(remains&(times>=switch)&(times<=times[-1]-confirmation+1e-12))
    return float(times[candidates[0]]-switch) if len(candidates) else None


def summary(values):
    values=np.asarray(values,dtype=float);mean=float(np.mean(values))
    half=1.96*float(np.std(values,ddof=1))/math.sqrt(len(values)) if len(values)>1 else 0.
    return {'mean':mean,'normal95':[mean-half,mean+half]}


def experiment(starts=None):
    p=protocol();starts=p['matched_starts'] if starts is None else starts
    times=np.arange(121)*p['sample_interval'];records=[];traces=[];refinements=[]
    cases=references()['linear_reference'];parameters=response_parameters()
    spectra=[]
    for graph_name,graph in graph_cases():
        weights,laplacian=operators(graph)
        eigen=np.linalg.eigvalsh(laplacian)
        spectra.append({'graph':graph_name,'alignment_gap':float(eigen[1]),
                        'mobility_min_eigenvalue':float(np.linalg.eigvalsh(2*np.eye(20)+weights)[0])})
        for start in range(starts):
            initial=initial_state(p['seed']+start)
            for case in cases:
                states=linear_path(initial,laplacian,case['matrix'],times)
                record={'family':'linear','graph':graph_name,'condition':case['name'],'start':start,
                        **measurements(times,states)}
                records.append(record)
                if start==0:traces.append({k:record[k] for k in ['family','graph','condition']}|trace(times,states))
            for reverse in [False,True]:
                rt,states=reversal_path(initial[:,0],weights,reverse)
                record={'family':'reversal','graph':graph_name,'condition':'reverse rule from 2 to 4' if reverse else 'forward',
                        'start':start,**measurements(rt,states),
                        'return_error_at_4':float(np.max(np.abs(states[40]-initial[:,0]))),
                        'final_distance_from_sink_rms':float(np.sqrt(np.mean((states[-1]+math.pi/2)**2)))}
                records.append(record)
                if start==0:
                    traces.append({k:record[k] for k in ['family','graph','condition']}|trace(rt,states)|
                                  {'mean_potential':np.mean(np.sin(states),axis=1).tolist()})
                if start<3:
                    _,fine=reversal_path(initial[:,0],weights,reverse,step=.01)
                    refinements.append({'graph':graph_name,'condition':record['condition'],'start':start,
                                        'max_state_difference':float(np.max(np.abs(fine-states))),
                                        'fine_return_error_at_4':float(np.max(np.abs(fine[40]-initial[:,0])))})
            for parameter in parameters:
                for control in ['fixed input','same target']:
                    rate=parameter['r'];gain=parameter['q'] if control=='fixed input' else rate
                    states=rate_path(initial[:,0],laplacian,times,rate,gain)
                    record={'family':'rate','graph':graph_name,'condition':parameter['name']+' / '+control,
                            'start':start,'rate':rate,'gain':gain,'final_target':-gain/rate,
                            **measurements(times,states),
                            'settling_after_switch':settling_time(times,states,-gain/rate)}
                    records.append(record)
                    if start==0:traces.append({k:record[k] for k in ['family','graph','condition','final_target']}|trace(times,states))
    aggregates=[]
    for family,graph,condition in dict.fromkeys((r['family'],r['graph'],r['condition']) for r in records):
        rows=[r for r in records if (r['family'],r['graph'],r['condition'])==(family,graph,condition)]
        entry={'family':family,'graph':graph,'condition':condition,'runs':len(rows),
               'final_spread':summary([r['final_spread'] for r in rows]),
               'mean_final_norm':float(np.mean([r['final_mean_norm'] for r in rows])),
               'final_choice_unanimity_fraction':float(np.mean([r['final_choice_unanimity'] for r in rows]))}
        if family=='rate':
            settled=[r['settling_after_switch'] for r in rows if r['settling_after_switch'] is not None]
            entry['settled_runs']=len(settled)
            entry['settling_among_confirmed']=summary(settled) if settled else None
        aggregates.append(entry)
    paired=[]
    for case in cases:
        for graph in ['Menger L1','Complete 20']:
            a=[r for r in records if r['family']=='linear' and r['graph']==graph and r['condition']==case['name']]
            b=[r for r in records if r['family']=='linear' and r['graph']=='Ring 20' and r['condition']==case['name']]
            paired.append({'condition':case['name'],'graph_minus_ring':graph,
                           'final_spread_difference':summary([x['final_spread']-y['final_spread'] for x,y in zip(a,b)])})
    return {'protocol':p,'actual_starts':starts,'total_new_sims_trajectories':len(records),
            'family_counts':{name:sum(r['family']==name for r in records) for name in ['linear','reversal','rate']},
            'spectra':spectra,'aggregates':aggregates,'paired_linear_comparisons':paired,
            'reversal_refinements':refinements,'runs':records,'representative_traces':traces}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();computed=experiment();path=ROOT/'sims_response_results.json'
    if args.check:
        if not compare_saved(computed,json.loads(path.read_text())):
            raise SystemExit('FAIL: response results differ beyond roundoff tolerance.')
        print(f"PASS: {computed['total_new_sims_trajectories']} matched continuous SIMS trajectories reproduced.")
    else:
        path.write_text(json.dumps(computed,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(f"Saved {computed['total_new_sims_trajectories']} matched continuous SIMS trajectories.")
