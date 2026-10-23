import unittest
import numpy as np
from batch_field import BatchField,Field,Parameters,activation
from extract import agreement,normalized,canonical
from analyze import fit_memory

def episode(n=0):return dict(case=str(n),scenario=str(n),split='train',points=[[[.5,.5]],[[.5,.5]],[[.5,.5]]],counts=[1,1,1],U=[1.,.5,1.],dt=[.1,.1])

class NumericalTests(unittest.TestCase):
    def test_batch_matches_single_case_rhs(self):
        p=Parameters(n=16,kappa=.1,threshold=1.);b=BatchField([episode()],p);f=Field(p)
        z,A=f.initial(total=0.,texture=0.);z[2]=f.fft(b.targets[0,0]);r1=f.terms(z,.2)[0];r2=b.terms(z[:,None],np.array([.2]))[0][:,0]
        np.testing.assert_allclose(r1,r2,rtol=1e-12,atol=1e-12)
    def test_batch_matches_single_case_trajectory(self):
        p=Parameters(n=16,kappa=.1,threshold=1.,baseline=.3);b=BatchField([episode()],p);f=Field(p)
        z,A=f.initial(total=0.,texture=0.,speed=0.);z[2]=f.fft(b.targets[0,0])
        for U in [1.,.5]:
            for _ in range(100):z,A=f.step(z,A,U,.001)
        rr,states,_=b.run(.001);np.testing.assert_allclose(f.real(z),states[-1,:,0],atol=1e-11,rtol=1e-11)
    def test_mixed_durations_and_mass(self):
        es=[episode(0),episode(1)];es[1]['dt']=[.04,.15];p=Parameters(n=16,kappa=-.2,baseline=.4)
        rr,states,_=BatchField(es,p).run(.005)
        self.assertLess(max(abs(r['mass_error']) for r in rr),1e-12)
        self.assertLess(max(r['divergence'] for r in rr),1e-12)
        self.assertLess(max(abs(r['energy_identity']) for r in rr),1e-12)
    def test_observed_kernel_mass(self):
        e=episode();e['points'][0]=[[.2,.3],[.8,.7]];e['counts'][0]=2
        b=BatchField([e],Parameters(n=16));self.assertAlmostEqual(b.targets[0,0].mean(),2.)
    def test_no_source_constant_total(self):
        rr,_,_=BatchField([episode()],Parameters(n=16,kappa=0.)).run()
        for r in rr:self.assertAlmostEqual(r['mass'],1.)
    def test_signed_tanh_not_clipped(self):
        self.assertLess(activation(np.array([-1.]),'tanh',1.)[0],0.)
    def test_same_parameters_keep_different_inputs_separate(self):
        es=[episode(0),episode(1)];es[1]['U']=[0.,0.,0.]
        rr,ss,_=BatchField(es,Parameters(n=16,kappa=1.)).run()
        self.assertGreater(abs(ss[-1,2,0].mean()-ss[-1,2,1].mean()),.01)

class DataTests(unittest.TestCase):
    def test_agreement_sets_and_uncertainty(self):
        votes=[dict(referents=['a','b'],unidentifiable=False),dict(referents=['b','a'],unidentifiable=False),dict(referents=['a'],unidentifiable=False)]
        self.assertAlmostEqual(agreement(votes),1/3);votes[0]['unidentifiable']=True;self.assertEqual(agreement(votes),0.)
    def test_normalized_wording(self):self.assertEqual(normalized('The LARGE dot!'),'the large dot')
    def test_entity_identity_is_not_agent_prefix(self):self.assertEqual(canonical('agent_1_72'),'72')
    def test_exact_mass_coefficient_known(self):
        e=episode();e['U']=[.5,1.,1.];e['counts']=[1,1,1.025]
        baseline,k=fit_memory([e]);self.assertEqual(baseline,.5);self.assertAlmostEqual(k,10.)
    def test_no_training_changes_from_unpassed_evaluation(self):
        train=[episode()];a=fit_memory(train);test=episode();test['counts']=[7,1,3]
        self.assertEqual(a,fit_memory(train))
if __name__=='__main__':unittest.main()
