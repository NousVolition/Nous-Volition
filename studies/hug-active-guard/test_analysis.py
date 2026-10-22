import unittest
import numpy as np
from model import Ensemble,protocol
from analyze import metrics,jacobian

class DiagnosticChecks(unittest.TestCase):
    def test_jacobian_all_models(self):
        p=protocol();y=np.array([.7,-1.2,.02,-.03,-.2,.3,.65,.35]);eps=1e-6
        for name in p['models']:
            r=dict(model=name,condition=0,start=0);m=Ensemble(p,[r])
            numerical=np.column_stack([(m.rhs(0,(y+eps*np.eye(8)[j])[None],np.zeros(1))[0]-m.rhs(0,(y-eps*np.eye(8)[j])[None],np.zeros(1))[0])/(2*eps) for j in range(8)])
            np.testing.assert_allclose(jacobian(p,r,y),numerical,atol=2e-8,rtol=2e-8)
    def test_hidden_guard_drift_is_not_a_full_repeat(self):
        p=protocol();P=p['orbit_period_s'];t=np.arange(4001)*P/100
        z=np.zeros((len(t),8));z[:,0]=np.sin(2*np.pi*t/P);z[:,1]=2*np.pi/P*np.cos(2*np.pi*t/P)
        z[:,4]=-.3;z[:,5]=.3;z[:,6]=.5+.0002*t;z[:,7]=.5
        new=metrics(p,dict(model='directional',condition=1,start=0),t,z)
        old=metrics(p,dict(model='old',condition=1,start=0),t,z)
        self.assertGreater(min(new['orbit_repeat_errors']),p['gates']['repeat_error'])
        self.assertLess(min(old['orbit_repeat_errors']),1e-9)
    def test_quiet_motion_has_no_measured_period(self):
        p=protocol();t=np.arange(501)*.05;z=np.zeros((len(t),8));z[:,6:]=.5
        d=metrics(p,dict(model='directional',condition=0,start=0),t,z)
        self.assertIsNone(d['mean_period_s']);self.assertEqual(d['half_amplitude_mm'],0)
    def test_known_period_recovered(self):
        p=protocol();P=2.85;t=np.arange(6001)*.05;z=np.zeros((len(t),8));z[:,0]=np.sin(2*np.pi*t/P);z[:,1]=2*np.pi/P*np.cos(2*np.pi*t/P)
        d=metrics(p,dict(model='old',condition=0,start=0),t,z)
        self.assertAlmostEqual(d['mean_period_s'],P,places=8)

if __name__=='__main__':unittest.main()
