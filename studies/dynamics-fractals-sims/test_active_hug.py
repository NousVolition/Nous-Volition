"""Constitutive, energy, stability and orbital controls for the active extension."""
import copy
import json
import unittest
import numpy as np
from scipy.integrate import quad
from active_hug import (ROOT, ActiveHug, protocol, raw_tide, tide_rms,
    orbital_force, integrate, energy_error, linear_threshold, validate)
from clay_sims import source
from orbits import protocol as orbit_protocol


class ActiveHugTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved=json.loads((ROOT/'active_hug_results.json').read_text())
        cls.models=[ActiveHug(m) for m in source.materials()]

    def test_protocol_matches_saved(self):
        self.assertEqual(self.saved['protocol'],protocol())

    def test_complete_paired_experiment(self):
        for row in (10,20,30,40):
            self.assertEqual([r['start_index'] for r in self.saved['autonomous'] if r['coefficient_row_stress_Pa']==row],[0,1,2])
            names=['Circular control']+[m['name'] for m in orbit_protocol()['moons']]
            self.assertEqual([r['name'] for r in self.saved['forced'] if r['coefficient_row_stress_Pa']==row],names)
        self.assertEqual(len(self.saved['solver_controls']),32)
        self.assertEqual(len(self.saved['passive']),4)
        self.assertEqual(len(self.saved['gain_controls']),24)
        self.assertEqual(self.saved['additional_sims_runs'],0)

    def test_unchanged_clay_internal_equations(self):
        p=protocol();y=np.array([.8,-.3,.2,-.1]); gamma=p['strain_scale']*y[0]
        for model in self.models:
            m=model.m;u,w=p['strain_scale']*y[2:];s=m['G_M_Pa']*(gamma-u-w)
            dy=model.rhs(0,y); factor=p['time_scale_seconds']/p['strain_scale']
            self.assertAlmostEqual(dy[2],factor*(s-m['G_K_Pa']*u)/m['eta_K_Pa_s'])
            self.assertAlmostEqual(dy[3],factor*s/m['eta_M_Pa_s'])

    def test_equilibrium_and_no_artificial_start_from_exact_rest(self):
        for model in self.models:
            np.testing.assert_array_equal(model.rhs(0,np.zeros(7)),np.zeros(7))
            sol=integrate(model,np.zeros(4),10)
            np.testing.assert_array_equal(sol.y,np.zeros_like(sol.y))

    def test_feedback_adds_small_motion_and_removes_large_motion_energy(self):
        model=self.models[0]
        self.assertGreater(model.rhs(0,[.1,.7,0,0,0,0,0])[4],0)
        self.assertLess(model.rhs(0,[3.,.7,0,0,0,0,0])[4],0)

    def test_jacobian_against_finite_difference(self):
        y=np.array([.8,-.3,.2,-.1]);h=1e-6
        for model in self.models:
            numeric=np.column_stack([(model.rhs(0,y+np.eye(4)[i]*h)-model.rhs(0,y-np.eye(4)[i]*h))/(2*h) for i in range(4)])
            np.testing.assert_allclose(numeric,model.jacobian(y),atol=1e-9,rtol=1e-9)

    def test_local_energy_identity_and_nonnegative_clay_loss(self):
        y=np.array([.8,-.3,.2,-.1,0.,0.,0.]);force=.4
        for model in self.models:
            x,v,u,w=y[:4];s=x-u-w
            gradient=np.array([model.kappa*x+s,v,-s+model.r*u,-s])
            dy=model.rhs(0,y,force)
            self.assertAlmostEqual(gradient@dy[:4],dy[4]+dy[5]-dy[6],places=12)
            self.assertGreaterEqual(dy[6],0)

    def test_passive_control_dissipates_and_settles(self):
        for row in self.saved['passive']:
            self.assertLess(row['final_norm'],protocol()['gates']['passive_final_norm'])
            z=np.array(row['trace']['state']);model=next(m for m in self.models if m.m['stress_Pa']==row['coefficient_row_stress_Pa'])
            self.assertLessEqual(float(np.max(np.diff(model.energy(z)))),1e-8)
            np.testing.assert_array_equal(z[:,4:6],np.zeros_like(z[:,4:6]))

    def test_linear_instability_threshold_has_complex_crossing(self):
        for model in self.models:
            result=linear_threshold(model.m)
            self.assertLess(result['below_leading_real'],0)
            self.assertGreater(result['above_leading_real'],0)
            ev=np.array(result['eigenvalues']);crossing=ev[np.abs(ev[:,0])<1e-8]
            self.assertEqual(len(crossing),2)
            self.assertTrue(np.all(np.abs(crossing[:,1])>.1))

    def test_all_starts_approach_full_state_cycle(self):
        g=protocol()['gates']
        for row in self.saved['autonomous']:
            self.assertLess(row['section_distance_to_shot_cycle'],g['initial_state_cycle_error'])
            self.assertLess(row['metrics']['full_state_return_error'],g['initial_state_cycle_error'])
            self.assertLess(row['metrics']['period_relative_variation'],g['cycle_period_relative_error'])

    def test_periodic_shooting_closes_all_memory_states(self):
        for row in self.saved['cycles']:
            z=np.array(row['cycle_state'])
            self.assertGreater(np.ptp(z[:,0]),1.)
            np.testing.assert_allclose(z[0],z[-1],atol=1e-7,rtol=0)

    def test_cycle_has_one_phase_multiplier_and_contracting_transverse_modes(self):
        for row in self.saved['cycles']:
            multipliers=np.array(row['multipliers']);ev=multipliers[:,0]+1j*multipliers[:,1]
            i=np.argmin(abs(ev-1));self.assertLess(abs(ev[i]-1),1e-6)
            self.assertTrue(np.all(abs(np.delete(ev,i))<protocol()['gates']['transverse_multiplier_max']))
            # Stored monodromy and stored eigenvalues independently agree.
            np.testing.assert_allclose(np.sort_complex(np.linalg.eigvals(row['monodromy'])),np.sort_complex(ev),atol=1e-10)

    def test_perturbations_return_to_cycle_section(self):
        for row in self.saved['cycles']:
            self.assertGreater(row['perturbation_initial_distance'],.1)
            self.assertLess(row['perturbation_return_error'],protocol()['gates']['perturbation_return_error'])

    def test_independent_cycle_work_equals_clay_loss(self):
        for row in self.saved['cycles']:
            self.assertGreater(row['dissipation_per_cycle_scaled'],0)
            self.assertLess(abs(row['active_work_per_cycle_scaled']-row['dissipation_per_cycle_scaled']),1e-7)

    def test_circular_signal_has_half_orbit_period(self):
        t=np.linspace(0,20,401)
        np.testing.assert_allclose(orbital_force(t,0),orbital_force(t+5,0),atol=2e-14,rtol=0)
        np.testing.assert_allclose(raw_tide(t,0),np.sin(4*np.pi*t),atol=3e-14,rtol=0)

    def test_eccentric_signal_keeps_orbit_period_and_differs_from_circle(self):
        t=np.linspace(0,10,101)
        for moon in orbit_protocol()['moons']:
            e=moon['e'];np.testing.assert_allclose(orbital_force(t,e),orbital_force(t+10,e),atol=3e-13,rtol=0)
            self.assertGreater(np.max(abs(orbital_force(t,e)-orbital_force(t,0))),.001)

    def test_all_orbital_signals_have_zero_mean_equal_rms(self):
        for e in [0]+[m['e'] for m in orbit_protocol()['moons']]:
            phases=np.linspace(0,1,101)
            np.testing.assert_allclose([raw_tide(float(p),e) for p in phases],raw_tide(phases,e),atol=1e-11,rtol=1e-11)
            mean=quad(lambda p:float(raw_tide(p,e))/tide_rms(e),0,1,epsabs=1e-11)[0]
            rms=quad(lambda t:float(orbital_force(t,e))**2,0,10,epsabs=1e-11)[0]/10
            self.assertAlmostEqual(mean,0,places=10)
            self.assertAlmostEqual(rms,protocol()['orbital_force_rms']**2,places=10)

    def test_forced_repeat_classification_uses_full_state(self):
        for row in self.saved['forced']:
            z=np.array(row['strobe_state'])
            for n in (1,2,3,4):
                expected=float(np.max(abs(z[-10:]-z[-10-n:-n])))
                self.assertAlmostEqual(row['strobe_return_errors'][str(n)],expected,places=13)
            matches=[n for n in (1,2,3,4) if row['strobe_return_errors'][str(n)]<1e-5]
            self.assertEqual(row['detected_repeat_orbits'],matches[0] if matches else None)

    def test_all_energy_and_independent_solver_gates(self):
        self.assertTrue(validate(self.saved))

    def test_short_new_run_energy_balance(self):
        for model in self.models:
            sol=integrate(model,[.3,.2,-.1,.05],20,lambda t:float(orbital_force(t,.412)))
            self.assertLess(energy_error(model,sol),protocol()['gates']['energy_balance_error'])

    def test_saved_failure_is_rejected(self):
        bad=copy.deepcopy(self.saved);bad['cycles'][0]['largest_transverse_modulus']=1.1
        with self.assertRaises(AssertionError):validate(bad)


if __name__=='__main__':unittest.main()
