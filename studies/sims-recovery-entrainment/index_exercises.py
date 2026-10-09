"""Visible index exercises 6.8.2--6.8.11; exact deductions plus winding checks."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np


def winding(v):
    angle=np.unwrap(np.arctan2(v[1],v[0]))
    return float((angle[-1]-angle[0])/(2*np.pi))


def main():
    data=Path('data');out=Path('analysis');target=data/'index_exercises.json'
    if target.exists():raise SystemExit('Refusing to overwrite index results.')
    (data/'index_exercises_protocol.json').write_text(json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      source='Supplied exercises 6.8.2--6.8.11; only visible text addressed.',
      checks='4097 samples on circles of radii .1 and 1; no field zeros on the sampled contours.',
      note='Dulac divergence supplements index theory in 6.8.7; a +1 interior equilibrium is not ruled out by index alone.'),indent=2))
    functions=[lambda x,y:np.array([x*x,y]),lambda x,y:np.array([y-x,x*x]),
               lambda x,y:np.array([y**3,x]),lambda x,y:np.array([x*y,x+y])]
    equations=['(x^2, y)','(y-x, x^2)','(y^3, x)','(xy, x+y)'];expected=[0,0,-1,0]
    theta=np.linspace(0,2*np.pi,4097);rows=[]
    for number,fn,eq,index in zip(range(2,6),functions,equations,expected):
        values=[]
        for radius in (.1,1):
            vector=fn(radius*np.cos(theta),radius*np.sin(theta))
            values.append(dict(radius=radius,index=winding(vector),minimum_norm=float(np.linalg.norm(vector,axis=0).min())))
        rows.append(dict(exercise=f'6.8.{number}',field=eq,equilibria=[[0,0]],exact_index=index,numerical=values))
    complex_rows=[]
    for conjugate in (False,True):
        for k in (1,2,3):
            z=np.exp(1j*theta);f=(np.conj(z) if conjugate else z)**k
            complex_rows.append(dict(conjugate=conjugate,k=k,index=winding([f.real,f.imag]),expected=-k if conjugate else k))
    # A polynomial counterexample: only r=1 and r=2 are periodic circles;
    # radial motion is strictly outward in the annulus and angular direction reverses.
    q=np.linspace(1.0001,3.9999,1000);radial=(q-1)*(4-q)
    check=dict(unusual_indices=all(abs(v['index']-r['exact_index'])<1e-12 and v['minimum_norm']>0 for r in rows for v in r['numerical']),
      complex_indices=all(abs(r['index']-r['expected'])<1e-12 for r in complex_rows),
      counterexample_annulus_no_equilibria=bool(np.all(radial>0)),opposite_cycle_directions=(1-2.5<0 and 4-2.5>0))
    result=dict(unusual=rows,complex=complex_rows,checks=check,all_passed=all(check.values()),
       cycle_count='N + F + C - S = 1 for usual isolated fixed points inside a simple periodic orbit bounding a disk.',
       three_cycles='Outer index1 minus inner indices1+1 leaves index -1 in the intervening region, so at least one equilibrium is required.',
       opposite_rotation_counterexample='q=x^2+y^2; g=(q-1)(4-q); w=q-2.5; xdot=g*x-w*y, ydot=w*x+g*y. No equilibrium in 1<r<2.',
       no_cycle_field_equilibria=[dict(point=[0,0],kind='saddle',index=-1),dict(point=[2,0],kind='saddle',index=-1),dict(point=[-2,0],kind='stable node',index=1),dict(point=[1,3],kind='stable focus',index=1)],
       no_cycle_proof='Axes are invariant. In each open quadrant B=1/(xy) gives div(BF)=-2x/y, with fixed nonzero sign. Bendixson-Dulac excludes cycles. Index alone does not exclude one enclosing (1,3).',
       surfaces='The disk statement survives on surfaces. Noncontractible loops on a cylinder or torus do not bound such disks. A simple loop on the sphere bounds two disks; smooth tangent fields have total index2.')
    target.write_text(json.dumps(result,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,3,figsize=(11,7));grid=np.linspace(-1.2,1.2,100);xx,yy=np.meshgrid(grid,grid);z=xx+1j*yy
    for ax,row in zip(axs.ravel(),complex_rows):
        f=(np.conj(z) if row['conjugate'] else z)**row['k'];ax.streamplot(grid,grid,f.real,f.imag,density=.8,color='#538a98',linewidth=.6)
        ax.plot(0,0,'o',color='#c26436');ax.set(aspect='equal',title=f"{'conjugate(z)' if row['conjugate'] else 'z'}^{row['k']} · index {row['expected']:+d}",xlabel='x',ylabel='y')
    fig.suptitle('Complex vector fields: winding can exceed +1 or -1 at a degenerate equilibrium');fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/('complex_fields.'+ext),dpi=150,bbox_inches='tight')
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4));angle=np.linspace(0,2*np.pi,400)
    for r in (1,2):
        axs[0].plot(r*np.cos(angle),r*np.sin(angle),color='#167d8d');sign=np.sign(r*r-2.5)
        axs[0].annotate('',xy=(r*np.cos(sign*.18),r*np.sin(sign*.18)),xytext=(r,0),arrowprops=dict(arrowstyle='->',color='#c26436',lw=2))
    axs[0].plot(0,0,'o',color='#c26436');axs[0].set(aspect='equal',title='Opposite rotations, no equilibrium between',xlabel='x',ylabel='y')
    radius=np.linspace(.1,2.4,400);axs[1].plot(radius,radius*(radius**2-1)*(4-radius**2),label="r'");axs[1].plot(radius,radius**2-2.5,label="theta'")
    axs[1].axhline(0,color='#777',lw=.7);axs[1].set(xlabel='Radius',title='The radial component stays nonzero for 1<r<2');axs[1].legend();fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(out/('index_counterexample.'+ext),dpi=150,bbox_inches='tight')
    plt.close(fig);print(json.dumps(result,indent=2))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
