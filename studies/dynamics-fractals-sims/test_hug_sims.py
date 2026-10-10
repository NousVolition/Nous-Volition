"""Source reproduction, nonlinear SIMS controls, and the original nine checks."""
import hashlib
import importlib.util
import json
import math
import unittest
import numpy as np
from hug_sims import (ROOT, source, protocol, starting, memory_rhs, path,
                       adaptive, energy, budget, pulse_control)
from sims_response import operators, graph_cases


class HugSimsTests(unittest.TestCase):
    def test_pinned_sources_match_the_recorded_repository_bytes(self):
        d=json.loads((ROOT/'hug_sources.json').read_text())
        for row in d['files']:
            raw=(ROOT/row['local_path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
            self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['git_blob_sha'])

    def test_vectorization_matches_original_rhs_in_both_memory_branches(self):
        z=starting(8,4);z[:,2]=[0,.1,.9,2]
        p=source.Parameters()
        for t in (0,1,2,4,8):
            expected=np.array([source.rhs(t,row,p) for row in z])
            np.testing.assert_allclose(memory_rhs(t,z,p,np.zeros((4,4))),expected,rtol=0,atol=0)

    def test_zero_coupling_reproduces_original_hug_trajectory(self):
        p=source.Parameters(r=-.25,memory_coupling=1.5)
        t,z=path(np.array([[.04,.03,0,0,0]]),p,np.zeros((1,1)),coupling=0,duration=8)
        ts,old=source.integrate(p,q0=.04,v0=.03,dt=.01,end=8)
        np.testing.assert_allclose(z[:,0],old[::10],atol=1e-14)

    def test_uniform_population_is_exact_single_hug_subspace(self):
        p=source.Parameters();single=np.array([[.04,0,0,0,0]])
        _,s=path(single,p,np.zeros((1,1)),duration=4)
        for _,g in graph_cases():
            _,l=operators(g);_,z=path(np.repeat(single,20,axis=0),p,l,duration=4)
            np.testing.assert_allclose(z,np.repeat(s,20,axis=1),atol=1e-14)

    def test_reflection_preserves_pressure_memory_and_work(self):
        z=starting(9);z[:,2]=.3;p=source.Parameters();_,l=operators(graph_cases()[0][1])
        reflected=z.copy();reflected[:,:2]*=-1
        f=memory_rhs(1,z,p,l);f[:,:2]*=-1
        np.testing.assert_allclose(memory_rhs(1,reflected,p,l),f,atol=1e-15)

    def test_relabeling_relabels_the_same_participants(self):
        z=starting(3);_,l=operators(graph_cases()[0][1]);perm=np.random.default_rng(7).permutation(20)
        p=source.Parameters()
        np.testing.assert_allclose(memory_rhs(1,z[perm],p,l[np.ix_(perm,perm)]),memory_rhs(1,z,p,l)[perm],atol=1e-14)

    def test_coupling_has_zero_net_force(self):
        z=starting(4);p=source.Parameters();_,l=operators(graph_cases()[0][1])
        delta=memory_rhs(1,z,p,l)-memory_rhs(1,z,p,l,coupling=0)
        np.testing.assert_allclose(delta.sum(axis=0),0,atol=1e-14)

    def test_energy_derivative_includes_coupling_storage(self):
        p=source.Parameters();z=starting(5);z[:,2]=.4;_,l=operators(graph_cases()[0][1])
        f=memory_rhs(1,z,p,l);eps=1e-6
        derivative=(energy(z+eps*f,p,l)-energy(z-eps*f,p,l))/(2*eps)
        self.assertAlmostEqual(derivative,float(np.sum(f[:,3]-f[:,4])),places=8)

    def test_balanced_stability_matches_graph_modes(self):
        _,l=operators(graph_cases()[0][1]);n=len(l);d=.6
        for r in (-.25,1.):
            jac=np.block([[np.zeros((n,n)),np.eye(n)],[r*np.eye(n)-2*l,-d*np.eye(n)]])
            predicted=np.concatenate([np.roots([1,d,2*lam-r]) for lam in np.linalg.eigvalsh(l)])
            actual=np.linalg.eigvals(jac)
            for value in actual:self.assertLess(np.min(np.abs(predicted-value)),1e-12)
            self.assertEqual(bool(max(actual.real)>0),r>0)

    def test_integrated_energy_budget_and_independent_solver(self):
        _,l=operators([[1],[0]]);p=source.Parameters(r=1);z=starting(7,2)
        t,a=path(z,p,l,duration=8);b=adaptive(z,p,l,t)
        self.assertLess(np.max(np.abs(a-b)),2e-6)
        self.assertLess(np.max(np.abs(budget(a,p,l))),2e-7)

    def test_memory_is_positive_bounded_and_relaxes_after_pulse(self):
        p=source.Parameters();t,z=path(starting(6,2),p,np.zeros((2,2)),duration=16)
        m=z[:,0,2];self.assertGreaterEqual(m.min(),0);self.assertLessEqual(m.max(),p.pressure)
        i=np.flatnonzero(t>=4)[0]
        np.testing.assert_allclose(m[i:],m[i]*np.exp(-(t[i:]-4)/6),atol=1e-12)

    def test_exact_balance_stays_balanced_under_pressure(self):
        p=source.Parameters(r=1,pressure=1.2,memory_coupling=1.5)
        _,l=operators(graph_cases()[0][1]);_,z=path(np.zeros((20,5)),p,l,duration=8)
        np.testing.assert_array_equal(z[...,:2],0)
        self.assertGreater(z[...,2].max(),0)

    def test_opening_is_latched_geometry_and_does_not_change_rhs(self):
        p=source.Parameters(pressure=1.2);opening=source.opening_time(p)
        self.assertAlmostEqual(source.pressure(opening,p),1)
        for t in (opening+.8,8,24):
            g=source.geometry(t,[0,0,.3,0,0],p)
            self.assertFalse(g['closed']);self.assertAlmostEqual(g['bend'],0,places=14)
        self.assertIsNone(source.opening_time(source.Parameters(pressure=.99999999)))
        self.assertIsNotNone(source.opening_time(source.Parameters(pressure=1)))

    def test_pressure_pulse_cannot_be_skipped_by_main_integrator(self):
        with self.assertRaises(ValueError):
            path(starting(2,2),source.Parameters(pulse_duration=.001),np.zeros((2,2)))

    def test_original_short_pulse_failure_is_detected_by_resolved_reference(self):
        d=pulse_control()
        self.assertTrue(all(x['peak_sampled_memory']==0 for x in d['old_fixed_steps']))
        self.assertGreater(d['resolved_peak_memory'],.06)
        self.assertLess(d['independent_max_state_difference'],2e-8)

    def test_matching_design_and_saved_accuracy_gates(self):
        cfg=protocol();d=json.loads((ROOT/'hug_sims_results.json').read_text())
        self.assertEqual(d['main_runs'],384);self.assertTrue(d['accuracy_gates_passed'])
        for g in cfg['graphs']:
            for c in cfg['conditions']:
                rows=[r for r in d['runs'] if r['graph']==g and r['condition']==c['name']]
                self.assertEqual([r['seed'] for r in rows],cfg['seeds'])


def load_tests(loader,tests,pattern):
    # Run unchanged source assertions without adding pytest as a dependency.
    for name in ('test_original_hug','test_original_pressure'):
        spec=importlib.util.spec_from_file_location(name,ROOT/'hug_source/tests'/f'{name}.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for key,value in vars(module).items():
            if key.startswith('test_') and callable(value):
                tests.addTest(unittest.FunctionTestCase(value))
    return tests


if __name__=='__main__':unittest.main()
