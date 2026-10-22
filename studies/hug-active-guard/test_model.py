import copy,unittest
import numpy as np
from scipy.integrate import solve_ivp,quad
from scipy.linalg import expm
from model import Ensemble,protocol,cases,physical_rhs,physical_scale
import hug_rhythm

class EquationChecks(unittest.TestCase):
    def setUp(self):self.p=protocol()
    def model(self,name='directional',condition=0):return Ensemble(self.p,[dict(model=name,condition=condition,start=0)])
    def test_old_matches_published_rhs(self):
        e=self.model('old');h=hug_rhythm.Model({k:self.p[k] for k in ['material','mechanics','feedback']})
        for state in [[.4,-.8,.1,-.1],[-1.2,2.2,-.3,.2],[0,0,0,0]]:
            z=np.r_[state,np.zeros(4)][None];f=3e-6
            np.testing.assert_allclose(e.rhs(0,z,[f])[0,:4],h.rhs(0,np.array(state),f),atol=1e-14,rtol=1e-14)
    def test_independent_physical_equations(self):
        scale=physical_scale(self.p)
        for name in self.p['models']:
            e=self.model(name,3);z=np.array([[.8,-1.7,.04,-.02,-.3,.4,.7,.2]])
            a=e.rhs(3.2,z)[0];b=np.array(physical_rhs(self.p,e.rows[0])(3.2,z[0]*scale))/scale
            np.testing.assert_allclose(a,b,atol=2e-14,rtol=2e-14)
    def test_energy_identity(self):
        for name in self.p['models']:
            e=self.model(name,2);z=np.array([[.8,-1.7,.04,-.02,-.3,.4,.7,.2,0,0,0,0]])
            dz=e.rhs(2.1,z);eps=1e-6
            derivative=(e.energy(z+eps*dz)-e.energy(z-eps*dz))/(2*eps)
            np.testing.assert_allclose(derivative,dz[:,8]+dz[:,9]-dz[:,10]-dz[:,11],atol=2e-9,rtol=1e-7)
            self.assertGreaterEqual(dz[0,11],0)
    def test_passive_energy_nonpositive(self):
        e=self.model('feedback_off')
        for z in np.random.default_rng(101).normal(size=(20,8)):
            z[6:]=[.2,.8];d=e.rhs(0,np.r_[z,np.zeros(4)][None])[0]
            self.assertLessEqual(d[8]+d[9]-d[10]-d[11],0)
    def test_guard_interval_inward(self):
        e=self.model()
        for boundary in [0,1]:
            z=e.start();z[:,6:]=boundary;d=e.rhs(0,z)[0,6:]
            self.assertTrue(np.all(d>=0) if boundary==0 else np.all(d<=0))
    def test_direction_relabeling(self):
        p=copy.deepcopy(self.p);p['guard']['baselines']=p['guard']['baselines'][::-1]
        a=self.model('A_receives_more');b=Ensemble(p,[dict(model='B_receives_more',condition=0,start=0)])
        z=np.array([[.2,1.1,.01,-.02,-.3,.4,.7,.2]]);perm=[0,1,2,3,5,4,7,6]
        np.testing.assert_allclose(a.rhs(0,z)[:,perm],b.rhs(0,z[:,perm]),atol=1e-14)
    def test_shared_guards_equal_derivatives(self):
        e=self.model('shared');z=e.start();z[:,1]=2.3;d=e.rhs(0,z)
        self.assertEqual(d[0,6],d[0,7])
    def test_frozen_guards_do_not_move(self):
        e=self.model('frozen');self.assertTrue(np.all(e.rhs(0,e.start())[:,6:]==0))
    def test_shared_directional_closed_subsystem(self):
        # With equal weights, mechanics, B-A and guard sum close exactly.
        a=self.model('directional');b=self.model('shared')
        for z in np.random.default_rng(907).normal(size=(30,8)):
            z[6:]=[.2,.7];other=z.copy();other[4:6]+=.4;other[6:]=.45
            da=a.rhs(0,z[None])[0];db=b.rhs(0,other[None])[0]
            np.testing.assert_allclose(da[:4],db[:4],atol=1e-14)
            self.assertAlmostEqual(da[5]-da[4],db[5]-db[4],places=13)
            self.assertAlmostEqual(da[6]+da[7],db[6]+db[7],places=13)
    def test_guard_and_strain_feedback_are_live(self):
        e=self.model();z=e.start();z[:,1]=2.;a=e.rhs(0,z)
        zz=z.copy();zz[:,6]+=.1;b=e.rhs(0,zz);self.assertNotEqual(a[0,1],b[0,1])
        zz=z.copy();zz[:,1]+=.1;b=e.rhs(0,zz);self.assertTrue(np.all(a[0,6:]!=b[0,6:]))
        zz=z.copy();zz[:,4]+=.1;b=e.rhs(0,zz);self.assertTrue(np.all(a[0,6:]!=b[0,6:]))
    def test_no_strain_control(self):
        e=self.model('no_strain');z=e.start();a=e.rhs(0,z);z[:,1]=3.;b=e.rhs(0,z)
        np.testing.assert_array_equal(a[:,6:],b[:,6:])
    def test_frozen_passive_linear_solution(self):
        p=copy.deepcopy(self.p);p['feedback']['gain_N_s_m']=0;p['feedback']['saturation_N_s_m3']=0
        e=Ensemble(p,[dict(model='frozen',condition=0,start=0)]);z=e.start()[0];J=np.zeros((4,4))
        for j in range(4):
            y=np.zeros((1,8));y[0,j]=1;y[0,6:]=.5;J[:,j]=e.rhs(0,y)[0,:4]
        sol=solve_ivp(lambda t,y:e.rhs(t,y[None])[0],(0,4),z,method='DOP853',rtol=1e-11,atol=1e-13)
        np.testing.assert_allclose(sol.y[:4,-1],expm(J*4)@z[:4],atol=2e-10,rtol=2e-10)
    def test_force_equal_rms_and_zero_mean(self):
        P=self.p['orbit_period_s'];rms=self.p['orbital_force_rms_N']
        for c in range(1,8):
            e=self.model(condition=c)
            mean=quad(lambda t:e.force(t)[0],0,P,epsabs=1e-14)[0]/P
            power=quad(lambda t:e.force(t)[0]**2,0,P,epsabs=1e-21)[0]/P
            self.assertLess(abs(mean),1e-12);self.assertAlmostEqual(power/rms**2,1,places=9)
    def test_zero_damper_recovers_old_mechanics(self):
        p=copy.deepcopy(self.p);p['guard']['damping_per_guard_N_s_m']=0
        e=Ensemble(p,[dict(model='directional',condition=0,start=0)]);old=self.model('old');z=e.start()
        np.testing.assert_array_equal(e.rhs(0,z)[:,:4],old.rhs(0,z)[:,:4])
    def test_case_matrix(self):
        rows=cases(self.p);self.assertEqual(len(rows),128);self.assertEqual(len({tuple(r.values()) for r in rows}),128)

if __name__=='__main__':unittest.main()
