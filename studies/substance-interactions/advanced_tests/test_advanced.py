import unittest
import numpy as np
from scipy.integrate import solve_ivp
import advanced_model as m


class CarbonateTests(unittest.TestCase):
    def test_detailed_balance(self):
        k=m.carbonate_constants()
        self.assertAlmostEqual((k['kh']/k['krh'])*k['ka'],k['ko']*k['kw']/k['kro'],places=16)
    def test_true_pka_matches_published_rounding(self):
        self.assertLess(abs(-np.log10(m.carbonate_constants()['ka'])-3.70),.03)
    def test_alkalinity(self):
        for alk in (0.,5e-5,2e-4):
            s=m.speciate_hydrated(1.2e-4,alk)
            self.assertLess(abs(s['bic']+2*s['carb']+s['OH']-s['H']-alk),1e-13)
    def test_carbon_conserved_and_pool_accounted(self):
        z=m.carbonate_run()
        self.assertLess(z['carbon_error'],1e-10)
        np.testing.assert_allclose(z['acid']+z['bic']+z['carb'],z['y'][1],atol=1e-14)
    def test_no_reaction_control(self):
        z=m.carbonate_run(water_scale=0,oh_scale=0,end=2)
        self.assertEqual(z['y'][1,-1],0.)
        self.assertAlmostEqual(z['pH'][-1],7.)
    def test_fixed_pH_analytic(self):
        # Independent reduction at prescribed pH: two pools exchange linearly.
        k=m.carbonate_constants();H=1e-6
        den=H*H+k['ka']*H+k['ka']*k['kb']
        f=k['kh']+k['ko']*k['kw']/H
        b=k['krh']*H*H/den+k['kro']*k['ka']*H/den
        z=solve_ivp(lambda t,y:[f*(1-y[0])-b*y[0]],(0,5),[0],rtol=1e-11,atol=1e-13)
        exact=f/(f+b)*(1-np.exp(-(f+b)*5))
        self.assertLess(abs(z.y[0,-1]-exact),1e-11)
    def test_equilibrium_stationarity(self):
        z=m.carbonate_run(alkalinity=1e-4,end=1000)
        zz=m.carbonate_run(alkalinity=1e-4,hydrated_initial=z['y'][1,-1],end=10)
        self.assertLess(abs(zz['pH'][-1]-zz['pH'][0]),1e-6)


class RadialTests(unittest.TestCase):
    def test_sphere_grid_convergence(self):
        err=[m.fixed_sphere_dirichlet(n)['error'] for n in (20,40,80)]
        self.assertGreater(err[0]/err[1],3.)
        self.assertGreater(err[1]/err[2],3.)
        self.assertLess(err[2],.0011)
    def test_closed_mass(self):
        z=m.radial_uptake(m.water_history(end=.2),cells=20)
        self.assertLess(z['conservation'],1e-9)
        self.assertLess(z['transfer_audit'],1e-10)
    def test_nonvolatile_receding_boundary(self):
        z=m.radial_uptake(m.water_history(end=.2),cells=30,exchange=False,initial_liquid=1.)
        np.testing.assert_allclose(z['liquid'],1.,atol=1e-10)
        self.assertLess(np.min(z['y']),1e-9) # gas/transfer zero
        self.assertGreaterEqual(np.min(z['y'][:30]),-1e-10)
    def test_fixed_geometry_Henry_equilibrium(self):
        h=m.water_history(end=3,evaporate=False)
        z=m.radial_uptake(h,cells=30)
        cap=m.H298[1]*m.R*298.15*.0005/1000
        self.assertLess(abs(z['liquid'][-1]-cap/(1+cap)),1e-9)
    def test_zero_exchange_empty_drop(self):
        z=m.radial_uptake(m.water_history(end=.1),exchange=False,cells=10)
        self.assertEqual(z['liquid'][-1],0.)
    def test_liquid_uniformity_at_equilibrium(self):
        z=m.radial_uptake(m.water_history(end=3,evaporate=False),cells=30)
        c=z['y'][:30,-1]/np.diff(np.linspace(0,1,31)**3)
        self.assertLess(np.ptp(c)/np.mean(c),1e-5)


class FallingTests(unittest.TestCase):
    def test_no_slip(self):
        x=np.array([[1.,0,0],[0,0,1.],[0,.6,.8]])
        np.testing.assert_allclose(m.stokes_velocity(x),0,atol=1e-15)
    def test_far_flow(self):
        np.testing.assert_allclose(m.stokes_velocity(np.array([[1e7,0,0.]])),[[0,0,1]],atol=1e-6)
    def test_divergence_free(self):
        p=np.array([[.7,.9,1.7]]);div=0.;eps=1e-5
        for j in range(3):
            dp=np.zeros((1,3));dp[0,j]=eps
            div+=(m.stokes_velocity(p+dp)[0,j]-m.stokes_velocity(p-dp)[0,j])/(2*eps)
        self.assertLess(abs(div),1e-9)
    def test_phoresis_saturation(self):
        p=m.phoretic_speeds(5e-5,1e-7,273.42,1.)
        self.assertLess(abs(p['vth'])+abs(p['vdf']),1e-12)
    def test_phoretic_directions(self):
        p=m.phoretic_speeds(5e-5,1e-7,273.42,.71)
        self.assertLess(p['vth'],0);self.assertGreater(p['vdf'],0)
        self.assertLess(p['vdf']+p['vth'],0)
    def test_streamline_interception_analytic(self):
        # Stokes streamfunction at equator r=R gives critical upstream flux.
        # Finite upstream-plane flux weighting recovers E=R²-1.5R+.5/R.
        a=.03*5e-5;rr=1.03
        z=m.falling_capture(a=a,samples=2048,brownian=False,phoresis=False,
            dt=.015,bmax=.15,zmax=6,tmax=800)
        exact=rr*rr-1.5*rr+.5/rr
        self.assertLess(abs(z['CE']-exact),3e-5)


class OtherTests(unittest.TestCase):
    def test_peroxide_atoms(self):
        z=m.peroxide_published_rate_audit(8)
        self.assertLess(z['hydrogen_residual'],1e-12)
        self.assertLess(z['oxygen_residual'],1e-12)
    def test_peroxide_analytic(self):
        z=m.peroxide_published_rate_audit(3)
        np.testing.assert_allclose(z['y'][0],.02*np.exp(-.009*z['t']),rtol=1e-9)
    def test_no_arbitrary_peroxide_pH(self):
        with self.assertRaises(ValueError):m.peroxide_published_rate_audit(7)
    def test_ice_aged_upper_bound(self):
        for T in (190,200,210,220):
            self.assertLessEqual(m.ice_capacity(T,aged=True)['total_cm2'],m.ice_capacity(T)['total_cm2'])
    def test_ice_guard(self):
        with self.assertRaises(ValueError):m.ice_capacity(298.15)
    def test_ice_kinetic_equilibrium(self):
        z=m.ice_capacity(200);n=1e10;ka=z['ka_cm3_s'];kd=z['kd_s'];cs=z['adsorbed_cm2']
        np.testing.assert_allclose(ka*n*(z['sites_cm2']-cs),kd*cs,rtol=1e-12)
    def test_charge_distribution(self):
        q,p=m.boltzmann_charges(1e-7,ion_ratio=1.)
        self.assertAlmostEqual(sum(p),1.);np.testing.assert_allclose(p,p[::-1])
    def test_charge_tail(self):
        q,p=m.boltzmann_charges(1e-7,nmax=100)
        self.assertLess(sum(p[abs(q)>=50]),1e-100)
    def test_lubrication_quadrature(self):
        exact,numeric=m.approach_time(1e-5,1e-6)
        self.assertLess(abs(exact-numeric)/exact,1e-12)
        self.assertGreater(exact,m.approach_time(1e-5,1e-6,lubrication=False)[0])


if __name__=='__main__':unittest.main(verbosity=2)
