import json,unittest
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from followup_model import *

class FogChecks(unittest.TestCase):
    def test_maxwell_radius_squared_against_exact_open_reservoir(self):
        c=Fog(RH=.5,cooling=False,kelvin=False,open_water_reservoir=True,end=.03)
        z=fog_run(c)
        slope=-2*2.5e-5*vapor_density(c.T)*(1-c.RH)/RHO
        np.testing.assert_allclose(z['radius']**2,c.radius**2+slope*z['times'],rtol=2e-9,atol=1e-21)
    def test_held_water_recovers_original_henry_transient(self):
        c=Fog(water_exchange=False,end=.05)
        z=fog_run(c);m=H298*R*c.T;v=c.liquid_kg_m3/RHO
        kla=3/(1/(2e-9/c.radius)+m/(2e-5/c.radius))/c.radius
        eq=m*v/(1+m*v)
        exact=eq[:,None]*(-np.expm1(-((1+m*v)*kla)[:,None]*z['times']))
        np.testing.assert_allclose(z['state'][3:7],exact,rtol=2e-6,atol=2e-15)
    def test_saturated_flat_control(self):
        z=fog_run(Fog(RH=1,kelvin=False,end=.2))
        np.testing.assert_allclose(z['radius'],1e-5,rtol=1e-12)
    def test_closed_mass_and_latent_heat_budgets(self):
        for rh in [.5,1.005]:
            z=fog_run(Fog(RH=rh,end=.5))
            self.assertLess(z['water_relative_error'],2e-7)
            self.assertLess(z['solute_relative_error'],2e-13)
            self.assertLess(z['heat_budget_error'],2e-13)
            self.assertLess(z['heat_balance_residual_W_m'],1e-9)
    def test_condensation_opposite_sign(self):
        z=fog_run(Fog(RH=1.005,end=.2))
        self.assertGreater(z['radius'][-1],1e-5)
        self.assertLess(z['heat_J_m3'][-1],0)
    def test_cooling_slows_evaporation(self):
        a=fog_run(Fog(RH=.5,cooling=False));b=fog_run(Fog(RH=.5,cooling=True))
        self.assertTrue(a['stopped'] and b['stopped'])
        self.assertGreater(b['times'][-1],a['times'][-1])
        self.assertLess(b['Td'][0],298.15)
    def test_finite_water_cannot_saturate_dry_air(self):
        c=Fog(RH=.5);z=fog_run(c)
        ceiling=c.RH+c.liquid_kg_m3/vapor_density(c.T)
        self.assertLess(z['RH'][-1],ceiling)
        self.assertLess(z['RH'][-1],.53)
    def test_cutoff_not_zero_water(self):
        z=fog_run(Fog(RH=.5))
        self.assertTrue(z['stopped']);self.assertAlmostEqual(z['radius'][-1],2e-6,places=12)
        self.assertGreater(z['state'][0,-1]**1.5,0)
    def test_no_solute_transfer_control(self):
        z=fog_run(Fog(solute_exchange=False,end=.1))
        np.testing.assert_array_equal(z['state'][3:7],0.)
        np.testing.assert_array_equal(z['state'][7:11],1.)
    def test_no_chemical_conversion_and_nonnegative_inventories(self):
        z=fog_run(Fog(RH=.9))
        self.assertGreaterEqual(z['state'][3:11].min(),-1e-12)
        np.testing.assert_allclose(z['state'][3:7]+z['state'][7:11],1,atol=2e-13)
    def test_time_step_and_method_agreement(self):
        a=fog_run(Fog(RH=.9,max_step=.2));b=fog_run(Fog(RH=.9,max_step=.05,rtol=2e-10,method='BDF'))
        self.assertLess(abs(a['times'][-1]/b['times'][-1]-1),2e-6)
        np.testing.assert_allclose(a['state'][3:7,-1],b['state'][3:7,-1],rtol=2e-5,atol=2e-12)
    def test_kelvin_surface_equilibrium(self):
        a=1e-5;T=298.15;rv=vapor_density(T)*np.exp(2*SIGMA*MW/(RHO*R*T*a))
        Td,flux,_=interface(T,rv,a)
        self.assertAlmostEqual(Td,T,places=8);self.assertLess(abs(flux),1e-16)
    def test_scenario_domain(self):
        with self.assertRaises(ValueError):fog_run(Fog(T=260))

class ForceChecks(unittest.TestCase):
    def test_image_force_equals_published_equation10(self):
        A=1e-5;r=A*np.array([2.,3.,10.]);q=100*E;Q=20*E;x=r/A
        explicit=KE*q*q/A**2*(-x/(x*x-1)**2+1/x**3+Q/q/x**2)
        np.testing.assert_allclose(electro_force(r,100,20,A),explicit,rtol=1e-12)
    def test_force_is_negative_potential_gradient(self):
        for r in [2e-5,3e-5,1e-4]:
            h=r*1e-5
            derivative=(electro_potential(r+h,100,1)-electro_potential(r-h,100,1))/(2*h)
            self.assertAlmostEqual(float(-derivative/electro_force(r,100,1)),1,places=7)
    def test_neutral_sphere_attraction_independent_of_charge_sign(self):
        self.assertLess(electro_force(3e-5,100,0),0)
        self.assertEqual(electro_force(3e-5,100,0),electro_force(3e-5,-100,0))
    def test_monopole_and_neutral_controls(self):
        self.assertEqual(electro_force(3e-5,100,0,polarization=False),0)
        self.assertEqual(electro_force(3e-5,0,0),0)
        self.assertGreater(electro_force(3e-5,100,100),0)
    def test_weak_like_charge_can_attract_in_sphere_model(self):
        self.assertLess(electro_force(3e-5,100,1),0)
        self.assertGreater(electro_force(3e-5,100,1,polarization=False),0)
    def test_far_field_dipole_limit(self):
        A=1e-5;r=1000*A
        leading=-2*KE*(100*E)**2*A**3/r**5
        self.assertLess(abs(electro_force(r,100,0,A)/leading-1),2e-6)
    def test_coulomb_stokes_exact_limit(self):
        z=deterministic_pair(q_e=100,Q_e=100,polarization=False,end=.1)
        b=mobility(1e-7)[0]+mobility(1e-5)[0]
        exact=((3e-5)**3+3*b*KE*(100*E)**2*z['times'])**(1/3)
        np.testing.assert_allclose(z['radius'],exact,rtol=2e-8)
    def test_electrostatic_energy_dissipated_as_drag_heat(self):
        for q,Q in [(100,0),(100,100),(100,-100)]:
            z=deterministic_pair(q_e=q,Q_e=Q)
            self.assertLess(z['energy_relative_residual'],2e-7)
            self.assertTrue(np.all(np.diff(z['heat'])>=-1e-25))
    def test_boundary_stop_before_contact(self):
        z=deterministic_pair(q_e=200)
        self.assertTrue(z['stopped']);self.assertAlmostEqual(z['radius'][-1],2e-5,places=12)
    def test_brownian_relative_einstein_limit(self):
        z=brownian_pairs(q_e=0,Q_e=0,A=.01,a=1e-6,end=.001,dt=.001,noise_dt=.001,samples=15000)
        diff=z['final_position']-np.array([.03,0,0])
        self.assertLess(abs(np.mean(np.sum(diff*diff,axis=1))/(6*z['Drelative']*.001)-1),.025)
    def test_repeated_seed(self):
        a=brownian_pairs(end=.01,samples=8);b=brownian_pairs(end=.01,samples=8)
        np.testing.assert_array_equal(a['final_position'],b['final_position'])
    def test_stop_preserves_outer_boundary(self):
        z=brownian_pairs(q_e=200,samples=100,end=.2)
        r=np.linalg.norm(z['final_position'],axis=1)
        self.assertGreaterEqual(r.min(),2e-5-1e-15)
        self.assertTrue(np.any(np.isfinite(z['stops'])))

class MeasurementChecks(unittest.TestCase):
    def test_table_shape_and_anchor_values(self):
        data=json.loads((Path(__file__).parent/'measured_collection.json').read_text())
        self.assertEqual(sum(len(g['CE']) for g in data['groups']),18)
        self.assertEqual(data['groups'][0]['wet_radius_nm'][0],79)
        self.assertEqual(data['groups'][2]['CE'][-1],.00732)
    def test_kernel_ce_units_and_zero_sticking(self):
        a,A=1e-7,5e-5;T=298.15;v=.25
        da,dd=mobility(a,T)[1],mobility(A,T)[1]
        self.assertAlmostEqual(brownian_collection_efficiency(a,A,T,v)*A*A*v/(4*(a+A)*(da+dd)),1)
        self.assertEqual(brownian_collection_efficiency(a,A,sticking=0),0)
    def test_smaller_particle_diffuses_faster(self):
        self.assertGreater(brownian_collection_efficiency(6e-8,5e-5),brownian_collection_efficiency(3e-7,5e-5))
    def test_invalid_geometry(self):
        with self.assertRaises(ValueError):electro_force(1e-5,100,0)
        with self.assertRaises(ValueError):brownian_collection_efficiency(1e-7,5e-5,speed=0)

if __name__=='__main__':unittest.main()
