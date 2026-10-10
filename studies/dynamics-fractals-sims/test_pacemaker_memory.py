"""Controls for directional coupling, memory, identification, and relaxation."""
import json
import math
from pathlib import Path
import unittest
import numpy as np
from models import integrate
from heteroclinic import competition_matrix,glv
from pacemaker import chain_field,integrate_chain,dominant_labels
from memory_inference import saddle_exit,branch_probability_gap,infer_matrix
from quench import relaxation_time

ROOT=Path(__file__).parent


class PacemakerMemoryTests(unittest.TestCase):
    def test_zero_coupling_equals_independent_glv(self):
        x=np.random.default_rng(42).uniform(.01,.1,(3,9))
        got=chain_field(x,0,0)
        for k in range(3):
            expected=glv(competition_matrix(gamma=1.05 if k==0 else 1.47))(0,x[k])
            np.testing.assert_allclose(got[k],expected,atol=1e-15)

    def test_open_chain_has_no_downstream_feedback(self):
        x=np.full((3,9),.1);y=x.copy();y[-1,2]+=.4
        np.testing.assert_array_equal(chain_field(x,closure=0)[0],chain_field(y,closure=0)[0])
        self.assertGreater(chain_field(y,closure=.01)[0,2],chain_field(x,closure=.01)[0,2])

    def test_diffusive_coupling_vanishes_on_equal_states(self):
        x=np.tile(np.arange(1,10)*.01,(4,1))
        np.testing.assert_allclose(chain_field(x,1.5,.01),chain_field(x,0,0),atol=1e-15)

    def test_equal_activity_does_not_count_as_a_dominant_state(self):
        self.assertEqual(int(dominant_labels(np.ones((1,9)))[0]),0)
        x=np.ones((1,9));x[0,3]=8
        self.assertEqual(int(dominant_labels(x)[0]),4)

    def test_chain_rk4_step_refinement(self):
        initial=np.random.default_rng(21).uniform(.01,.1,(1,3,9))
        a,_=integrate_chain(initial,10.,.1);b,_=integrate_chain(initial,10.,.05);c,_=integrate_chain(initial,10.,.025)
        e1=np.max(abs(a-c));e2=np.max(abs(b-c))
        self.assertGreater(e1/e2,10.)
        self.assertLess(e2,1e-7)

    def test_source_ensemble_accuracy_gates(self):
        d=json.loads((ROOT/'pacemaker_results.json').read_text())
        self.assertEqual(d['within_path_seeds']+d['between_path_seeds']+d['unresolved_seeds'],64)
        for gate in d['refinements']:
            self.assertLess(gate['max_state_error'],.002)
            self.assertTrue(gate['same_pacemaker_sequence'])
            self.assertLess(gate['last_unit_agreement_difference'],.002)
        self.assertGreater(d['minimum_activity'],0.)

    def test_saddle_exit_matches_numerical_linear_flow(self):
        time,y=saddle_exit(.001,.3,1.,.6)
        end=integrate(lambda t,x:(x[0],-.6*x[1]),(.001,.3),time,time/2000)[-1]
        self.assertAlmostEqual(end[1],1.,places=9);self.assertAlmostEqual(end[2],y,places=10)

    def test_positive_saddle_quantity_retains_offset_relative_to_noise(self):
        self.assertGreater(branch_probability_gap(.001,[.5]),branch_probability_gap(.1,[.5]))
        self.assertLess(branch_probability_gap(.001,[1.5]),branch_probability_gap(.1,[1.5]))

    def test_two_saddle_offsets_can_erase_initial_lift_off(self):
        self.assertGreater(branch_probability_gap(.001,[.4,.4]),.99)
        self.assertLess(branch_probability_gap(.001,[.4,.9]),.11)

    def test_local_memory_monte_carlo_matches_analytic_gaussian_readout(self):
        d=json.loads((ROOT/'memory_inference_results.json').read_text())['memory']
        for case in d['configurations']:
            self.assertLess(abs(case['measured_conditional_gap']-case['exact_conditional_gap']),.04)
        self.assertEqual(d['markov_control_conditional_gap'],0.)

    def test_identification_uses_full_rank_excited_data(self):
        d=json.loads((ROOT/'memory_inference_results.json').read_text())['inference']
        clean,noisy=d['cases']
        self.assertEqual(clean['rank'],9);self.assertEqual(noisy['rank'],9)
        self.assertTrue(clean['exact_transition_edges_recovered']);self.assertTrue(noisy['exact_transition_edges_recovered'])
        self.assertLess(clean['maximum_parameter_error'],2e-5)
        self.assertLess(noisy['heldout_max_state_error'],.02)

    def test_coexistence_is_rank_deficient(self):
        B=np.asarray(competition_matrix());x=np.full(9,1/sum(B[0]))
        rows=[(k*.02,*x) for k in range(100)]
        _,diagnostic=infer_matrix([rows])
        self.assertEqual(diagnostic['rank'],1)
        C=np.asarray(competition_matrix(e=.3,f=.2))
        np.testing.assert_allclose(B@x,C@x)
        self.assertFalse(np.array_equal(B,C))

    def test_relaxation_requires_staying_inside_tolerance(self):
        self.assertEqual(relaxation_time([0,50,100,150,200],[.1,.01,.1,.01,.01],confirmation=50),150.)
        self.assertIsNone(relaxation_time([0,50,100],[.1,.1,.01],confirmation=50))

    def test_quenched_equilibrium_is_stable_with_complex_modes(self):
        for gamma in (1.47,1.55,1.8,2.5):
            B=np.asarray(competition_matrix(gamma=gamma));eigen=np.linalg.eigvals(-B/sum(B[0]))
            self.assertLess(max(eigen.real),0)
            self.assertGreater(max(abs(eigen.imag)),.1)


if __name__=='__main__':unittest.main()
