"""Frozen falling_capture versus unused literature data; see both protocol files.
Run python run_external.py (minutes). No network access and no physical tuning.
"""
from pathlib import Path
import sys,json,hashlib,csv,time,platform
import numpy as np
from scipy.stats import t as student_t
HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent/'advanced_tests'
PROTOCOL=json.loads((HERE/'protocol.json').read_text())
def verify_model():
    for name,want in PROTOCOL['source_sha256'].items():
        got=hashlib.sha256((FROZEN/name).read_bytes()).hexdigest()
        if got!=want:raise RuntimeError(f'Frozen model changed: {name}')
verify_model()
sys.path.insert(0,str(FROZEN))
from advanced_model import falling_capture,phoretic_speeds,stokes_velocity

def measurements():
    with (HERE/'measurements.csv').open() as f:rows=list(csv.DictReader(f))
    for r in rows:
        for k in r:
            if k not in ('source','flag'):r[k]=float(r[k])
        r['row']=int(r['row'])
    return rows

def nominal(r):
    p=dict(PROTOCOL['numerics']);p.pop('seeds')
    return dict(p,A=r['drop_diameter_mm']*1e-3/2,
                a=r['dphysical_um']*1e-6/2,T=293.15,RH=r['RH_fraction'],U=4.7)

def jobs(rows):
    for r in rows:yield r,'nominal',nominal(r)
    for r in rows:
        if r['row'] not in [1,5,8]:continue
        for dt in [.0125,.00625]:yield r,f'dt_{dt}',dict(nominal(r),dt=dt)
        yield r,'long_time',dict(nominal(r),tmax=1000)
        yield r,'wide_domain',dict(nominal(r),bmax=1.2,zmax=16,samples=16384,tmax=1000)
        for key,vals in {'T':[288.15,298.15],'RH':[.72,.82],'U':[4.5,4.9]}.items():
            for val in vals:yield r,f'{key}_{val}',dict(nominal(r),**{key:val})
        for key in ['phoresis','brownian','interception']:
            yield r,'no_'+key,dict(nominal(r),**{key:False})

def aggregate(batch,p):
    vals=np.array([x['CE'] for x in batch]);mean=float(vals.mean())
    half=float(student_t.ppf(.975,len(vals)-1)*vals.std(ddof=1)/np.sqrt(len(vals)))
    n=sum(x['samples'] for x in batch);hits=sum(x['hits'] for x in batch)
    # inlet maximum <=1: Stokes vz<=1; ph*z/r^3 positive but < |ph|/zmax^2.
    pp=phoretic_speeds(p['A'],p['a'],p['T'],p['RH'])
    ph=(pp['vdf']+pp['vth'])/p['U'] if p.get('phoresis',True) else 0.
    # Safe global upper on this inlet disk; does not assume <=1.
    wmax=1+abs(ph)/p['zmax']**2
    upper=p['bmax']**2*wmax*(-np.expm1(np.log(.05)/n)) if hits==0 else None
    return dict(mean_CE=mean,seed_CI95_low=max(0.,mean-half),seed_CI95_high=mean+half,
       hits=hits,paths=n,zero_hit_CE95_upper=upper,
       censored_mean=float(np.mean([x['censored_bound'] for x in batch])),
       censored_max=max(x['censored_bound'] for x in batch),Re=batch[0]['Re'],Pe=batch[0]['Pe'])

def main():
    out=HERE/'results';out.mkdir(exist_ok=True)
    records=[];summary=[];start=time.time()
    cache={}
    for r,tag,p in jobs(measurements()):
        batch=[]
        for seed in PROTOCOL['numerics']['seeds']:
            key=json.dumps(dict(p,seed=seed),sort_keys=True)
            if key not in cache:
                z=falling_capture(**p,seed=seed)
                cache[key]={k:v for k,v in z.items() if k not in ('t','traces','hit')}
            z=cache[key];batch.append(z)
            records.append(dict(row=r['row'],scenario=tag,seed=seed,**(p | z)))
        a=aggregate(batch,p)
        a.update(row=r['row'],scenario=tag,observed_CE=r['CE'],
                 predicted_over_observed=a['mean_CE']/r['CE'],
                 zero_hit_upper_over_observed=(a['zero_hit_CE95_upper']/r['CE'] if a['zero_hit_CE95_upper'] is not None else None))
        summary.append(a)
        (out/'cases.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
        print(f"row {r['row']} {tag}: CE={a['mean_CE']:.5g}, hits={a['hits']}, censored={a['censored_mean']:.5g}",flush=True)
    with (out/'seeds.csv').open('w',newline='') as f:
        fields=list(dict.fromkeys(k for r in records for k in r))
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
    with (out/'comparisons.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    metadata=dict(elapsed_s=time.time()-start,python=sys.version,numpy=np.__version__,
       platform=platform.platform(),unique_simulations=len(cache),simulated_paths=sum(z['samples'] for z in cache.values()),
       frozen_sha256=PROTOCOL['source_sha256'],input_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest()
       for n in ['measurements.csv','continuation_protocol.json','protocol.json','run_external.py']})
    (out/'run_metadata.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata),flush=True)
if __name__=='__main__':main()
