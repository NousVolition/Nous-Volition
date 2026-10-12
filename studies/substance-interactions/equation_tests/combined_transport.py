"""All five screenshot systems coupled one-way to the earlier partition model.

This is a manufactured, externally driven kinematic benchmark. The controllers
prescribe a divergence-free shear flow; they do NOT replace molecular forces,
chemical rates, Navier-Stokes momentum, or the gas/water partition law.
Output concentrations are normalized per initial mean gas inventory.
"""
from pathlib import Path
import json,time,unittest
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from equations import radial_exact

ROOT=Path(__file__).resolve().parent
R=8.31446261815324;T=298.15;P=101325.;PHI=5e-7;L=1.;D=2e-5;A=1e-5
NAMES=['CO','acetone','H2O2']
H=np.array([9.7e-6,.27,860.])
XPPM=np.array([1.,1.,.001])
BASE_CONC=XPPM*1e-6*P/(R*T)


def controller_solution(end=180):
    # Dimensionless screenshot times are mapped to a chosen30s time scale.
    # Clock uses its actual hand-relative rate. Saddle node uses3s time scale.
    def rhs(t,z):
        phi,velocity,xs=z
        return [velocity/30,(1.2-np.sin(phi)-.2*velocity)/30,
                (.01+xs*xs)/3 if xs<1 else 0]
    # Use an event and hold the output rather than integrating past blow-up.
    def gate(t,z):return z[2]-1
    gate.terminal=True;gate.direction=1
    sol1=solve_ivp(rhs,(0,end),[0,0,-1],events=gate,dense_output=True,
                   rtol=1e-10,atol=1e-12,max_step=.5)
    stop=float(sol1.t[-1]);state=sol1.y[:,-1].copy()
    if stop<end:
        state[2]=1
        def after(t,z):return [z[1]/30,(1.2-np.sin(z[0])-.2*z[1])/30,0]
        sol2=solve_ivp(after,(stop,end),state,dense_output=True,
            rtol=1e-10,atol=1e-12,max_step=.5)
    else:sol2=None
    def signals(t):
        phase,velocity,xs=(sol1.sol(t) if t<=stop else sol2.sol(t))
        return dict(limit_cycle=float(radial_exact(t/30,.2)*np.cos(t/30)),
            junction=float(np.sin(phase)),clock=float(np.cos(2*np.pi*t/(43200/11))),
            saddle=float(np.clip((xs+1)/2,0,1)),harmonic=float(np.cos(t/30)))
    return signals,stop


def shear_amplitudes(t,signals,case='combined'):
    if case=='no_flow':return 0.,0.
    if case=='steady':return .01,.006
    s=signals(t)
    if case.startswith('without_'):s[case.removeprefix('without_')]=0
    ux=.01*(1+.2*s['limit_cycle']+.2*s['clock'])
    uy=.01*(.6+.2*s['junction']+.1*s['harmonic']+.1*s['saddle'])
    return ux,uy


def exchange(y,dt,enabled=True):
    if not enabled:return y.copy()
    m=H*R*T
    kl=2e-9/A;kg=D/A
    kla=3/(A*(1/kl+m/kg))
    ratio=m*PHI;f=ratio/(1+ratio);decay=np.exp(-kla*(1+ratio)*dt)
    total=y[:,0]+y[:,1]
    liquid=f[:,None,None]*total+(y[:,1]-f[:,None,None]*total)*decay[:,None,None]
    return np.stack([total-liquid,liquid],axis=1)


def simulate(n=48,dt=.25,end=180,case='combined',uptake=True):
    signals,stop=controller_solution(end)
    dx=L/n;grid=(np.arange(n)+.5)*dx
    X,Y=np.meshgrid(grid,grid,indexing='xy')
    # Exact cell averages of the same continuous initial concentration on all grids.
    initial=1+.5*np.sinc(1/n)**2*np.cos(2*np.pi*X/L)*np.cos(2*np.pi*Y/L)
    y=np.zeros((3,2,n,n));y[:,0]=initial
    initial_mass=y.sum(axis=1).mean(axis=(1,2))
    diffusivity=np.array([D,0.])[None,:,None,None]
    sinx=np.sin(2*np.pi*X/L);siny=np.sin(2*np.pi*Y/L)
    def transport_rhs(state,ux,uy):
        velx=ux*siny;vely=uy*sinx
        xp,xm=np.roll(state,-1,-1),np.roll(state,1,-1)
        yp,ym=np.roll(state,-1,-2),np.roll(state,1,-2)
        # Conservative MUSCL fluxes with monotonized-central limited slopes.
        # Face velocities are independent of their face-normal coordinate.
        def slope(minus,plus):
            central=(minus+plus)/2
            magnitude=np.minimum(abs(central),np.minimum(2*abs(minus),2*abs(plus)))
            return np.where(minus*plus>0,np.sign(central)*magnitude,0.)
        sx=slope(state-xm,xp-state);sy=slope(state-ym,yp-state)
        fx=np.maximum(velx,0)*(state+.5*sx)+np.minimum(velx,0)*(xp-.5*np.roll(sx,-1,-1))
        fy=np.maximum(vely,0)*(state+.5*sy)+np.minimum(vely,0)*(yp-.5*np.roll(sy,-1,-2))
        dxf=(fx-np.roll(fx,1,-1))/dx;dyf=(fy-np.roll(fy,1,-2))/dx
        lap=(xp+xm+yp+ym-4*state)/dx**2
        return -dxf-dyf+diffusivity*lap
    count=int(np.ceil(end/dt));h=end/count
    hist=[];max_residual=0.;minimum=1.
    for k in range(count):
        ux,uy=shear_amplitudes((k+.5)*h,signals,case)
        if h*(2*(abs(ux)+abs(uy))/dx+4*D/dx**2)>.9:
            raise ValueError('Timestep violates positivity bound')
        y=exchange(y,h/2,uptake)
        z1=y+h*transport_rhs(y,ux,uy)
        z2=.75*y+.25*(z1+h*transport_rhs(z1,ux,uy))
        y=y/3+2*(z2+h*transport_rhs(z2,ux,uy))/3
        y=exchange(y,h/2,uptake)
        mass=y.sum(axis=1).mean(axis=(1,2))
        max_residual=max(max_residual,float(np.max(abs(mass-initial_mass))))
        minimum=min(minimum,float(y.min()))
        if k%10==0 or k==count-1:
            hist.append(dict(t_s=(k+1)*h,ux_amplitude_m_s=ux,uy_amplitude_m_s=uy,
                CO_gas_variance=float(np.var(y[0,0])),aqueous_percent=(100*y[:,1].mean(axis=(1,2))).tolist()))
    result=dict(case=case,n=n,dt_s=h,end_s=end,
        initial_species_moles=BASE_CONC.tolist(),
        final_total_species_moles=(BASE_CONC*y.sum(axis=1).mean(axis=(1,2))).tolist(),
        final_aqueous_percent=(100*y[:,1].mean(axis=(1,2))).tolist(),
        gas_variance=(np.var(y[:,0],axis=(1,2))).tolist(),
        initial_variance=float(np.var(initial)),
        max_relative_mass_residual=max_residual,minimum_normalized_concentration=minimum,
        gate_full_activation_s=stop,chemical_conversion_moles=[0.,0.,0.])
    return result,y,hist


class CombinedTests(unittest.TestCase):
    def test_exchange_conservation(self):
        y=np.random.default_rng(123).uniform(size=(3,2,5,5))
        z=exchange(y,1)
        np.testing.assert_allclose(z.sum(axis=1),y.sum(axis=1),rtol=1e-14)
        self.assertTrue(np.all(z>=0))

    def test_exchange_equilibrium(self):
        y=np.zeros((3,2,2,2));y[:,0]=1
        z=exchange(y,1000)
        ratio=H*R*T*PHI
        np.testing.assert_allclose(z[:,1,0,0],ratio/(1+ratio),atol=1e-12)

    def test_combined_species_mass_and_positivity(self):
        r,y,h=simulate(n=24,dt=.5,end=20)
        self.assertLess(r['max_relative_mass_residual'],1e-12)
        self.assertGreaterEqual(r['minimum_normalized_concentration'],0)
        self.assertEqual(r['chemical_conversion_moles'],[0,0,0])

    def test_global_partition_independent_of_prescribed_flow(self):
        a=simulate(n=24,dt=.5,end=20,case='combined')[0]
        b=simulate(n=24,dt=.5,end=20,case='no_flow')[0]
        np.testing.assert_allclose(a['final_aqueous_percent'],b['final_aqueous_percent'],atol=1e-10)

    def test_no_uptake_control(self):
        r,y,h=simulate(n=24,dt=.5,end=20,uptake=False)
        self.assertEqual(float(y[:,1].max()),0)

    def test_discrete_flow_divergence(self):
        n=32;x=(np.arange(n)+.5)/n;X,Y=np.meshgrid(x,x)
        u=.012*np.sin(2*np.pi*Y);v=.008*np.sin(2*np.pi*X)
        div=(np.roll(u,-1,1)-u)*n+(np.roll(v,-1,0)-v)*n
        self.assertEqual(float(abs(div).max()),0)

    def test_saddle_controller_event(self):
        signals,stop=controller_solution()
        expected=3*2*np.arctan(10)/.1
        self.assertAlmostEqual(stop,expected,places=7)
        self.assertAlmostEqual(signals(179)['saddle'],1,places=12)

    def test_diffusion_only_analytic_fourier_decay(self):
        n=32;end=20
        r,y,h=simulate(n=n,dt=.5,end=end,case='no_flow',uptake=False)
        grid=(np.arange(n)+.5)/n;X,Y=np.meshgrid(grid,grid)
        exact=1+.5*np.sinc(1/n)**2*np.exp(-8*np.pi**2*D*end)*np.cos(2*np.pi*X)*np.cos(2*np.pi*Y)
        self.assertLess(float(np.max(abs(y[0,0]-exact))),5e-5)


def run():
    start=time.perf_counter();rows=[];fields={};histories={}
    cases=['no_flow','steady','combined']+['without_'+x for x in ['limit_cycle','junction','clock','saddle','harmonic']]
    for case in cases:
        row,field,hist=simulate(case=case)
        rows.append(row);fields[case]=field;histories[case]=hist
    coarse,f0,_=simulate(n=24,dt=.5)
    fine,f1,_=simulate(n=96,dt=.1)
    timefine,ft,_=simulate(n=48,dt=.125)
    medium=fields['combined']
    averaged_medium=medium.reshape(3,2,24,2,24,2).mean(axis=(3,5))
    averaged_fine=f1.reshape(3,2,48,2,48,2).mean(axis=(3,5))
    delta_coarse=float(np.sqrt(np.mean((f0[0,0]-averaged_medium[0,0])**2)))
    delta_fine=float(np.sqrt(np.mean((medium[0,0]-averaged_fine[0,0])**2)))
    delta_time=float(np.sqrt(np.mean((medium[0,0]-ft[0,0])**2)))
    proof=simulate(case='combined',uptake=False)[0]
    fig,ax=plt.subplots(1,3,figsize=(12,4.1),layout='constrained')
    vmin=min(float(fields[k][0,0].min()) for k in ['no_flow','steady','combined'])
    vmax=max(float(fields[k][0,0].max()) for k in ['no_flow','steady','combined'])
    for a,key in zip(ax,['no_flow','steady','combined']):
        im=a.imshow(fields[key][0,0],origin='lower',extent=[0,1,0,1],vmin=vmin,vmax=vmax,cmap='viridis')
        a.set(title={'no_flow':'Diffusion only','steady':'Steady shear flow','combined':'All five controllers'}[key],xlabel='x (m)',ylabel='y (m)')
    fig.colorbar(im,ax=ax,label='CO gas concentration (ppm)')
    fig.suptitle('Combined transport at 180 s: same CO, water, diffusivity and initial field\nPrescribed divergence-free flow; no chemical conversion',fontsize=12)
    fig.savefig(ROOT/'combined_transport.png',dpi=180,bbox_inches='tight')
    fig.savefig(ROOT/'combined_transport.svg',bbox_inches='tight');plt.close(fig)
    summary=dict(description='Manufactured one-way coupling of all five equation-based controllers to conservative two-phase transport',
        conditions=dict(T_K=T,P_Pa=P,domain_m=[1,1,1],periodic_x_y=True,water_volume_fraction=PHI,
            droplet_radius_m=A,gas_diffusivity_m2_s=D,initial_wet_gas_ppm=dict(zip(NAMES,XPPM)),
            assumption='Fixed saturated fog inventory, co-advection without settling, no reactions; imposed flow, not a momentum prediction'),
        species_order=NAMES,runs=rows,no_uptake_control=proof,
        refinement=dict(coarse_24=coarse,fine_96=fine,
            CO_rms_24_vs_restricted48=delta_coarse,CO_rms_48_vs_restricted96=delta_fine,
            CO_rms_dt025_vs_dt0125=delta_time,
            note='Differences between numerical grids, not analytic error estimates. Refinement indicates sensitivity to spatial numerical diffusion.'),
        caveat='The chosen coupling gains/time scales are declared scenario assumptions, not measured chemical effects. Global partition is unchanged by flow because kLa and water volume are fixed.',
        elapsed_seconds=time.perf_counter()-start)
    (ROOT/'combined_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (ROOT/'controller_and_transport_history.json').write_text(json.dumps(histories,indent=2),encoding='utf-8')
    np.savez_compressed(ROOT/'combined_fields.npz',**fields,fine96=f1)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':run()
