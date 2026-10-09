"""Later-page addendum: vector-field index and a critical-window junction diagnostic."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from oscillators import junction_rhs,rk4


def field(x,y):return np.array([x*x*y,x*x-y*y])


def basin_diagnostic(dt,duration=600,observe=200):
    cases=[(b,i,start) for b in (.2,2.,10.) for i in (.4,.5,.8,.9,1.,1.025) for start in ('rest','running')]
    beta=np.array([r[0] for r in cases]);bias=np.array([r[1] for r in cases])
    state=np.array([[np.arcsin(min(i,1)) if start=='rest' else 0 for b,i,start in cases],
                    [0 if start=='rest' else max(i,1.) for b,i,start in cases]],float)
    for step in range(round(duration/dt)):
        state=rk4(state,dt,lambda z:junction_rhs(z,bias,beta))
        if step+1==round((duration-observe)/dt):before=state[0].copy()
    velocity=(state[0]-before)/observe
    return [dict(beta=b,bias=i,initial=start,mean_velocity=float(v)) for (b,i,start),v in zip(cases,velocity)]


def main():
    data=Path('data');out=Path('analysis');target=data/'index_bistability.json'
    if target.exists():raise SystemExit('Refusing to overwrite addendum results.')
    protocol=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       vector_field='(x^2 y, x^2-y^2)',source='User-provided Figure 6.8.5',
       index='Winding of field direction along counterclockwise unit circle; not a dynamical trajectory.',
       junction='Post-analysis check prompted by finite-window disagreement at beta10, bias1. Two initial conditions; dt .04 and .02; duration600, final200. Critical rest state is initialized exactly.',
       status='Additional diagnostic after main numerical results; not preplanned confirmation.')
    (data/'index_bistability_protocol.json').write_text(json.dumps(protocol,indent=2))
    theta=np.linspace(0,2*np.pi,4097);vectors=field(np.cos(theta),np.sin(theta))
    angle=np.unwrap(np.arctan2(vectors[1],vectors[0]));index=float((angle[-1]-angle[0])/(2*np.pi))
    labels=np.arange(9)*np.pi/4;v=field(np.cos(labels),np.sin(labels));v[np.abs(v)<1e-14]=0
    coarse=basin_diagnostic(.04);fine=basin_diagnostic(.02)
    changes=[dict(beta=a['beta'],bias=a['bias'],initial=a['initial'],difference=abs(a['mean_velocity']-b['mean_velocity'])) for a,b in zip(coarse,fine)]
    controls={}
    for name,vector in [('constant',np.array([np.ones_like(theta),np.zeros_like(theta)])),('rotation',np.array([-np.sin(theta),np.cos(theta)])),('saddle',np.array([np.cos(theta),-np.sin(theta)]))]:
        aa=np.unwrap(np.arctan2(vector[1],vector[0]));controls[name]=float((aa[-1]-aa[0])/(2*np.pi))
    result=dict(index=index,index_controls=controls,min_field_norm_on_circle=float(np.linalg.norm(vectors,axis=0).min()),
        nine_vectors=v.T.tolist(),coarse_junction=coarse,refined_junction=fine,
        maximum_junction_step_difference=max(r['difference'] for r in changes),
        checks=dict(index_zero=abs(index)<1e-12,index_controls=all(abs(controls[k]-v)<1e-12 for k,v in [('constant',0),('rotation',1),('saddle',-1)]),nonzero_on_contour=bool(np.linalg.norm(vectors,axis=0).min()>0),
                    junction_step_convergence=all(r['difference']<.005 for r in changes)))
    target.write_text(json.dumps(result,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(12,4))
    axs[0].plot(np.cos(theta),np.sin(theta),c='#777')
    norm=np.linalg.norm(v,axis=0)
    axs[0].quiver(np.cos(labels[:-1]),np.sin(labels[:-1]),v[0,:-1]/norm[:-1],v[1,:-1]/norm[:-1],angles='xy',scale_units='xy',scale=3.5,color='#167d8d')
    for j,t in enumerate(labels[:-1]):axs[0].text(1.23*np.cos(t),1.23*np.sin(t),'1,9' if j==0 else str(j+1),ha='center')
    axs[0].set(aspect='equal',xlim=(-1.6,1.6),ylim=(-1.6,1.6),title='Vectors sampled on the unit circle')
    axs[1].plot(theta/np.pi,angle/np.pi,c='#167d8d');axs[1].set(xlabel='Contour angle / pi',ylabel='Unwrapped field angle / pi',title='Net winding = 0')
    grid=np.linspace(-1.5,1.5,151);xx,yy=np.meshgrid(grid,grid);uu,vv=field(xx,yy)
    axs[2].streamplot(grid,grid,uu,vv,density=.8,color='#538a98',linewidth=.7)
    axs[2].plot(0,0,'o',color='#c26436');axs[2].set(aspect='equal',title='Actual trajectories of the vector field',xlabel='x',ylabel='y')
    fig.suptitle('An index counts vector-direction turns; it does not measure synchronization');fig.tight_layout()
    for extension in ('png','svg'):fig.savefig(out/('vector_index.'+extension),dpi=160,bbox_inches='tight')
    plt.close(fig);print(json.dumps({k:v for k,v in result.items() if 'junction' not in k},indent=2))
    if not all(result['checks'].values()):raise SystemExit(1)


if __name__=='__main__':main()
