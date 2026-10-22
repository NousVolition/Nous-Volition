import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.linalg import expm
import guard_sync as s

class InterventionChecks(unittest.TestCase):
    def setUp(self):self.cfg=s.protocol();self.p=s.guard_protocol()
    def test_schedule_and_case_matrix(self):
        self.assertEqual(self.cfg['boundaries_s'],[0,171,741,4161]);self.assertEqual(len(s.cases(self.cfg)),84)
        for arm,expected in [('restore',[1,2,1]),('sham',[1,1,1]),('hold_high',[1,2,2])]:self.assertEqual([s.factor(arm,i,self.cfg) for i in range(3)],expected)
    def test_switch_energy_and_continuous_state(self):
        m=s.Ensemble(self.p,[dict(model='directional',condition=1,start=0)]);z=m.start();before=m.energy(z);old=m.k;m.k*=2
        np.testing.assert_allclose(m.energy(z)-before,s.spring_work(z[:,0],old,m.k,m),atol=1e-15)
        self.assertLess(float(s.spring_work(np.array([1.]),m.k,old,m)[0]),0)
    def test_guard_drift_prevents_false_relock(self):
        z=np.zeros((40,2,8));z[:,:,6]=np.arange(40)[:,None]*.001
        errors=s.legacy.repeat_windows(z,self.cfg)[-1];self.assertEqual(s.legacy.classify(errors,0,.1,self.cfg),'no_short_repeat')
        mechanical=s.legacy.repeat_windows(z[:,:,:4],self.cfg)[-1];self.assertEqual(s.legacy.classify(mechanical,0,.1,self.cfg),'synchronized')
    def test_confirmation_window_length(self):
        errors=s.legacy.repeat_windows(np.zeros((40,2,8)),self.cfg)
        self.assertTrue(all(e is None for e in errors[:23]));self.assertIsNotNone(errors[23])
    def test_four_orbit_repeat(self):
        z=np.zeros((60,2,8));z[:,:,0]=np.cos(np.arange(60)*np.pi/2)[:,None];z[:,:,1]=np.sin(np.arange(60)*np.pi/2)[:,None]
        error=s.legacy.repeat_windows(z,self.cfg)[-1];self.assertLess(error[3],1e-12);self.assertGreater(min(error[:3]),1)
    def test_history_and_quiet_gates(self):
        self.assertEqual(s.legacy.classify([0]*4,.01,.1,self.cfg),'no_short_repeat');self.assertEqual(s.legacy.classify([0]*4,0,0,self.cfg),'quiet')
    def test_temporary_lock_not_sustained(self):
        self.assertEqual(s.legacy.stable_first_time([0,1,2,3],['assessing','synchronized','no_short_repeat','synchronized'],'synchronized'),3)
        self.assertIsNone(s.legacy.stable_first_time([0,1],['synchronized','no_short_repeat'],'synchronized'))
    def test_force_preserves_absolute_clock(self):
        e=s.Ensemble(self.p,[dict(model='directional',condition=c,start=0) for c in range(1,8)])
        for t in [171,741]:np.testing.assert_allclose(e.force(6000+t),e.force(6000+t+5.7),atol=1e-15)
    def test_piecewise_passive_exact_solution(self):
        cfg=copy.deepcopy(self.cfg);cfg['boundaries_s']=[0,1,2,3];p=copy.deepcopy(self.p);p['feedback']['gain_N_s_m']=p['feedback']['saturation_N_s_m3']=0;p['orbital_force_rms_N']=0
        rows=[dict(model='old',arm=arm,condition=1,history=0) for arm in cfg['arms']];initial=np.tile([.4,-.2,.03,-.01,0,0,0,0],(3,1))
        with tempfile.TemporaryDirectory() as tmp:
            d=s.integrate(cfg,p,rows,initial,Path(tmp),'main',False);out=np.load(Path(tmp)/'state.npy')[-1]
        for i,row in enumerate(rows):
            y=initial[i,:4];m=s.Ensemble(p,s.base_rows([row]));k=m.k
            for stage in range(3):
                m.k=k*s.factor(row['arm'],stage,cfg);J=np.column_stack([m.rhs(0,np.r_[np.eye(4)[j],np.zeros(4)][None],np.zeros(1))[0,:4] for j in range(4)]);y=expm(J)@y
            np.testing.assert_allclose(out[i,:4],y,atol=2e-8)
        self.assertTrue(all(e['before']==e['after'] for e in d['events']));self.assertLess(max(d['energy_error']),1e-7)

if __name__=='__main__':unittest.main()
