import copy,hashlib,unittest
from pathlib import Path
import numpy as np
from model import Hug,protocol,metric
from baseline import Hug as FixedHug

class FeedbackChecks(unittest.TestCase):
    def setUp(self):self.p=protocol();self.m=Hug(self.p,32);self.rng=np.random.default_rng(220)
    def test_baseline_bytes_are_pinned(self):
        self.assertEqual(hashlib.sha256(Path(__file__).with_name('baseline.py').read_bytes()).hexdigest(),self.p['baseline_model_sha256'])
    def test_metric_matches_full_gradient_transform(self):
        for gamma in [-2,-.3,0,.4,2]:
            F=np.array([[1,gamma],[0,1]]);t=np.array([-np.sin(self.m.theta),np.cos(self.m.theta)])
            expected=np.sum((np.linalg.inv(F).T@t)**2,axis=0)
            np.testing.assert_allclose(metric(self.m.theta,gamma),expected,atol=2e-15)
            self.assertAlmostEqual(np.linalg.det(F),1)
    def test_frozen_control_recovers_old_rhs(self):
        sel=[dict(scenario='frozen',condition=c,history=0) for c in range(3)]
        old=FixedHug(self.p,32,sel);new=Hug(self.p,32,sel);z=self.rng.normal(scale=.1,size=old.initial().shape)
        np.testing.assert_allclose(new.rhs(123,z),old.rhs(123,z),rtol=1e-13,atol=1e-13)
    def test_zero_deformation_recovers_old_operators(self):
        S=self.rng.normal(size=(self.m.nr,32));g=np.zeros(self.m.nr)
        np.testing.assert_array_equal(self.m.deformed_force(S,g),self.m.memory_force(S))
        expected=self.m.f['diffusivity_m2_s']*(np.roll(S,-1,1)-2*S+np.roll(S,1,1))/self.m.ds**2
        np.testing.assert_allclose(self.m.diffusion(S,g),expected,atol=1e-14)
    def test_diffusion_redistributes_and_dissipates_variation(self):
        S=self.rng.normal(size=(self.m.nr,32));g=self.rng.uniform(-2,2,self.m.nr);d=self.m.diffusion(S,g)
        self.assertLess(np.abs(d.sum(axis=1)).max(),1e-13)
        self.assertTrue(np.all(np.sum(S*d,axis=1)<0))
        np.testing.assert_array_equal(self.m.diffusion(np.ones_like(S),g),0)
    def test_motion_changes_field_rate_without_changing_mean(self):
        z=self.m.initial();z[:,4:7]=[1,1,1];z[:,7:39]=np.cos(self.m.theta)+.2*np.sin(2*self.m.theta)
        z[:,0]=20
        a=self.m.rhs(500,z,True,np.zeros(3));z[:,0]=0;b=self.m.rhs(500,z,True,np.zeros(3))
        self.assertGreater(np.max(np.abs(a[:6,7:39]-b[:6,7:39])),1e-5)
        np.testing.assert_allclose(a[:,7:39].mean(axis=1),b[:,7:39].mean(axis=1),atol=1e-14)
        np.testing.assert_array_equal(a[:,4:7],0)
    def test_manufactured_diffusion_second_order(self):
        errors=[];gamma=.35;D=self.p['field']['diffusivity_m2_s'];R=self.p['field']['radius_m']
        for n in [32,64,128]:
            m=Hug(self.p,n,[dict(scenario='feedback',condition=0,history=0)]);th=m.theta
            S=np.sin(3*th)+.2*np.cos(2*th);Sp=3*np.cos(3*th)-.4*np.sin(2*th);Spp=-9*np.sin(3*th)-.8*np.cos(2*th)
            g=metric(th,gamma);gp=2*gamma*np.cos(2*th)+gamma**2*np.sin(2*th)
            exact=D/R**2*(gp*Sp+g*Spp);actual=m.diffusion(S[None,:],np.array([gamma]))[0]
            errors.append(np.sqrt(np.mean((actual-exact)**2)))
        self.assertTrue(all(3.7<a/b<4.3 for a,b in zip(errors,errors[1:])),errors)
    def test_material_advection_chain_rule(self):
        # The material derivative includes u.grad(S); adding it again double-counts transport.
        omega=.7;t=.4;pts=np.array([[.03,.02],[-.04,.01],[.01,-.035]])
        def field(x,t):
            gamma=.2*np.sin(omega*t);X=x[:,0]-gamma*x[:,1];Y=x[:,1]
            return np.sin(2*np.arctan2(Y,X))
        h=1e-6;dt=(field(pts,t+h)-field(pts,t-h))/(2*h)
        shift=np.array([h,0]);dx=(field(pts+shift,t)-field(pts-shift,t))/(2*h)
        u=.2*omega*np.cos(omega*t)*pts[:,1]
        np.testing.assert_allclose(dt+u*dx,0,atol=2e-9)
    def test_field_bound_with_moving_diffusion(self):
        z=self.m.initial();z[:,0]=self.rng.uniform(-2,2,self.m.nr)*self.m.L/self.m.Q
        B=self.m.bound()
        for sign in [-1,1]:
            z[:,7:39]=self.rng.uniform(-B,B,(self.m.nr,32));z[:,7+9]=sign*B;z[:,4:7]=sign*1e6
            out=self.m.rhs(500,z,True,np.zeros(3))
            self.assertLessEqual((sign*out[:,7+9]).max(),1e-12)
    def test_current_gradient_remains_sign_even(self):
        S=self.rng.normal(size=(self.m.nr,32));gamma=self.rng.normal(size=self.m.nr)
        np.testing.assert_array_equal(self.m.deformed_force(S,gamma),self.m.deformed_force(-S,gamma))
    def test_no_reset_scenarios(self):
        self.assertTrue(all(not x['erase'] for x in self.p['scenarios']))
        self.assertTrue(all(x['transmission']==.55 for x in self.p['scenarios']))
    def test_advection_does_not_require_diffusion(self):
        # With D=0, no sources/exchange/relaxation, S remains on its material label.
        p=copy.deepcopy(self.p);p['events']=[]
        for key in ['diffusivity_m2_s','exchange_rate_per_s','expression_relaxation_per_s']:p['field'][key]=0
        m=Hug(p,32);z=m.initial();z[:,7:39]=self.rng.normal(size=(m.nr,32));z[:,0]=10;z[:,1]=20
        np.testing.assert_array_equal(m.rhs(500,z,False,np.zeros(3))[:,7:39],0)

if __name__=='__main__':unittest.main()

