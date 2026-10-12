import hashlib
import json
import unittest
from pathlib import Path
import numpy as np
from scipy.integrate import quad
import hug_rhythm as h
from hug_calibration import mechanical_matrix

ROOT=Path(__file__).resolve().parent


class RhythmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'hug_rhythm_results.json').read_text())
        cls.truth=json.loads((ROOT/'calibration/synthetic_truth.json').read_text());cls.model=h.Model(cls.truth)

    def test_01_sources_are_pinned(self):
        for path,digest in self.data['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)

    def test_02_scaled_rhs_matches_physical_calibration_equations(self):
        z=np.array([.7,-.3,.02,-.01]);y=z*self.model.scale;q,v,_,_=y
        expected=mechanical_matrix(self.truth['material'],.2,.7,.1,1e-7)@y
        expected[1]+=((.03-3e6*q*q)*v+2e-6)/.2
        np.testing.assert_allclose(self.model.rhs(0,z,2e-6)*self.model.scale,expected,rtol=1e-12,atol=1e-15)

    def test_03_analytic_jacobian_matches_finite_differences(self):
        z=np.array([.7,-.3,.02,-.01]);eps=1e-6
        numeric=np.column_stack([(self.model.rhs(0,z+eps*e)-self.model.rhs(0,z-eps*e))/(2*eps) for e in np.eye(4)])
        np.testing.assert_allclose(self.model.jacobian(z),numeric,rtol=1e-7,atol=1e-9)

    def test_04_energy_identity_includes_active_and_orbital_work(self):
        z=np.array([.7,-.3,.02,-.01]);dz=self.model.rhs(0,np.r_[z,0,0,0],2e-6);eps=1e-6
        derivative=(self.model.energy(z+eps*dz[:4])-self.model.energy(z-eps*dz[:4]))/(2*eps)
        self.assertAlmostEqual(float(derivative),dz[4]+dz[5]-dz[6],places=8)

    def test_05_passive_model_adds_no_power(self):
        model=h.Model(self.truth,True);dz=model.rhs(0,np.array([1.,.4,.1,.02,0,0,0]))
        self.assertEqual(dz[4],0);self.assertEqual(dz[5],0);self.assertGreater(dz[6],0)

    def test_06_unperturbed_origin_stays_at_rest(self):
        np.testing.assert_array_equal(self.model.rhs(0,np.zeros(7)),np.zeros(7))

    def test_07_circular_input_has_two_cycles_per_orbit(self):
        period=5.7;t=np.linspace(0,period,73)
        np.testing.assert_allclose([h.force_at(v,0,period) for v in t],[h.force_at(v+period/2,0,period) for v in t],atol=1e-18)

    def test_08_eccentric_input_breaks_half_orbit_symmetry(self):
        period=5.7;t=np.linspace(0,period,73)
        diff=max(abs(h.force_at(v,.412,period)-h.force_at(v+period/2,.412,period)) for v in t)
        self.assertGreater(diff,1e-6)

    def test_09_orbit_inputs_have_equal_rms_and_zero_mean(self):
        for e in (0,.412,.212,.160,.009,.007,.018):
            norm=h.protocol()['orbital_force_rms_N']
            rms=np.sqrt(quad(lambda t:(h.force_at(t,e,5.7)/norm)**2,0,5.7,epsabs=1e-10)[0]/5.7)
            mean=quad(lambda t:h.force_at(t,e,5.7)/norm,0,5.7,epsabs=1e-10)[0]/5.7
            self.assertAlmostEqual(rms,1,places=9);self.assertAlmostEqual(mean,0,places=9)

    def test_10_crossings_recover_known_sinusoid(self):
        t=np.arange(0,100,.05);q=.2*np.sin(2*np.pi*t/2.85)
        r=h.measurement_metrics(t,q);self.assertEqual(r['status'],'measured');self.assertAlmostEqual(r['mean_period_s'],2.85,places=8)
        self.assertLess(abs(r['mean_half_amplitude_mm']-.2),.001)

    def test_11_hysteresis_rejects_small_zero_crossing_chatter(self):
        t=np.arange(0,100,.01);q=.2*np.sin(2*np.pi*t/3)+.002*np.sin(2*np.pi*t/.03)
        r=h.measurement_metrics(t,q,.002);self.assertEqual(r['status'],'measured');self.assertLess(abs(r['mean_period_s']-3),.001);self.assertEqual(r['cycles'],32)

    def test_12_flat_or_subnoise_signal_has_no_claimed_rhythm(self):
        t=np.arange(100)*.1
        for q in [np.zeros(100),.001*np.sin(t)]:self.assertEqual(h.measurement_metrics(t,q,.001)['status'],'signal_below_detection')

    def test_13_invalid_times_are_rejected(self):
        with self.assertRaises(ValueError):h.measurement_metrics(np.zeros(20),np.arange(20))
        t=np.arange(20,dtype=float);t[2]=np.nan
        with self.assertRaises(ValueError):h.measurement_metrics(t,np.arange(20))

    def test_14_full_state_periodic_orbit_is_closed(self):
        self.assertLess(self.data['autonomous_cycle']['shooting_error_scaled'],1e-7)

    def test_15_floquet_check_establishes_local_attraction(self):
        c=self.data['autonomous_cycle'];self.assertLess(c['neutral_multiplier_error'],1e-6);self.assertLess(c['largest_transverse_multiplier'],.9999)

    def test_16_three_starts_reach_the_same_cycle_section(self):
        self.assertEqual(len(self.data['autonomous_starts']),3)
        for r in self.data['autonomous_starts']:self.assertLess(r['distance_to_cycle_scaled'],h.protocol()['gates']['section_recovery_error_scaled'])

    def test_17_disturbed_cycle_recovers(self):
        d=self.data['disturbance'];self.assertGreater(max(d['section_distance_scaled'][:5]),.001)
        self.assertLess(d['distance_to_cycle_scaled'],h.protocol()['gates']['section_recovery_error_scaled'])

    def test_18_power_off_control_decays(self):
        self.assertLess(self.data['passive']['final_norm_scaled'],1e-4);self.assertLess(self.data['passive']['energy_balance_error_scaled'],1e-5)

    def test_19_numerical_energy_balance_and_solver_controls_pass(self):
        for c in self.data['cases']:
            self.assertLess(c['energy_balance_error_scaled'],1e-5);self.assertLess(c['independent_solver_error_scaled'],2e-6)

    def test_20_cycle_energy_is_supplied_by_feedback(self):
        c=self.data['autonomous_cycle'];self.assertGreater(c['active_work_per_cycle_J'],0)
        self.assertAlmostEqual(c['active_work_per_cycle_J']/c['dissipated_energy_per_cycle_J'],1,places=7)

    def test_21_fixed_fits_predict_new_recordings(self):
        p=[r for r in self.data['cases'] if 'prediction_rmse_mm' in r];self.assertEqual(len(p),10)
        for r in p:self.assertLess(r['prediction_rmse_mm'],h.protocol()['gates']['parameter_prediction_rmse_mm'])

    def test_22_noise_checks_preserve_period_and_amplitude(self):
        for case in self.data['cases']:
            self.assertEqual(len(case['measurement_noise_checks']),6)
            for r in case['measurement_noise_checks']:
                self.assertEqual(r['status'],'measured');self.assertLess(r['period_relative_error'],.002);self.assertLess(r['amplitude_relative_error'],.02)

    def test_23_forcing_comparison_covers_six_eccentricities_and_detuning(self):
        rows=[c for c in self.data['cases'] if c['eccentricity'] is not None];self.assertEqual(len(rows),9)
        self.assertEqual({r['name'] for r in rows if 'control' not in r['name']},{'Circular','Pasiphae','Elara','Himalia','Europa','Callisto','Thebe'})
        self.assertEqual(sum(r['orbit_period_s']==4 for r in rows),2)

    def test_24_repetition_labels_follow_all_four_state_errors(self):
        for c in self.data['cases']:
            if 'orbit_repeat' not in c:continue
            r=c['orbit_repeat'];expected=next((int(n) for n,e in r['return_errors_scaled'].items() if e<h.protocol()['gates']['orbit_repeat_error_scaled']),None)
            self.assertEqual(r['repeat_orbits'],expected)
            self.assertEqual(np.asarray(r['state_scaled']).shape,(41,4))

    def test_25_only_synthetic_data_no_extra_sims_or_physical_claim(self):
        self.assertEqual(self.data['origin'],'synthetic');self.assertEqual(self.data['physical_measurements'],0);self.assertEqual(self.data['additional_sims_runs'],0)

    def test_26_published_recordings_reproduce_observation_metrics(self):
        for c in self.data['cases']:
            o=c['observation'];m=h.measurement_metrics(o['time_s'],o['clean_displacement_mm'])
            self.assertAlmostEqual(m['mean_period_s'],c['clean_metrics']['mean_period_s'],places=7)

    def test_27_calibration_not_refitted_on_rhythm_trials(self):
        cal=json.loads((ROOT/'calibration/synthetic_results.json').read_text())
        self.assertEqual(self.data['fit_trial_ids'],cal['fit_trial_ids'])
        for a,b in [('material','creep'),('mechanics','passive'),('feedback','feedback')]:self.assertEqual(self.data['fitted_parameters'][a],cal['fits'][b]['parameters'])

    def test_28_all_declared_accuracy_gates_pass(self):
        self.assertEqual(h.validate(self.data),self.data['checks']);self.assertTrue(all(self.data['checks'].values()))
        audit=self.data['initial_horizon_audit']
        for key in ('memory_start_error_scaled','disturbed_return_error_scaled','passive_final_norm_scaled'):self.assertGreater(audit[key],audit['gate_scaled'])
        self.assertEqual(self.data['protocol']['gates']['section_recovery_error_scaled'],audit['gate_scaled'])


if __name__=='__main__':unittest.main()
