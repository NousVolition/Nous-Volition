"""Executable topology checks and controls for interpreting SIMS aggregation."""
from fractions import Fraction
from itertools import combinations, product
import unittest
from models import menger_graph
from sims import run
from topology import (graph,reflexive,edges,connected,map_audit,compose,pullback,lifts,
    transitivity_witness,transitive_closure,menger_parent,face,degeneracy,
    check_identities,insert_zero,merge_weights,realize,complex_from_facets,
    skeleton,boundary_columns,gf2_rank,homology,triangle_chain,contacts,
    nerve_face,nerve_degeneracy,nerve_checks,cube_face,cube_projection,
    cube_connection,cubical_checks,expected_block_change,aggregation_counterexample,menger_symmetries)


class GraphProjectionTests(unittest.TestCase):
    def test_surjectivity_on_vertices_is_insufficient(self):
        path=graph(3,[(0,1),(1,2)]);triangle=graph(3,[(0,1),(1,2),(0,2)])
        audit=map_audit(path,triangle,(0,1,2))
        self.assertTrue(audit['homomorphism']);self.assertTrue(audit['vertex_surjective'])
        self.assertFalse(audit['edge_surjective']);self.assertFalse(audit['connected_epimorphism'])

    def test_edge_surjectivity_is_insufficient(self):
        audit=map_audit(graph(3,[(0,1),(1,2)]),graph(2,[(0,1)]),(0,1,0))
        self.assertTrue(audit['edge_surjective']);self.assertFalse(audit['connected_fibers'])

    def test_connected_fiber_criterion_against_all_subsets(self):
        targets=[graph(3,[(0,1),(1,2)]),graph(3,[(0,1),(1,2),(0,2)])]
        sources=[graph(4,[(0,1),(1,2),(2,3)]),graph(4,[(0,1),(1,2),(2,3),(3,0)])]
        compared=0
        for source,target in product(sources,targets):
            for mapping in product(range(3),repeat=4):
                audit=map_audit(source,target,mapping)
                if not all(audit[k] for k in ('homomorphism','vertex_surjective','edge_surjective')):continue
                all_connected=True
                for n in (1,2,3):
                    for subset in combinations(range(3),n):
                        if connected(target,subset):
                            all_connected &= connected(source,[i for i in range(4) if mapping[i] in subset])
                self.assertEqual(audit['connected_fibers'],all_connected);compared+=1
        self.assertGreater(compared,10)

    def test_menger_parent_maps_and_composition(self):
        levels=[reflexive(menger_graph(n)) for n in range(3)]
        p1,p2=menger_parent(1),menger_parent(2)
        self.assertTrue(map_audit(levels[2],levels[1],p2)['connected_epimorphism'])
        self.assertTrue(map_audit(levels[1],levels[0],p1)['connected_epimorphism'])
        self.assertEqual(set(compose(p1,p2)),{0})
        self.assertTrue(all(p2.count(i)==20 for i in range(20)))

    def test_transitivity_failure_and_closure(self):
        G=reflexive(menger_graph(1));x,y,z=transitivity_witness(G)
        self.assertIn(y,G[x]);self.assertIn(z,G[y]);self.assertNotIn(z,G[x])
        closure=transitive_closure(G)
        self.assertIsNone(transitivity_witness(closure))
        self.assertEqual(len(edges(G,False)),24);self.assertEqual(len(edges(closure,False)),190)

    def test_disconnected_closure_preserves_components(self):
        G=graph(5,[(0,1),(1,2),(3,4)]);closure=transitive_closure(G)
        self.assertEqual(closure[0],(0,1,2));self.assertEqual(closure[4],(3,4))

    def test_menger_symmetry_orbits_separate_position_types(self):
        result=menger_symmetries()
        self.assertEqual(result['verified_coordinate_symmetries'],48)
        self.assertEqual(sorted((r['size'],r['contact_degree']) for r in result['orbits']),[(8,3),(12,2)])
        self.assertEqual(sorted(i for r in result['orbits'] for i in r['seats']),list(range(20)))

    def test_pullback_commutes_and_projections_are_connected(self):
        A=graph(2,[(0,1)]);B=graph(3,[(0,1),(1,2)]);g=(0,0,1);f=(0,1,1)
        D,pB,pC,pairs=pullback(B,B,A,g,f)
        self.assertEqual(len(D),4);self.assertEqual(compose(g,pB),compose(f,pC))
        self.assertTrue(map_audit(D,B,pB)['connected_epimorphism'])
        self.assertTrue(map_audit(D,B,pC)['connected_epimorphism'])

    def test_finite_lift_can_require_refinement(self):
        A=graph(2,[(0,1)]);B=graph(3,[(0,1),(1,2)]);g=(0,0,1);f=(0,1,1)
        self.assertEqual(lifts(B,B,A,f,g),[])
        D,pB,pC,pairs=pullback(B,B,A,g,f);fD=compose(f,pC)
        self.assertEqual(lifts(D,B,A,fD,g,{0:0,3:2}),[(0,1,2,2)])
        self.assertEqual(g[0],fD[1])
        self.assertEqual(lifts(D,B,A,fD,g,{1:0}),[])
        with self.assertRaises(ValueError):lifts(B,B,A,f,(0,1,0))


class SimplicialTests(unittest.TestCase):
    def test_all_five_simplicial_identity_families(self):
        counts=check_identities(6)
        self.assertEqual(len(counts),5);self.assertTrue(all(v>100 for v in counts.values()))

    def test_face_gluing_in_barycentric_coordinates(self):
        vertices=((0,0),(2,0),(0,3));simplex=(0,1,2)
        for i in range(3):
            for numerator in range(6):
                p=(Fraction(numerator,5),Fraction(5-numerator,5))
                self.assertEqual(realize(face(simplex,i),p,vertices),realize(simplex,insert_zero(p,i),vertices))

    def test_degeneracy_gluing_in_barycentric_coordinates(self):
        vertices=((0,0),(2,0),(0,3));simplex=(0,1,2)
        for i in range(3):
            for a,b,c in product(range(4),repeat=3):
                if a+b+c>3:continue
                weights=tuple(Fraction(x,3) for x in (a,b,c,3-a-b-c))
                self.assertEqual(realize(degeneracy(simplex,i),weights,vertices),
                                 realize(simplex,merge_weights(weights,i),vertices))

    def test_nerve_faces_compose_and_degeneracies_insert_identity(self):
        self.assertEqual(nerve_face((1,2),1),(0,))
        self.assertEqual(nerve_face((1,2),0),(2,))
        self.assertEqual(nerve_face((1,2),2),(1,))
        self.assertEqual(nerve_degeneracy((1,2),1),(1,0,2))
        self.assertGreater(nerve_checks(5)['equalities_checked'],20000)

    def test_nerve_functor_respects_faces_and_degeneracies(self):
        functor=lambda chain:tuple(2*a%3 for a in chain)
        for degree in range(1,5):
            for chain in product(range(3),repeat=degree):
                for i in range(degree+1):
                    self.assertEqual(functor(nerve_face(chain,i)),nerve_face(functor(chain),i))
                    self.assertEqual(functor(nerve_degeneracy(chain,i)),nerve_degeneracy(functor(chain),i))

    def test_homology_of_known_complexes(self):
        expected=[([(0,1),(1,2),(0,2)],[1,1]), ([(0,1,2)],[1,0,0]),
                  (list(combinations(range(4),3)),[1,0,1]),([tuple(range(4))],[1,0,0,0])]
        for facets,betti in expected:
            result=homology(complex_from_facets(facets))
            self.assertEqual(result['betti_Z2'],betti)
            self.assertEqual(result['euler_characteristic'],sum((-1)**i*b for i,b in enumerate(betti)))

    def test_boundary_of_boundary_is_zero(self):
        K=complex_from_facets([(0,1,2,3),(1,2,3,4)])
        for degree in (2,3):
            lower=boundary_columns(K,degree-1)
            for column in boundary_columns(K,degree):
                composition=0
                for i,c in enumerate(lower):
                    if column>>i&1:composition^=c
                self.assertEqual(composition,0)

    def test_fill_changes_homology_but_not_pairwise_contacts(self):
        wire,filled=triangle_chain(False),triangle_chain(True)
        self.assertEqual(homology(wire)['betti_Z2'],[1,4])
        self.assertEqual(homology(filled)['betti_Z2'],[1,0,0])
        self.assertEqual(skeleton(wire),skeleton(filled))


class CubicalTests(unittest.TestCase):
    def test_supplied_cube_relations(self):
        self.assertGreater(cubical_checks(4)['equalities_checked'],6000)

    def test_connection_convention_selected_by_zero_identity(self):
        p=(Fraction(2,5),)
        self.assertEqual(cube_connection(cube_face(p,0,0),0),p)
        self.assertNotEqual((min(0,p[0]),),p)
        self.assertEqual(cube_connection(cube_face(p,0,1),0),(1,))

    def test_cube_and_simplex_degeneracies_are_different(self):
        p=(Fraction(1,5),Fraction(3,10),Fraction(1,2))
        self.assertEqual(cube_projection(p,1),(Fraction(1,5),Fraction(1,2)))
        self.assertEqual(merge_weights(p,1),(Fraction(1,5),Fraction(4,5)))


class TopologySIMSTests(unittest.TestCase):
    def test_identical_contacts_give_identical_complete_outcome(self):
        initial=[0,1,0,1,1,0,0,1,0]
        for initiative in (0,.02):
            left=run(contacts(skeleton(triangle_chain(False))),initial,42,initiative=initiative)
            right=run(contacts(skeleton(triangle_chain(True))),initial,42,initiative=initiative)
            self.assertEqual(left,right)

    def test_valid_projection_does_not_close_block_dynamics(self):
        result=aggregation_counterexample()
        self.assertTrue(result['map_audit']['connected_epimorphism'])
        self.assertEqual(result['ones_per_block'][0],result['ones_per_block'][1])
        self.assertNotEqual(result['expected_change_in_block_ones'][0],result['expected_change_in_block_ones'][1])

    def test_exact_drift_matches_enumerated_update_distribution(self):
        G=graph(6,[(i,i+1) for i in range(5)]);mapping=(0,0,0,1,1,1);state=(0,0,1,0,0,1)
        changes=[Fraction(0),Fraction(0)]
        for seat,row in enumerate(contacts(G)):
            for donor in row:
                after=list(state);after[seat]=state[donor]
                probability=Fraction(1,6*len(row))*Fraction(17,20)
                for block in (0,1):
                    delta=sum(after[i]-state[i] for i in range(6) if mapping[i]==block)
                    changes[block]+=probability*delta
        self.assertEqual(tuple(changes),expected_block_change(G,state,mapping))

    def test_identity_renaming_preserves_seat_behavior(self):
        G=contacts(skeleton(triangle_chain(True)));initial=[0,1,0,1,1,0,0,1,0]
        ordinary=run(G,initial,999);renamed=run(G,initial,999,seat_to_id=list(reversed(range(9))))
        for key in ('first_consensus','unanimous_at_end','switches','refusals','final','credits_by_seat'):
            self.assertEqual(ordinary[key],renamed[key])


if __name__=='__main__':unittest.main()
