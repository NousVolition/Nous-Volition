import copy
import json
import math
from pathlib import Path
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
import numpy as np
from scipy.linalg import expm
import hug_calibration as h

ROOT=Path(__file__).resolve().parent


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session=json.loads((ROOT/'calibration/synthetic_demo.json').read_text())
        cls.truth=json.loads((ROOT/'calibration/synthetic_truth.json').read_text())
        cls.report=h.analyze(cls.session)

    def trial(self,kind,role='validation'):
        return copy.deepcopy(next(t for t in self.session['trials'] if t['kind']==kind and t['role']==role))

    def only(self,trial):return dict(self.session,trials=[trial])

    def test_01_blank_has_no_measurements_or_pass(self):
        blank=json.loads((ROOT/'calibration/blank_session.json').read_text())
        self.assertTrue(all(not t['samples'] for t in blank['trials']))
        report=h.analyze(blank);self.assertEqual(report['status'],'awaiting_measurements');self.assertFalse(report['physical_calibration_established']);self.assertEqual(report['fits'],{})

    def test_02_pipeline_has_all_six_held_out_types(self):
        self.assertEqual(self.report['status'],'synthetic_pipeline_passed')
        self.assertEqual({t['kind'] for t in self.report['validation']},set(h.KINDS))
        self.assertTrue(all(t['status']=='passed' for t in self.report['validation']))

    def test_03_synthetic_never_establishes_physical_calibration(self):
        self.assertEqual(self.report['data_origin'],'synthetic');self.assertFalse(self.report['physical_calibration_established'])

    def test_04_clay_recovered_from_independent_integration(self):
        for key,value in self.truth['material'].items():self.assertAlmostEqual(self.report['fits']['creep']['parameters'][key]/value,1,places=7)

    def test_05_mechanics_recovered_despite_initial_phase_error(self):
        for key,value in self.truth['mechanics'].items():self.assertAlmostEqual(self.report['fits']['passive']['parameters'][key]/value,1,places=6)

    def test_06_feedback_force_parameters_recovered(self):
        for key,value in self.truth['feedback'].items():self.assertAlmostEqual(self.report['fits']['feedback']['parameters'][key],value,delta=max(1e-12,abs(value)*1e-10))

    def test_07_material_and_feedback_have_local_rank(self):
        self.assertEqual(self.report['fits']['creep']['quality']['rank'],4)
        self.assertTrue(all(r['quality']['identifiable'] for r in self.report['fits'].values()))

    def test_08_fit_and_validation_ids_disjoint(self):
        fit={i for r in self.report['fits'].values() for i in r['fit_trial_ids']}
        held={t['id'] for t in self.session['trials'] if t['role']=='validation'}
        self.assertFalse(fit&held)

    def test_09_held_out_corruption_does_not_change_fit(self):
        session=copy.deepcopy(self.session)
        for t in session['trials']:
            if t['role']=='validation' and t['kind']=='creep':
                for r in t['samples']:r['displacement_mm']+=.01
        report=h.analyze(session)
        self.assertEqual(report['fits'],self.report['fits']);self.assertEqual(next(r['status'] for r in report['validation'] if r['kind']=='creep'),'failed')

    def test_10_missing_threshold_cannot_pass(self):
        session=dict(self.session,acceptance={});report=h.analyze(session)
        self.assertTrue(all(r['status']=='tolerance_not_set' for r in report['validation']));self.assertNotEqual(report['status'],'synthetic_pipeline_passed')

    def test_11_si_geometry_conversion(self):
        np.testing.assert_allclose(h.geometry(self.session,'creep'),[1e-4,.01]);np.testing.assert_allclose(h.geometry(self.session,'motion'),[.1,1e-7])

    def test_12_absolute_times_are_relative_in_predictions(self):
        trial=self.trial('passive');a=h.passive_prediction(self.session,trial,self.truth['material'],.2,.7)
        for row in trial['samples']:row['time_s']+=100
        b=h.passive_prediction(self.session,trial,self.truth['material'],.2,.7)
        np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-14)

    def test_13_nonmonotone_time_rejected(self):
        t=self.trial('creep');t['samples'][2]['time_s']=t['samples'][1]['time_s']
        with self.assertRaisesRegex(ValueError,'strictly increasing'):h.validate_session(self.only(t))

    def test_14_nonfinite_observation_rejected(self):
        t=self.trial('feedback');t['samples'][3]['force_N']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite'):h.validate_session(self.only(t))

    def test_15_unknown_clay_memory_rejected(self):
        t=self.trial('passive');t['initial']['known']=False
        with self.assertRaisesRegex(ValueError,'memory'):h.validate_session(self.only(t))

    def test_16_duplicate_ids_rejected(self):
        t=self.trial('creep')
        with self.assertRaisesRegex(ValueError,'unique'):h.validate_session(dict(self.session,trials=[t,t]))

    def test_17_missing_orbit_force_rejected(self):
        t=self.trial('eccentric');t['samples'][3]['orbit_force_N']=None
        with self.assertRaisesRegex(ValueError,'orbit_force_N'):h.validate_session(self.only(t))

    def test_18_passive_powered_force_rejected(self):
        t=self.trial('passive');t['samples'][1]['active_force_N']=.01
        with self.assertRaisesRegex(ValueError,'off'):h.validate_session(self.only(t))

    def test_19_autonomous_continued_push_rejected(self):
        t=self.trial('autonomous');t['samples'][1]['force_N']=.001
        with self.assertRaisesRegex(ValueError,'split off'):h.validate_session(self.only(t))

    def test_20_active_motion_cannot_be_used_for_fit(self):
        t=self.trial('circular');t['role']='fit'
        with self.assertRaisesRegex(ValueError,'reserve'):h.validate_session(self.only(t))

    def test_21_equilibrium_cannot_identify_feedback(self):
        t=self.trial('feedback','fit')
        for r in t['samples']:r.update(displacement_mm=0.,velocity_mm_s=0.,active_force_N=0.)
        with self.assertRaisesRegex(ValueError,'amplitudes'):h.fit_feedback([t])

    def test_22_delay_alignment_uses_past_motion(self):
        t=self.trial('feedback','fit');t['controller_delay_s']=.4
        x,_,mask=h.feedback_arrays(t);times,q,_,_=h.columns(t);v=np.array([r['velocity_mm_s'] for r in t['samples']])*1e-3
        np.testing.assert_allclose(x[:,0],np.interp(times[mask]-.4,times,v));np.testing.assert_allclose(x[:,1],-np.interp(times[mask]-.4,times,q)**2*x[:,0])

    def test_23_delayed_first_segment_matches_exact_forced_linear_solution(self):
        t=self.trial('autonomous');t['samples']=t['samples'][:26];t['initial']['velocity_mm_s']=.1;t['controller_delay_s']=5.
        f=dict(self.truth['feedback'],controller_delay_s=5.);out=h.active_prediction(self.session,t,self.truth['material'],self.truth['mechanics'],f)
        m=h.mechanical_matrix(self.truth['material'],.2,.7,.1,1e-7);a=np.zeros((5,5));a[:4,:4]=m
        q0=t['samples'][0]['displacement_mm']*1e-3;v0=.0001;a[1,4]=(.03-3e6*q0*q0)*v0/.2
        exact=(expm(a*5.)@np.array([q0,v0,0,0,1]))[:4];np.testing.assert_allclose(out[-1],exact,rtol=1e-7,atol=1e-11)

    def test_24_unknown_delay_history_and_changed_delay_rejected(self):
        t=self.trial('autonomous');t['samples']=t['samples'][:26];t['controller_delay_s']=.2;t['initial']['constant_delay_history_known']=False;f=dict(self.truth['feedback'],controller_delay_s=.2)
        with self.assertRaisesRegex(ValueError,'history'):h.active_prediction(self.session,t,self.truth['material'],self.truth['mechanics'],f)
        f['controller_delay_s']=.3
        with self.assertRaisesRegex(ValueError,'differs'):h.active_prediction(self.session,t,self.truth['material'],self.truth['mechanics'],f)

    def test_25_measured_active_force_is_not_forward_prediction_input(self):
        t=self.trial('autonomous');t['samples']=t['samples'][:51]
        a=h.active_prediction(self.session,t,self.truth['material'],self.truth['mechanics'],self.truth['feedback'])
        for r in t['samples']:r['active_force_N']=1000
        b=h.active_prediction(self.session,t,self.truth['material'],self.truth['mechanics'],self.truth['feedback']);np.testing.assert_array_equal(a,b)

    def test_26_no_load_cannot_identify_four_clay_parameters(self):
        t=self.trial('creep','fit')
        for r in t['samples']:r.update(force_N=0.,displacement_mm=0.)
        with self.assertRaisesRegex(ValueError,'identified'):h.fit_material(self.session,[t])

    def test_27_wrong_mechanics_fails_held_out_prediction(self):
        t=self.trial('passive');observed=h.columns(t)[1]
        wrong=h.passive_prediction(self.session,t,self.truth['material'],.4,.7)[:,0]
        self.assertGreater(float(np.sqrt(np.mean((wrong-observed)**2)))*1000,self.session['acceptance']['displacement_rmse_mm'])

    def test_28_entry_page_has_blank_template_and_complete_fields(self):
        class Page(HTMLParser):
            def __init__(self):super().__init__();self.ids=[]
            def handle_starttag(self,tag,attrs):
                a=dict(attrs)
                if 'id' in a:self.ids.append(a['id'])
        text=(ROOT/'calibration/measurements.html').read_text(encoding='utf-8');p=Page();p.feed(text)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        for key in ('rows','trials','export','check','geometry.mode_volume_mm3','acceptance.force_rmse_N'):self.assertIn(key,p.ids)
        start=text.index('<script id="blank" type="application/json">')+len('<script id="blank" type="application/json">')
        embedded=json.loads(text[start:text.index('</script>',start)])
        self.assertEqual(embedded,json.loads((ROOT/'calibration/blank_session.json').read_text(encoding='utf-8')))

    def test_29_measurement_entry_conversion_and_checks(self):
        node=shutil.which('node')
        if not node:
            bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
            if bundled.is_file():node=str(bundled)
        if not node:self.skipTest('Node unavailable; run calibration/test_entry.cjs separately')
        run=subprocess.run([node,str(ROOT/'calibration/test_entry.cjs')],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)


if __name__=='__main__':unittest.main()
