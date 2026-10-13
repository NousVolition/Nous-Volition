import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import numpy as np
from scipy.linalg import expm
import hug_sync as s
import hug_robustness as r
from hug_rhythm import Model


class LiveSynchronizationMath(unittest.TestCase):
    def setUp(self):self.cfg=s.protocol()

    def test_01_declared_switch_schedule(self):
        np.testing.assert_allclose(s.boundaries(self.cfg),[0,171,741,4161],atol=1e-10)

    def test_02_control_schedules(self):
        self.assertEqual([s.factor('restore',i,self.cfg) for i in range(3)],[1,2,1])
        self.assertEqual([s.factor('sham',i,self.cfg) for i in range(3)],[1,1,1])
        self.assertEqual([s.factor('hold_high',i,self.cfg) for i in range(3)],[1,2,2])

    def test_03_switch_work_matches_physical_spring_energy(self):
        p,_,_=s.initial_states(self.cfg);m=Model(p);x=np.array([-.7,0,1.2])
        w=s.spring_work_scaled(x,.7,1.4,m)*m.energy_scale
        np.testing.assert_allclose(w,.5*1.4*(m.qscale*x)**2-.5*.7*(m.qscale*x)**2,rtol=1e-14)

    def test_04_lowering_stiffness_extracts_energy(self):
        p,_,_=s.initial_states(self.cfg);m=Model(p)
        self.assertLess(float(s.spring_work_scaled(1,1.4,.7,m)),0)
        self.assertEqual(float(s.spring_work_scaled(0,.7,1.4,m)),0)

    def test_05_hidden_memory_drift_rejects_displacement_repeat(self):
        z=np.zeros((60,2,4));z[:,:,2]=np.arange(60)[:,None]*.01
        errors=s.repeat_windows(z,self.cfg)[-1]
        self.assertEqual(s.classify(errors,0,.1,self.cfg),'no_short_repeat')

    def test_06_four_orbit_repeat_is_detected(self):
        phase=np.arange(60)*np.pi/2;z=np.zeros((60,2,4));z[:,:,0]=np.cos(phase)[:,None];z[:,:,1]=np.sin(phase)[:,None]
        errors=s.repeat_windows(z,self.cfg)[-1]
        self.assertGreater(min(errors[:3]),1);self.assertLess(errors[3],1e-12)
        self.assertEqual(s.classify(errors,0,.1,self.cfg),'synchronized')

    def test_07_short_windows_are_not_assessed(self):
        a=s.repeat_windows(np.zeros((30,2,4)),self.cfg)
        self.assertTrue(all(x is None for x in a[:23]));self.assertIsNotNone(a[23])

    def test_08_quiet_motion_is_not_called_rhythm(self):
        self.assertEqual(s.classify([0]*4,0,0,self.cfg),'quiet')

    def test_09_histories_must_agree(self):
        self.assertEqual(s.classify([0]*4,.001,.2,self.cfg),'no_short_repeat')

    def test_10_temporary_repeat_is_not_sustained_recovery(self):
        self.assertEqual(s.stable_first_time([0,1,2,3,4],['assessing','synchronized','synchronized','no_short_repeat','synchronized'],'synchronized'),4)
        self.assertIsNone(s.stable_first_time([0,1],['synchronized','no_short_repeat'],'synchronized'))

    def test_11_initial_states_are_continued_at_their_recorded_phase(self):
        _,cc,z=s.initial_states(self.cfg);d=json.loads((s.ROOT/self.cfg['initial_results']).read_text())
        for case,state in zip(s.cases(self.cfg),z):
            row=next(x for x in d['cases'] if x['setting']==0 and x['condition']==case['condition']+1 and x['start']==case['history'])
            np.testing.assert_array_equal(state,row['stroboscopic_last_state_scaled'])
        self.assertEqual(len(cc),7)

    def test_12_wrong_initial_time_is_rejected(self):
        cfg=copy.deepcopy(self.cfg);cfg['absolute_start_s']=0
        with self.assertRaises(ValueError):s.initial_states(cfg)

    def test_13_force_clock_is_unchanged_by_stiffness(self):
        _,cc,_=s.initial_states(self.cfg)
        for c in cc:
            for t in s.boundaries(self.cfg)[1:3]:
                a=r.force(self.cfg['absolute_start_s']+t,c,self.cfg)
                b=r.force(self.cfg['absolute_start_s']+t+self.cfg['orbit_period_s'],c,self.cfg)
                self.assertAlmostEqual(float(a),float(b),places=14)

    def test_14_piecewise_linear_exact_propagator_and_rk4_order(self):
        cfg=copy.deepcopy(self.cfg);cfg.update(orbit_period_s=.5,baseline_orbits=2,raised_stiffness_orbits=2,recovery_orbits=2,sample_interval_s=.05)
        p,cc,z=s.initial_states(self.cfg);p=copy.deepcopy(p);p['feedback'].update(gain_N_s_m=0.,saturation_N_s_m3=0.)
        base=Model(p);high=copy.deepcopy(base);high.k*=2
        z=np.tile([.3,-.2,.01,-.03],(42,1));errs=[]
        with patch.object(s,'initial_states',return_value=(p,cc,z)),patch.object(r,'force',side_effect=lambda t,c,cf:np.zeros_like(t)):
            for dt in [.05,.025]:
                out=s.integrate(cfg,dt,False);exact=[]
                for case,start in zip(s.cases(cfg),z):
                    for stage in range(3):start=expm((base if s.factor(case['arm'],stage,cfg)==1 else high).jacobian(np.zeros(4)))@start
                    exact.append(start)
                errs.append(np.max(np.abs(out['state'][-1]-exact)))
        self.assertLess(errs[1],2e-6);self.assertGreater(errs[0]/errs[1],14);self.assertLess(errs[0]/errs[1],18)


class LiveSynchronizationResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=json.loads((s.ROOT/'hug_sync_results.json').read_text())

    def test_15_complete_conditions_controls_histories(self):
        self.assertEqual(self.d['cases'],s.cases(s.protocol()));self.assertEqual(len(self.d['cases']),42)
        self.assertEqual(len(self.d['summary']),21);self.assertEqual(len(self.d['independent_controls']),21)

    def test_16_all_four_states_are_continuous_at_both_changes(self):
        self.assertEqual(len(self.d['switch_events']),2)
        for event in self.d['switch_events']:self.assertEqual(event['before_state_scaled'],event['after_state_scaled'])

    def test_17_energy_and_independent_accuracy(self):
        self.assertTrue(self.d['checks']['energy_balance']);self.assertTrue(self.d['checks']['independent_solver'])

    def test_18_refinement_and_classification_accuracy(self):
        self.assertTrue(all(self.d['checks'].values()),self.d['checks']);self.assertEqual(self.d['numerical_status'],'passed')

    def test_19_results_and_sources_are_current(self):
        self.assertEqual(self.d['protocol'],s.protocol())
        for path,digest in self.d['source_sha256'].items():self.assertEqual(hashlib.sha256((s.ROOT/path).read_bytes()).hexdigest(),digest)

    def test_20_intervention_reports_actual_outcomes(self):
        for row in self.d['summary']:
            self.assertEqual(row['stages'][0]['end_status'],'synchronized')
            if row['arm']=='restore':
                self.assertIsNotNone(row['loss_confirmed_s']);self.assertIsNotNone(row['relock_confirmed_s']);self.assertGreater(row['relock_confirmed_s'],741)
            if row['arm']=='sham':self.assertTrue(all(x['end_status']=='synchronized' for x in row['stages']))
            if row['arm']=='hold_high':self.assertIsNone(row['relock_confirmed_s']);self.assertEqual(row['stages'][2]['end_status'],'no_short_repeat')

    def test_21_recovery_confirmation_never_crosses_a_switch(self):
        cfg=self.d['protocol'];minimum=(cfg['repeat_comparisons']+cfg['maximum_repeat_orbits']-1)*cfg['orbit_period_s']
        for row in self.d['summary']:
            if row['relock_confirmed_s'] is not None:self.assertGreaterEqual(row['relock_confirmed_s']-741,minimum-1e-8)

    def test_22_no_measurements_or_new_sims_claim(self):
        self.assertEqual(self.d['physical_measurements'],0);self.assertEqual(self.d['additional_sims_runs'],0)


if __name__=='__main__':unittest.main()
