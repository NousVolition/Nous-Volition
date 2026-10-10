"""Independent checks of equilibria, orientation, invariants, and integration."""
import json
import math
from pathlib import Path
import unittest
from models import integrate
from heteroclinic import (competition_matrix,glv,jacobian,axis_state,axis_eigenvalues,
                          transition_edges,log_trajectory,visits,sequence_summary)


class HeteroclinicTests(unittest.TestCase):
    def test_matrix_matches_block_construction(self):
        B=competition_matrix()
        self.assertEqual(B[0],(1.05,2.,.2,2.,1.25,1.25,.3,1.25,1.25))
        self.assertEqual(B[3],(.3,1.25,1.25,1.05,2.,.2,2.,1.25,1.25))

    def test_nine_axis_equilibria_and_coexistence(self):
        B=competition_matrix();field=glv(B)
        for i in range(9):self.assertLess(max(abs(v) for v in field(0,axis_state(B,i))),1e-14)
        x=[1/sum(B[0])]*9
        self.assertLess(max(abs(v) for v in field(0,x)),1e-14)

    def test_jacobian_against_central_differences(self):
        B=competition_matrix();x=[.03+.01*i for i in range(9)];J=jacobian(B,x);field=glv(B)
        for j in range(9):
            a=x.copy();b=x.copy();a[j]+=1e-6;b[j]-=1e-6
            for i,(p,q) in enumerate(zip(field(0,a),field(0,b))):
                self.assertAlmostEqual((p-q)/2e-6,J[i][j],places=9)

    def test_saddle_eigenvalues_and_unstable_dimensions(self):
        for n,positive in ((3,1),(9,2)):
            B=competition_matrix(n)
            for i in range(n):
                J=jacobian(B,axis_state(B,i));values=axis_eigenvalues(B,i)
                # Only the occupied state's row can have off-diagonal entries.
                for j in range(n):
                    self.assertAlmostEqual(J[j][j],values[j])
                    if j!=i:self.assertTrue(all(abs(J[j][k])<1e-14 for k in range(n) if k!=j))
                self.assertEqual(sum(v>0 for v in values),positive)

    def test_directed_edges_have_source_to_destination_orientation(self):
        expected={(i,3*(i//3)+(i+1)%3) for i in range(9)}
        expected|={(i,(i+3)%9) for i in range(9)}
        self.assertEqual(set(transition_edges(competition_matrix())),expected)

    def test_rate_swap_preserves_all_18_available_connections(self):
        graphs=[transition_edges(competition_matrix(e=e,f=f)) for e,f in ((.2,.3),(.25,.25),(.3,.2))]
        self.assertEqual(len(graphs[0]),18)
        self.assertEqual(graphs[0],graphs[1]);self.assertEqual(graphs[0],graphs[2])

    def test_equilibrium_itself_is_not_counted_as_a_connection(self):
        self.assertTrue(all(i!=j for i,j in transition_edges(competition_matrix())))

    def test_connection_planes_have_no_positive_coexistence_equilibrium(self):
        B=competition_matrix();gamma=B[0][0]
        for i,j in transition_edges(B):
            alpha,beta=B[j][i],B[i][j]
            self.assertLess(alpha,gamma);self.assertGreater(beta,gamma)
            determinant=gamma*gamma-alpha*beta
            u=(gamma-beta)/determinant;v=(gamma-alpha)/determinant
            self.assertLess(u*v,0.)

    def test_intended_connection_graph_is_strongly_connected(self):
        graph=transition_edges(competition_matrix())
        for source in range(9):
            reached={source}
            while True:
                enlarged=reached|{j for i,j in graph if i in reached}
                if enlarged==reached:break
                reached=enlarged
            self.assertEqual(reached,set(range(9)))

    def test_all_connections_approach_their_target_in_invariant_planes(self):
        B=competition_matrix()
        for i,j in transition_edges(B):
            initial=list(axis_state(B,i));initial[j]=1e-5
            end=integrate(glv(B),initial,60.,.025)[-1][1:]
            self.assertLess(math.dist(end,axis_state(B,j)),2e-10)
            self.assertTrue(all(end[k]==0 for k in range(9) if k not in (i,j)))

    def test_constant_input_breaks_boundary_invariance(self):
        B=competition_matrix(3);x=axis_state(B,0)
        self.assertEqual(glv(B)(0,x)[1],0.)
        self.assertEqual(glv(B,1e-6)(0,x)[1],1e-6)

    def test_isolated_axis_matches_logistic_solution(self):
        B=competition_matrix(3);x0=.2;gamma=B[0][0]
        rows=integrate(glv(B),[x0,0,0],10,.02)
        error=max(abs(row[1]-1/(gamma+(1/x0-gamma)*math.exp(-row[0]))) for row in rows)
        self.assertLess(error,1e-9)

    def test_log_and_original_coordinate_integrations_agree(self):
        B=competition_matrix(3);x=(.7,.1,.03)
        logrows,_=log_trajectory(B,x,30.,.01)
        direct=integrate(glv(B),x,30.,.01)
        self.assertLess(max(abs(a-b) for p,q in zip(logrows,direct) for a,b in zip(p[1:],q[1:])),1e-8)

    def test_log_solver_rejects_zero_instead_of_adding_a_floor(self):
        with self.assertRaises(ValueError):log_trajectory(competition_matrix(3),(.8,.1,0),1.)

    def test_coordinate_swap_exchanges_two_cycle_families(self):
        A=competition_matrix(e=.2,f=.3);B=competition_matrix(e=.3,f=.2)
        p=[3*(i%3)+i//3 for i in range(9)]
        self.assertTrue(all(A[i][j]==B[p[i]][p[j]] for i in range(9) for j in range(9)))
        initial=[.01+.005*i for i in range(9)]
        a,_=log_trajectory(A,initial,40.,.04)
        b,_=log_trajectory(B,[initial[p[i]] for i in range(9)],40.,.04)
        self.assertLess(max(abs(x[i+1]-y[p[i]+1]) for x,y in zip(a,b) for i in range(9)),1e-12)

    def test_visit_interpolation_and_censoring(self):
        events=visits([(0.,.8,.1),(1.,.6,.3),(2.,.4,.5),(3.,.2,.7)],.5)
        self.assertEqual([e['state'] for e in events],[1,2])
        self.assertAlmostEqual(events[0]['end'],1.5)
        self.assertTrue(events[0]['left_censored']);self.assertFalse(events[0]['right_censored'])
        self.assertEqual(events[1]['start'],2.)
        self.assertFalse(events[1]['left_censored']);self.assertTrue(events[1]['right_censored'])

    def test_transition_counts_keep_unclassified_observations(self):
        events=[{'state':i} for i in (1,2,5,9)]
        counts=sequence_summary(events)
        self.assertEqual((counts['within'],counts['between'],counts['unclassified']),(1,1,1))
        self.assertEqual(sum(map(sum,counts['transition_counts'])),3)

    def test_same_state_histogram_does_not_determine_sequence(self):
        a=[{'state':i} for i in (1,2,3,4,5,6,7,8,9)]
        b=[{'state':i} for i in (1,4,7,2,5,8,3,6,9)]
        self.assertEqual(sorted(x['state'] for x in a),sorted(x['state'] for x in b))
        self.assertNotEqual(sequence_summary(a)['transition_counts'],sequence_summary(b)['transition_counts'])

    def test_saved_long_trajectory_accuracy_and_no_underflow(self):
        d=json.loads(Path(__file__).with_name('heteroclinic_results.json').read_text())
        gates=[d['three_state']['refinement'],*d['nine_state']['refinement']]
        for gate in gates:
            self.assertLess(gate['max_state_error'],1e-5)
            self.assertTrue(gate['same_sequence'])
        for case in d['nine_state']['conditions']:
            self.assertTrue(all(run['minimum_log_activity']>-700 for run in case['runs']))


if __name__=='__main__':unittest.main()
