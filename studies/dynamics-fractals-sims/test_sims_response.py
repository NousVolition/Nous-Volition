"""Mathematical controls and participant-level tests for the SIMS extension."""
import math
import unittest
import numpy as np
from bridge_checks import reversible, linear_flow, classify, references, channel_tau
from models import integrate, ring_graph
from sims_response import (graph_cases, operators, initial_state, linear_path,
    reverse_field, reversal_path, response_parameters, rate_path,
    measurements, settling_time, protocol)


class GraphAndLinearTests(unittest.TestCase):
    def test_undirected_alignment_conserves_mean_and_reduces_spread(self):
        for name,graph in graph_cases():
            w,l=operators(graph);z=initial_state(3)
            np.testing.assert_allclose(l.sum(axis=0),0,atol=1e-14)
            self.assertLessEqual(float(np.sum(z*(-l@z))),0)
            path=linear_path(z,l,np.zeros((2,2)),[0,2])
            np.testing.assert_allclose(path[-1].mean(axis=0),z.mean(axis=0),atol=2e-15)
            self.assertLess(np.std(path[-1]),np.std(z))

    def test_collective_mean_obeys_the_exact_reference_system(self):
        z=initial_state(7);times=[0,.4,2]
        for name,graph in graph_cases():
            _,l=operators(graph)
            for case in references()['linear_reference']:
                path=linear_path(z,l,case['matrix'],times)
                exact=[linear_flow(case['matrix'],z.mean(axis=0),t) for t in times]
                np.testing.assert_allclose(path.mean(axis=1),exact,atol=1e-13)

    def test_coupled_linear_flow_against_independent_rk4(self):
        _,l=operators(ring_graph(4));a=np.array([[-.2,-1],[1,-.2]]);z=initial_state(8,4)
        def rhs(t,flat):
            y=np.array(flat).reshape(4,2)
            return (y@a.T-2*l@y).ravel()
        numeric=np.array(integrate(rhs,z.ravel(),2,.002)[-1][1:]).reshape(4,2)
        np.testing.assert_allclose(numeric,linear_path(z,l,a,[2])[0],atol=2e-11)

    def test_full_network_eigenvalues_match_graph_mode_prediction(self):
        _,l=operators(ring_graph(4));a=np.array([[1.,-1.],[-1.,0.]])
        full=np.kron(np.eye(4),a)-2*np.kron(l,np.eye(2))
        predicted=sorted(x-2*y for x in np.linalg.eigvalsh(a) for y in np.linalg.eigvalsh(l))
        np.testing.assert_allclose(np.linalg.eigvalsh(full),predicted,atol=1e-14)

    def test_unstable_collective_growth_can_coexist_with_alignment(self):
        _,l=operators(graph_cases()[2][1]);z=initial_state(5)
        path=linear_path(z,l,[[.2,-1],[1,.2]],[0,5])
        m=measurements(np.array([0,5]),path)
        self.assertLess(m['final_spread'],m['initial_spread']/1000)
        self.assertAlmostEqual(m['final_mean_norm']/np.linalg.norm(z.mean(axis=0)),math.exp(1),places=12)

    def test_neutral_reference_mode_is_not_attracted_to_zero(self):
        a=[[-1,1],[1,-1]];_,l=operators(ring_graph(4))
        z=np.tile([.3,.3],(4,1))
        np.testing.assert_allclose(linear_path(z,l,a,[0,10])[-1],z,atol=2e-14)
        self.assertIn('zero eigenvalue',classify(a)['classification'])

    def test_linear_center_preserves_collective_radius(self):
        _,l=operators(ring_graph(4));z=initial_state(1,4)
        path=linear_path(z,l,[[0,1],[-1,0]],np.linspace(0,8,81))
        np.testing.assert_allclose(np.linalg.norm(path.mean(axis=1),axis=1),np.linalg.norm(z.mean(axis=0)),atol=1e-14)

    def test_graph_relabeling_preserves_all_three_models(self):
        w,l=operators(ring_graph(4));z=initial_state(6,4);perm=[2,0,3,1]
        wp=w[np.ix_(perm,perm)];lp=l[np.ix_(perm,perm)]
        a=[[-.2,-1],[1,-.2]]
        np.testing.assert_allclose(linear_path(z[perm],lp,a,[0,1]),linear_path(z,l,a,[0,1])[:,perm],atol=1e-14)
        np.testing.assert_allclose(rate_path(z[perm,0],lp,[0,1,5],1.2,.8),rate_path(z[:,0],l,[0,1,5],1.2,.8)[:,perm],atol=1e-14)
        _,x=reversal_path(z[:,0],w,True);_,xp=reversal_path(z[perm,0],wp,True)
        np.testing.assert_allclose(xp,x[:,perm],atol=2e-13)


class ReversalParticipantTests(unittest.TestCase):
    def test_two_participant_reduction_is_the_supplied_equation(self):
        w,_=operators([[1],[0]])
        for z in [[.2,.4],[-1.2,.8],[2.,-2.]]:
            np.testing.assert_allclose(reverse_field(z,w),reversible(0,z),atol=1e-14)

    def test_network_mobility_is_positive(self):
        for name,graph in graph_cases():
            w,_=operators(graph)
            self.assertGreaterEqual(np.linalg.eigvalsh(2*np.eye(20)+w)[0],1-1e-14)

    def test_network_reversal_identity(self):
        for name,graph in graph_cases():
            w,_=operators(graph);z=initial_state(9)[:,0]
            np.testing.assert_allclose(reverse_field(-z,w),reverse_field(z,w),atol=1e-14)

    def test_population_potential_decreases_along_forward_rule(self):
        for name,graph in graph_cases():
            w,_=operators(graph);z=initial_state(2)[:,0];field=reverse_field(z,w)
            rate=float(np.cos(z)@field)
            self.assertLess(rate,0)
            finite=(np.sin(z+1e-6*field).sum()-np.sin(z-1e-6*field).sum())/2e-6
            self.assertAlmostEqual(rate,finite,places=7)
            _,path=reversal_path(z,w)
            self.assertLessEqual(float(np.max(np.diff(np.sin(path).sum(axis=1)))),1e-12)

    def test_reversal_intervention_increases_potential_and_retraces(self):
        w,_=operators(ring_graph(4));z=initial_state(2,4)[:,0]
        _,path=reversal_path(z,w,True,step=.01)
        values=np.sin(path).sum(axis=1)
        self.assertTrue(np.all(np.diff(values[:21])<0))
        self.assertTrue(np.all(np.diff(values[20:41])>0))
        np.testing.assert_allclose(path[40],z,atol=2e-7)

    def test_reversal_refinement_reduces_return_error(self):
        w,_=operators(ring_graph(4));z=initial_state(2,4)[:,0];errors=[]
        for h in [.05,.025,.0125]:
            _,path=reversal_path(z,w,True,step=h)
            errors.append(np.max(np.abs(path[40]-z)))
        self.assertTrue(all(a>10*b for a,b in zip(errors,errors[1:])),errors)


class ResponseRateTests(unittest.TestCase):
    def test_saved_material_values_set_response_rates_and_targets(self):
        p=references()['water_properties']['298.15'];h,d=p['H2O'],p['D2O'];cases=response_parameters()
        self.assertEqual(cases[0]['r'],1)
        self.assertEqual(cases[0]['q'],1)
        self.assertAlmostEqual(cases[1]['q']/cases[1]['r'],1,places=14)
        self.assertAlmostEqual(cases[3]['q']/cases[3]['r'],h['mu']/d['mu'],places=14)
        self.assertAlmostEqual(1/cases[3]['r'],channel_tau(d['rho'],d['mu'])/channel_tau(h['rho'],h['mu']),places=14)

    def test_coupled_response_against_independent_rk4(self):
        _,l=operators(ring_graph(4));initial=initial_state(6,4)[:,0];rate,gain=1.2,.8
        first=lambda t,z:gain-rate*(np.eye(4)+2*l)@z
        second=lambda t,z:-gain-rate*(np.eye(4)+2*l)@z
        middle=integrate(first,initial,4,.005)[-1][1:]
        final=integrate(second,middle,2,.005)[-1][1:]
        np.testing.assert_allclose(final,rate_path(initial,l,[6],rate,gain)[0],atol=3e-11)

    def test_target_matched_control_is_exact_time_rescaling_for_constant_signal(self):
        _,l=operators(ring_graph(4));initial=initial_state(4,4)[:,0];times=np.linspace(0,3,31)
        for parameter in response_parameters():
            r=parameter['r']
            np.testing.assert_allclose(rate_path(initial,l,times,r,r,switch=None),rate_path(initial,l,times*r,1,1,switch=None),atol=2e-14)

    def test_density_changes_initial_response_independently_of_viscosity(self):
        _,l=operators(ring_graph(4));z=np.zeros(4);eps=1e-7;cases=response_parameters()
        slope=[]
        for p in cases:
            slope.append(rate_path(z,l,[eps],p['r'],p['q'],switch=None)[0].mean()/eps)
        self.assertAlmostEqual(slope[0],slope[2],places=6)
        self.assertAlmostEqual(slope[1],slope[3],places=6)
        self.assertLess(slope[1],slope[0])

    def test_uniform_rate_settling_matches_exact_step_response(self):
        _,l=operators(ring_graph(4));times=np.arange(121)*.1
        for rate in [.9,1,1.25]:
            states=rate_path(np.ones(4),l,times,rate,rate)
            sampled=settling_time(times,states,-1)
            exact=math.log(40)/rate
            self.assertGreaterEqual(sampled+1e-12,exact)
            self.assertLess(sampled-exact,.10000001)

    def test_missing_settling_is_retained_as_unconfirmed(self):
        _,l=operators(ring_graph(4));times=np.arange(61)*.1
        states=rate_path(np.ones(4),l,times,.2,.2)
        self.assertIsNone(settling_time(times,states,-1))

    def test_25_degree_property_ratio_is_not_reused_at_other_temperatures(self):
        ratios=[p['H2O']['mu']/p['D2O']['mu'] for p in references()['water_properties'].values()]
        self.assertTrue(all(a<b for a,b in zip(ratios,ratios[1:])))
        self.assertTrue(all(r<1 for r in ratios))


class MeasurementTests(unittest.TestCase):
    def test_zero_state_is_aligned_but_not_a_unanimous_choice(self):
        metrics=measurements(np.array([0,1]),np.zeros((2,4)))
        self.assertEqual(metrics['final_spread'],0)
        self.assertFalse(metrics['final_choice_unanimity'])
        self.assertIsNone(metrics['first_choice_unanimity'])

    def test_first_unanimity_and_later_break_are_separate(self):
        states=np.array([[.2,-.2],[.2,.2],[0,0],[-.2,-.2]])
        metrics=measurements(np.array([0,1,2,3]),states)
        self.assertEqual(metrics['first_choice_unanimity'],1)
        self.assertEqual(metrics['sampled_agreement_breaks'],1)
        self.assertTrue(metrics['final_choice_unanimity'])

    def test_matched_start_and_planned_counts(self):
        np.testing.assert_array_equal(initial_state(7),initial_state(7))
        self.assertFalse(np.array_equal(initial_state(7),initial_state(8)))
        np.testing.assert_allclose(initial_state(7).mean(axis=0),[.1,-.04],atol=1e-15)
        p=protocol();n=p['matched_starts']*len(p['graphs'])
        expected={'linear':n*7,'reversal':n*2,'rate':n*4*2}
        self.assertEqual(sum(expected.values()),p['planned_counts']['total_new_sims_trajectories'])
        for name,count in expected.items():self.assertEqual(count,p['planned_counts'][name])


if __name__=='__main__':unittest.main()
