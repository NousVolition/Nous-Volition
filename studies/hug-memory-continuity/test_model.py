import copy,hashlib,json,unittest
import numpy as np
from scipy.linalg import expm
from model import Hug,protocol,exposure_weights,activation,raw_orbit,orbit_norm

class Checks(unittest.TestCase):
    def setUp(self):self.p=protocol();self.m=Hug(self.p,32);self.z=self.m.initial()
    def test_lower_exchange_exactly_off(self):
        rng=np.random.default_rng(104);S=rng.normal(size=(self.m.nr,32))*1e4
        for sign in [-1,1]:
            self.m.sign[:]=sign
            self.assertTrue(np.all(self.m.exchange(S)[:,self.m.y<=0]==0))
    def test_pair_exchange_conserves_sum(self):
        S=np.random.default_rng(105).normal(size=(self.m.nr,32))
        self.assertLess(np.max(np.abs(self.m.exchange(S).sum(axis=1))),1e-15)
    def test_source_law_exact_off_and_value(self):
        np.testing.assert_array_equal(activation(np.array([-20.,-1.,0.])),0)
        self.assertAlmostEqual(float(activation(np.array(1.))),np.exp(-1))
    def test_reversing_field_preserves_source_force(self):
        S=np.random.default_rng(12).normal(size=(self.m.nr,32))
        np.testing.assert_array_equal(self.m.memory_force(S),self.m.memory_force(-S))
    def test_no_input_does_not_erase_A(self):
        self.z[:,4:7]=[1.,.4,-.2]
        r=self.m.rhs(500,self.z,True,np.zeros(3))
        np.testing.assert_array_equal(r[:,4:7],0)
        self.assertGreater(np.max(np.abs(r[:,7:39])),0)
    def test_capacity_points_inward(self):
        for sign in [-1,1]:
            self.z[:,7:39]=sign*self.m.bound();self.z[:,4:7]=sign*1e8
            self.assertLessEqual(np.max(sign*self.m.rhs(500,self.z,True,np.zeros(3))[:,7:39]),1e-14)
    def test_incoming_budget_and_partial_transmission(self):
        for s in self.p['scenarios']:self.assertLessEqual(np.abs(exposure_weights(s)).sum(),1+1e-15)
        s=copy.deepcopy(self.p['scenarios'][0]);s['caregiver']=s['neighbor']=0
        vals=[]
        for g in range(5):s['generation']=g;vals.append(exposure_weights(s)[0])
        np.testing.assert_allclose(vals,.55**np.arange(5))
    def test_ancestry_channel_not_calibrated_by_adoption(self):
        self.assertFalse(self.p['ancestry_channel']['enabled'])
        self.assertNotIn('adoption_rate',json.dumps(self.p))
    def test_diffusion_mean_zero(self):
        S=np.random.default_rng(15).normal(size=(3,32));lap=(np.roll(S,1,1)-2*S+np.roll(S,-1,1))/self.m.ds**2
        self.assertLess(np.max(np.abs(lap.mean(axis=1))),1e-11)
    def test_orbital_rms(self):
        t=np.arange(10000)/10000
        for e in [0,.212]:self.assertAlmostEqual(float(np.sqrt(np.mean((raw_orbit(t,e,1)/orbit_norm(e))**2))),1,places=10)
    def test_energy_differential_balance(self):
        z=np.random.default_rng(16).normal(scale=.05,size=self.z.shape);z[:,-5:]=0
        for pause in [False,True]:
            dz=self.m.rhs(12,z,pause,np.zeros(3));h=1e-5
            rate=(self.m.energy(z+h*dz)-self.m.energy(z-h*dz))/(2*h)
            accounted=dz[:,-5]+dz[:,-4]+dz[:,-3]-dz[:,-2]-dz[:,-1]
            np.testing.assert_allclose(rate,accounted,atol=3e-9,rtol=2e-7)
    def test_passive_clay_against_matrix_exponential(self):
        p=copy.deepcopy(self.p);p['mechanics']['active_gain_N_s_m']=p['mechanics']['active_saturation_N_s_m3']=0;p['field']['response_strength_Pa']=0
        m=Hug(p,32,[dict(scenario='retained',condition=0,history=0)]);z=m.initial();M=np.zeros((4,4))
        for i in range(4):
            e=z*0;e[0,i]=1;M[:,i]=m.rhs(200,e,False,np.zeros(3))[0,:4]
        from scipy.integrate import solve_ivp
        sol=solve_ivp(lambda t,v:M@v,(0,10),z[0,:4],rtol=1e-11,atol=1e-13)
        np.testing.assert_allclose(sol.y[:,-1],expm(M*10)@z[0,:4],atol=1e-10)
    def test_ledger_has_no_generation_relabeling_as_direct(self):
        self.assertIn('communicated',self.p['events'][0]['route'])
        self.assertEqual(len({e['id'] for e in self.p['events']}),len(self.p['events']))

if __name__=='__main__':unittest.main()
