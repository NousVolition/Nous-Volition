"""Physics and numerical verification. No empirical environmental validation."""
import unittest
import numpy as np
from model import *


class PhysicsTests(unittest.TestCase):
    def test_henry_units_known_CO(self):
        self.assertAlmostEqual(9.7e-6*101325, .9828525) # mol/m3 at 1 atm pure CO
        self.assertAlmostEqual(henry(.27,5500,298.15),.27)

    def test_partition_closed_analytic_and_budget(self):
        for H in [9.7e-6,.27,860]:
            y,f,k,_=partition(H,298.15,1,5e-7,np.linspace(0,600,201),mode='fog')
            np.testing.assert_allclose(y,f*(-np.expm1(-k*np.linspace(0,600,201))),atol=3e-10,rtol=2e-8)
            self.assertLess(abs((1-y[-1])+y[-1]-1),1e-14)
            self.assertTrue(np.all(y>=-1e-16)); self.assertLessEqual(y.max(),1)

    def test_zero_transfer_control(self):
        y,*_=partition(.27,298.15,1,.001,np.array([0,600]),bulk_kLa=0)
        np.testing.assert_array_equal(y,[0,0])

    def test_carbonate_charge_and_carbon(self):
        r=carbonate_closed()
        self.assertLess(abs(r['charge_residual_M']),1e-14)
        self.assertLess(abs(r['carbon_residual_mol']),1e-12)
        self.assertTrue(5.5<r['pH']<5.7)

    def test_carbonate_pure_water_limit(self):
        self.assertAlmostEqual(carbonate_from_co2(0)['pH'],7,places=10)

    def test_carbonate_blocks_temperature_extrapolation(self):
        with self.assertRaises(ValueError):carbonate_closed(T=280)

    def test_transport_analytic_grid_convergence(self):
        errors=[]
        for n in [24,48,96]:
            z=transport(n=n,dt=.004)
            self.assertLess(abs(z['mean']-1),2e-12)
            self.assertGreater(z['minimum'],0)
            errors.append(z['relative_L2'])
        self.assertLess(errors[1],errors[0]*.65);self.assertLess(errors[2],errors[1]*.65)

    def test_transport_positivity_bound(self):
        with self.assertRaises(ValueError):transport(n=192,dt=1)

    def test_inert_no_flow_no_diffusion(self):
        z=transport(n=16,u=0,v=0,diffusivity=0,dt=.1)
        np.testing.assert_allclose(z['field'],z['initial'],atol=1e-14)

    def test_capture_reservoir(self):
        z=transport(n=24,dt=.01,decay=.1)
        self.assertLess(abs(z['mean']+z['captured']-1),1e-13)
        self.assertLess(z['sink_analytic_error'],1e-8)

    def test_coulomb_stokes_limit_both_signs(self):
        for sign in [-1,1]:
            z=particle_pairs(a=1e-5,q1_e=1000,q2_e=sign*1000,r0=2e-4,
                end=5,dt=.001,samples=1,brownian=False)
            exact=pair_analytic(2e-4,5,1e-5,1000,sign*1000)
            self.assertLess(abs(z['final_separation_m'][0]/exact-1),2e-5)

    def test_no_charge_no_brownian(self):
        z=particle_pairs(q1_e=0,q2_e=0,samples=1,brownian=False)
        self.assertAlmostEqual(z['final_separation_m'][0],2e-5,places=14)

    def test_charged_neutral_monopole_control(self):
        z=particle_pairs(q1_e=1000,q2_e=0,samples=1,brownian=False)
        self.assertAlmostEqual(z['final_separation_m'][0],2e-5,places=14)

    def test_seed_repeatability(self):
        a=particle_pairs(samples=5,end=.01,seed=77)
        b=particle_pairs(samples=5,end=.01,seed=77)
        np.testing.assert_array_equal(a['traces_m'],b['traces_m'])

    def test_brownian_einstein_msd(self):
        # 2 particles × 3 Cartesian coordinates. Expected <|dx|²> = 6Dt.
        z=particle_pairs(a=1e-6,q1_e=0,q2_e=0,r0=.01,end=.01,dt=.001,
            samples=10000,trace_count=10000,seed=81)
        d=z['traces_m'][-1]-z['traces_m'][0]
        msd=np.sum(d*d,axis=2).mean()
        self.assertLess(abs(msd/(6*z['particle_D_m2_s']*.01)-1),.03)

    def test_validity_stop_before_contact(self):
        z=particle_pairs(q1_e=100,q2_e=-100,end=1,samples=1,brownian=False)
        self.assertEqual(z['stopped_fraction'],1)
        self.assertGreater(z['final_separation_m'][0],2e-6)

    def test_stokes_continuum_and_slip(self):
        b,D,c=mobility(1e-5,slip=False)
        self.assertAlmostEqual(b*6*np.pi*air_mu()*1e-5,1)
        self.assertAlmostEqual(D/(KB*298.15*b),1)
        self.assertGreater(mobility(1e-7)[2],1)

    def test_saturation_reference(self):
        self.assertLess(abs(saturation(273.16,True)-611.657),.02)
        self.assertLess(abs(saturation(298.15)-3169.9),2)
        self.assertLess(saturation(263.15,True),saturation(263.15,False))

    def test_water_ice_exchange_sign_and_conservation(self):
        ice=vapor_exchange();water=vapor_exchange(ice=False)
        self.assertGreater(ice['transferred_water_mg'],0)
        self.assertLess(water['transferred_water_mg'],0)
        for z in [ice,water]:self.assertLess(z['conservation_relative'],1e-12)

    def test_ice_sorption_equilibrium_and_capacity(self):
        z=ice_adsorption()
        self.assertLess(z['equilibrium_error'],1e-8)
        self.assertTrue(np.all(z['gas_fraction']>0))
        self.assertTrue(np.all(z['adsorbed_fractions']>=0))

    def test_ice_sorption_validity_range(self):
        with self.assertRaises(ValueError):ice_adsorption(T=263)

    def test_scavenging_sticking_control(self):
        self.assertEqual(brownian_scavenging(sticking=0)['rate_s_1'],0)
        self.assertGreater(brownian_scavenging()['rate_s_1'],0)

    def test_decomposition_element_conservation(self):
        for f in [0,.1,.8,1]:
            p=decomposition_products(1,f)
            self.assertAlmostEqual(2*p[0]+2*p[1],2)
            self.assertAlmostEqual(2*p[0]+p[1]+2*p[2],2)
            self.assertAlmostEqual(p[2],(1-p[0])/2)

    def test_co_oh_atom_conservation_finite_oxidant(self):
        z=co_oh_kinetics()
        self.assertLess(z['atom_relative_error'],1e-12)
        self.assertLess(z['moles'][2,-1],z['OH_initial_mol'])
        self.assertTrue(np.all(z['moles']>=0))
        self.assertLess(z['combined_k_pressure_correction_fraction'],.0006)

    def test_co_no_oxidant_control(self):
        z=co_oh_kinetics(OH_molecules_cm3=0)
        self.assertEqual(z['CO_converted_percent'],0)

    def test_co_oh_against_exact_second_order_solution(self):
        z=co_oh_kinetics()
        a,b=z['CO_initial_mol'],z['OH_initial_mol']
        u=np.exp(-(a-b)*z['k_m3_mol_s']*z['times_s'])
        exact=a*b*(1-u)/(a-b*u)
        np.testing.assert_allclose(z['moles'][2],exact,rtol=1e-9,atol=1e-22)

    def test_phase_change_mass_energy(self):
        for power in [5,-5,0]:
            z=freezing_melting(power_W=power)
            np.testing.assert_allclose(z['converted_mass_kg']+z['remaining_mass_kg'],.01)
            np.testing.assert_allclose(z['latent_energy_J']+z['unused_heat_after_completion_J'],abs(power)*z['times_s'])


if __name__=='__main__':unittest.main()
