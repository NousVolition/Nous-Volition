import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import numpy as np
from scipy.linalg import expm
from scipy.integrate import quad
import hug_robustness as r
import hug_rhythm as h


class RobustnessEquations(unittest.TestCase):
    def setUp(self):
        self.cfg=r.protocol();self.settings=r.settings();self.models=[h.Model(s['parameters']) for s in self.settings]

    def test_01_ensemble_matches_existing_equations_for_all_parameters(self):
        z=np.random.default_rng(12).normal(0,.4,(35,7));f=np.linspace(-1e-5,1e-5,35)
        np.testing.assert_allclose(r.Ensemble(self.models).rhs(z,f),[m.rhs(0,x,v) for m,x,v in zip(self.models,z,f)],rtol=2e-14,atol=1e-14)

    def test_02_energy_matches_existing_physical_energy(self):
        z=np.random.default_rng(13).normal(size=(35,7))
        np.testing.assert_allclose(r.Ensemble(self.models).energy(z),[m.energy(x) for m,x in zip(self.models,z)],rtol=2e-14)

    def test_03_rows_do_not_couple(self):
        ens=r.Ensemble(self.models);z=np.ones((35,7))*.1;a=ens.rhs(z,np.zeros(35));z[8]*=2;b=ens.rhs(z,np.zeros(35))
        np.testing.assert_array_equal(np.delete(a,8,axis=0),np.delete(b,8,axis=0));self.assertGreater(np.max(np.abs(a[8]-b[8])),0)

    def test_04_power_balance_under_parameter_changes(self):
        ens=r.Ensemble(self.models);z=np.tile([.7,-.3,.02,-.01,0,0,0],(35,1));dz=ens.rhs(z,np.full(35,3e-6));eps=1e-6
        numeric=(ens.energy(z+eps*dz)-ens.energy(z-eps*dz))/(2*eps)
        np.testing.assert_allclose(numeric,dz[:,4]+dz[:,5]-dz[:,6],rtol=1e-6,atol=1e-9)

    def test_05_feedback_off_removes_both_active_terms(self):
        p=next(s['parameters'] for s in self.settings if s['label']=='Feedback off');m=h.Model(p)
        self.assertEqual(m.gain,0);self.assertEqual(m.saturation,0);self.assertEqual(m.rhs(0,[1,.5,.1,0,0,0,0])[4],0)

    def test_06_joint_scenarios_are_reproducible_and_bounded(self):
        self.assertEqual(self.settings,r.settings());joint=[s for s in self.settings if s['kind']=='joint'];self.assertEqual(len(joint),16)
        self.assertTrue(np.all((np.array([s['factors'] for s in joint])>=.75)&(np.array([s['factors'] for s in joint])<=1.25)))

    def test_07_forcing_preserves_mean_and_rms(self):
        for c in r.conditions()[1:8]:
            period=c['period_s'];scale=self.cfg['orbital_force_rms_N']
            mean=quad(lambda t:float(r.force(t,c,self.cfg))/scale,0,period)[0]/period
            power=quad(lambda t:(float(r.force(t,c,self.cfg))/scale)**2,0,period)[0]/period
            self.assertAlmostEqual(mean,0,places=9);self.assertAlmostEqual(power,1,places=9)

    def test_08_linear_passive_solution_and_fourth_order_refinement(self):
        cfg=copy.deepcopy(self.cfg);cfg.update(horizon_s=10.,saved_window_s=5.)
        p=copy.deepcopy(self.settings[0]['parameters']);p['feedback'].update(gain_N_s_m=0.,saturation_N_s_m3=0.)
        s=[dict(parameters=p)];m=h.Model(p);exact=expm(10*m.jacobian(np.zeros(4)))@cfg['starts_scaled'][0]
        with patch.object(r,'settings',return_value=s):
            coarse=r.integrate_ensemble(cfg,.025,False);fine=r.integrate_ensemble(cfg,.0125,False)
        ec=np.max(np.abs(coarse['final'][0,:4]-exact));ef=np.max(np.abs(fine['final'][0,:4]-exact))
        self.assertLess(ef,1e-7);self.assertGreater(ec/ef,14);self.assertLess(ec/ef,18)

    def test_09_full_state_repeat_detects_hidden_memory_drift(self):
        def synthetic(t):return np.column_stack([np.sin(2*np.pi*t/5.7),np.cos(2*np.pi*t/5.7),.001*t,np.zeros_like(t)])
        errors,_=r.repeat_metrics(synthetic,6000,5.7)
        self.assertTrue(all(e>.005 for e in errors.values()))

    def test_10_exact_orbit_repeat_is_detected(self):
        def periodic(t):return np.column_stack([np.sin(2*np.pi*t/5.7),np.cos(2*np.pi*t/5.7),np.zeros_like(t),np.zeros_like(t)])
        errors,_=r.repeat_metrics(periodic,6000,5.7);self.assertLess(max(errors.values()),1e-10)

    def test_11_small_signal_is_not_called_orbit_rhythm(self):
        row=dict(guard_time_s=-1,metrics=dict(status='signal_below_detection'),return_errors_scaled={'1':0.})
        self.assertEqual(r.classify_forced(row,self.cfg),'unsettled')

    def test_12_unsettled_internal_state_is_not_called_converged_cycle(self):
        row=dict(guard_time_s=-1,tail_norm_scaled=1,rest_growth_rate_s_inv=.01,metrics=dict(status='measured',mean_period_s=3),section_cycle_error_scaled=.01,amplitude_drift_fraction=0)
        self.assertEqual(r.classify_autonomous(row,dict(status='attracting_cycle',period_s=3),self.cfg),'unsettled')

    def test_13_guard_is_separate_from_dynamical_instability(self):
        self.assertEqual(r.classify_forced(dict(guard_time_s=5),self.cfg),'integration_guard')


class RobustnessResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=json.loads((r.ROOT/'hug_robustness_results.json').read_text())

    def test_14_all_sources_unchanged(self):
        for path,digest in self.d['source_sha256'].items():self.assertEqual(hashlib.sha256((r.ROOT/path).read_bytes()).hexdigest(),digest)

    def test_15_complete_declared_ensemble(self):
        self.assertEqual(len(self.d['settings']),35);self.assertEqual(len(self.d['cases']),568);self.assertEqual(len(self.d['pairs']),284)
        self.assertEqual([{k:c[k] for k in ('setting','condition','start')} for c in self.d['cases']],r.cases())

    def test_16_every_setting_has_all_eccentricities_and_both_starts(self):
        for i in range(35):
            rows=[c for c in self.d['cases'] if c['setting']==i and c['condition']<8]
            self.assertEqual({(c['condition'],c['start']) for c in rows},{(j,k) for j in range(8) for k in range(2)})

    def test_17_step_refinement_and_energy_checks_pass(self):
        self.assertEqual(r.validate(self.d),self.d['checks']);self.assertTrue(all(self.d['checks'].values()))

    def test_18_independent_controls_cover_all_unforced_settings_and_baseline_orbits(self):
        controls=[self.d['cases'][c['case_index']] for c in self.d['independent_controls']]
        self.assertEqual(len(controls),46);self.assertEqual({c['setting'] for c in controls if c['condition']==0},set(range(35)))
        self.assertEqual({c['condition'] for c in controls if c['setting']==0},set(range(12)))

    def test_19_autonomous_cycle_claims_have_local_stability_evidence(self):
        for row in self.d['cases']:
            if row['classification']!='self_sustained':continue
            c=self.d['cycles'][row['setting_id']];self.assertEqual(c['status'],'attracting_cycle')
            self.assertLess(c['shooting_error_scaled'],1e-7);self.assertLess(c['largest_transverse_multiplier'],1)
            self.assertLess(row['section_cycle_error_scaled'],self.d['protocol']['gates']['section_error_scaled'])

    def test_20_orbit_repeat_claims_use_all_state_variables(self):
        for c in self.d['cases']:
            if c['condition']==0:continue
            expected=next((int(n) for n,e in c['return_errors_scaled'].items() if e<1e-4),None)
            self.assertEqual(c['repeat_orbits'],expected)
            if c['classification']=='orbit_repeat':self.assertIsNotNone(expected)

    def test_21_locked_pairs_agree_between_starts(self):
        for p in self.d['pairs']:
            if p['classification']=='orbit_locked':self.assertLess(p['between_start_state_error_scaled'],1e-4)

    def test_22_baseline_matches_prior_unforced_cycle(self):
        prior=json.loads((r.ROOT/'hug_rhythm_results.json').read_text())
        self.assertAlmostEqual(self.d['cycles']['baseline']['period_s'],prior['autonomous_cycle']['period_s'],places=7)

    def test_23_parameters_are_scenarios_without_measurement_claims(self):
        self.assertEqual(self.d['origin'],'synthetic_parameter_sensitivity');self.assertEqual(self.d['physical_measurements'],0);self.assertEqual(self.d['additional_sims_runs'],0)
        self.assertEqual(self.d['settings'],r.settings());self.assertEqual(self.d['protocol'],r.protocol())

    def test_24_saved_outcomes_retain_nonrepeats_and_unsettled_states(self):
        allowed={'self_sustained','rest','unsettled','mixed_or_unsettled','orbit_locked','no_short_repeat','repeat_start_dependent','integration_guard'}
        self.assertTrue(all(p['classification'] in allowed for p in self.d['pairs']))
        self.assertEqual(sum(self.d['counts'].values()),284)
        audit=self.d['initial_resolution_audit'];self.assertFalse(audit['checks']['energy_balance']);self.assertFalse(audit['checks']['independent_solver'])
        self.assertEqual(audit['protocol']['gates'],self.d['protocol']['gates'])
        self.assertLess(self.d['protocol']['main_step_s'],audit['protocol']['main_step_s'])


if __name__=='__main__':unittest.main()
