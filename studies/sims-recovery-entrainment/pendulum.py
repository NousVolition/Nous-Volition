"""Additional supplied energy portrait: conservative theta'' + sin(theta) = 0."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from oscillators import rk4


def rhs(z):return np.array([z[1],-np.sin(z[0])])
def energy(z):return .5*z[1]**2-np.cos(z[0])


def integrate(initial,dt,duration):
    state=np.array(initial,float);e0=energy(state);maximum=0.
    for _ in range(round(duration/dt)):
        state=rk4(state,dt,rhs);maximum=max(maximum,float(abs(energy(state)-e0)))
    return dict(initial=initial,dt=dt,duration=duration,energy=float(e0),
                final=state.tolist(),maximum_energy_error=maximum)


def main():
    data=Path('data');out=Path('analysis')
    record=data/'pendulum.json'
    if record.exists():raise SystemExit('Refusing to overwrite pendulum results.')
    protocol=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  equation="theta'=v; v'=-sin(theta)",energy='v^2/2 - cos(theta)',
                  cases=[[.4,0],[0,1.8],[0,2.2]],duration=100,steps=[.02,.01],
                  damping=dict(b=.2,cases=[[.4,0],[0,1.8],[0,3.2]],duration=80,energy_balance='E(t)-E(0)+integral(b*v^2)=0'),
                  separatrix='Exact theta=4 atan(exp(t))-pi, v=2 sech(t), tested to t=10 only.',
                  status='Additional calculation specified after the main ensemble, prompted by a later supplied page.')
    (data/'pendulum_protocol.json').write_text(json.dumps(protocol,indent=2))
    runs=[integrate(z,dt,100) for z in protocol['cases'] for dt in protocol['steps']]
    separatrix=[integrate([0,2],dt,10) for dt in protocol['steps']]
    exact=np.array([4*np.arctan(np.exp(10))-np.pi,2/np.cosh(10)])
    for row in separatrix:row['exact_endpoint_max_error']=float(np.max(abs(np.array(row['final'])-exact)))
    checks=dict(centers_energy_minus_one=bool(np.isclose(energy(np.array([0,0])), -1)),
                saddles_energy_one=bool(np.isclose(energy(np.array([np.pi,0])),1)),
                energy_error_below_one_millionth=all(r['maximum_energy_error']<1e-6 for r in runs),
                refinement_reduces_energy_error=all(runs[i+1]['maximum_energy_error']<runs[i]['maximum_energy_error'] for i in (0,2,4)),
                separatrix_refined_endpoint=separatrix[1]['exact_endpoint_max_error']<1e-5,
                conservative_energy_derivative=bool(np.allclose([np.sin(x)*v+v*(-np.sin(x)) for x,v in ((.3,2.),(2.,-.4))],0)))
    damping=[]
    for initial in ([.4,0],[0,1.8],[0,3.2]):
        for dt in (.02,.01):
            z=np.array(initial,float);states=[z.copy()];e0=float(energy(z));loss=0.;largest_increase=0.
            for _ in range(round(80/dt)):
                before=z.copy();z=rk4(z,dt,lambda q:np.array([q[1],-np.sin(q[0])-.2*q[1]]))
                loss+=.2*dt*(before[1]**2+z[1]**2)/2
                largest_increase=max(largest_increase,float(energy(z)-energy(before)));states.append(z.copy())
            damping.append(dict(initial=initial,dt=dt,energy_balance_error=abs(float(energy(z))-e0+loss),
                                largest_energy_increase=largest_increase,final=z.tolist(),states=np.array(states)))
    checks['damped_energy_nonincreasing']=all(r['largest_energy_increase']<1e-10 for r in damping)
    checks['damped_energy_balance']=all(r['energy_balance_error']<1e-3 for r in damping)
    result=dict(runs=runs,separatrix=separatrix,damping=[{k:v for k,v in r.items() if k!='states'} for r in damping],checks=checks,all_passed=all(checks.values()))
    record.write_text(json.dumps(result,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    theta=np.linspace(-3*np.pi,3*np.pi,700);velocity=np.linspace(-3,3,240)
    xx,yy=np.meshgrid(theta,velocity);ee=.5*yy**2-np.cos(xx)
    fig,ax=plt.subplots(figsize=(11,4.3))
    ax.contour(xx,yy,ee,levels=[-.9,-.5,0,.5,1.5,2.5,3.5],colors='#538a98',linewidths=.8)
    ax.contour(xx,yy,ee,levels=[1],colors='#c26436',linewidths=2)
    qx,qy=np.meshgrid(np.linspace(-3*np.pi,3*np.pi,31),np.linspace(-2.8,2.8,13))
    u=qy;v=-np.sin(qx);norm=np.hypot(u,v);norm[norm==0]=1
    ax.quiver(qx,qy,u/norm,v/norm,color='#4b5960',alpha=.45,scale=48)
    centers=np.arange(-2,3,2)*np.pi;saddles=np.arange(-3,4,2)*np.pi
    ax.scatter(centers,np.zeros(3),c='#157d8d',s=35,label='Centers: E = -1')
    ax.scatter(saddles,np.zeros(4),c='#c26436',marker='x',s=45,label='Saddles and separatrix: E = 1')
    ax.set_xticks(np.arange(-3,4)*np.pi,['-3pi','-2pi','-pi','0','pi','2pi','3pi'])
    ax.set(xlabel='Angle theta (unwrapped)',ylabel='Angular velocity v',title='Conservative pendulum: libration, separatrix, rotation')
    ax.legend(loc='upper center',ncol=2);fig.tight_layout()
    for extension in ('png','svg'):fig.savefig(out/('pendulum.'+extension),dpi=160,bbox_inches='tight')
    plt.close(fig)
    fig=plt.figure(figsize=(7,6));ax=fig.add_subplot(111,projection='3d')
    angle=np.linspace(-np.pi,np.pi,500)
    for level,color in [(-.5,'#167d8d'),(.5,'#548e47'),(1,'#c26436'),(2,'#785cb4')]:
        speed=np.sqrt(np.maximum(0,2*(level+np.cos(angle))));speed[level+np.cos(angle)<0]=np.nan
        for sign in (1,-1):ax.plot(np.cos(angle),np.sin(angle),sign*speed,color=color,lw=2,label=f'E={level:g}' if sign==1 else None)
    for height in (-2.6,0,2.6):ax.plot(np.cos(angle),np.sin(angle),np.full_like(angle,height),color='#aaaaaa',alpha=.3)
    ax.scatter([1,-1],[0,0],[0,0],c=['#167d8d','#c26436'],s=40)
    ax.set(xlabel='cos(theta)',ylabel='sin(theta)',zlabel='v',title='The same angle after a full turn: phase space is a cylinder')
    ax.view_init(22,38);ax.legend();fig.tight_layout()
    for extension in ('png','svg'):fig.savefig(out/('cylinder.'+extension),dpi=160,bbox_inches='tight')
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for row in damping[::2]:
        z=row['states'];time=np.arange(len(z))*row['dt'];label=str(row['initial'])
        axs[0].plot(z[:,0],z[:,1],label=label);axs[1].plot(time,.5*z[:,1]**2-np.cos(z[:,0]),label=label)
    axs[0].set(xlabel='Unwrapped angle',ylabel='v',title='Damping b=0.2: spiraling toward rest');axs[0].legend(title='Initial [angle, speed]',fontsize=8)
    axs[1].set(xlabel='Dimensionless time',ylabel='Energy',title="E' = -b v^2: energy cannot increase");axs[1].axhline(-1,color='#777',ls=':')
    fig.tight_layout()
    for extension in ('png','svg'):fig.savefig(out/('damping.'+extension),dpi=160,bbox_inches='tight')
    plt.close(fig);print(json.dumps(result,indent=2))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
