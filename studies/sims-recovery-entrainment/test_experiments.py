import hashlib,importlib.util,json,sys,unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from recovery_model import Config,run,initialize
from oscillators import triangle,drift_period,integrate_phase,network_rhs,rk4,phase_rhs,circle_solutions,junction_rhs
from analyze import recovery_time


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parent.parent/'social-organization/model.py'
        spec=importlib.util.spec_from_file_location('original_social',path)
        cls.old=importlib.util.module_from_spec(spec);sys.modules['original_social']=cls.old;spec.loader.exec_module(cls.old)

    def test_original_source_and_default_equivalence(self):
        provenance=json.loads(Path('model_provenance.json').read_text())
        self.assertEqual(hashlib.sha256(Path(provenance['source']).read_bytes()).hexdigest(),provenance['source_sha256'])
        for topology in ('ring','random','hub'):
            c=Config(n=30,rounds=120,stress=1,memory=1,transitions=1,behavior=1,identity=.7,topology=topology)
            expected=self.old.run(c,True)
            for actual in (run(c,True),run(c,True,[(40,80)])):
                self.assertEqual(expected['digest'],actual['digest'])
                np.testing.assert_equal(expected['events'],actual['events'])

    def test_extended_prefix_matches_original(self):
        c=Config(n=30,rounds=120,stress=1,memory=1,transitions=1,behavior=1,identity=.7)
        a=self.old.run(c,True);b=run(replace(c,rounds=480),True,[(40,80)])
        np.testing.assert_equal(a['events'],b['events'][:120])

    def test_no_anticipation_and_empty_schedule(self):
        c=Config(n=30,rounds=120,stress=1,memory=1,transitions=1)
        a=run(c,True,[]);b=run(c,True,[(60,80)])
        self.assertEqual(a['digest'],self.old.run(replace(c,stress=0))['digest'])
        np.testing.assert_equal(a['events'][:60],b['events'][:60])
        self.assertNotEqual(a['digest'],b['digest'])

    def test_bad_schedules_rejected(self):
        for windows in ([(-1,4)],[(2,2)],[(0,9),(8,10)],[(0,121)],[(1.5,3)]):
            with self.assertRaises(ValueError):run(Config(),stress_windows=windows)

    def test_triangle_periodicity_peaks_and_matching(self):
        x=np.linspace(-9,9,1001)
        np.testing.assert_allclose(triangle(x),triangle(x+2*np.pi),atol=4e-15)
        self.assertAlmostEqual(float(triangle(np.pi/2)),np.pi/2)
        self.assertAlmostEqual(float(triangle(-np.pi/2)),-np.pi/2)
        self.assertAlmostEqual(float(triangle(np.pi/2,True)),1.)
        np.testing.assert_allclose(triangle(x),-triangle(-x),atol=2e-15)

    def test_drift_periods_against_independent_quadrature(self):
        theta=np.linspace(0,2*np.pi,100001)
        for response in ('sine','triangle','triangle_normalized'):
            for delta in (1.8,2.5):
                integral=np.trapezoid(1/phase_rhs(theta,delta,response=response),theta)
                self.assertAlmostEqual(float(drift_period(delta,response=response)),float(integral),places=7)

    def test_measured_turns_agree_with_formula(self):
        for response in ('sine','triangle','triangle_normalized'):
            result=integrate_phase([1.8,2.5],response,dt=.02,duration=60,transient=20)
            np.testing.assert_allclose(result['measured_period'],drift_period(np.array([1.8,2.5]),response=response),rtol=2e-4)

    def test_stable_locked_phase_and_threshold(self):
        c=integrate_phase([.25,.75],duration=40,transient=20)
        np.testing.assert_allclose(c['final'],np.arcsin([.25,.75]),atol=1e-9)
        self.assertTrue(np.isinf(drift_period(1.)))
        self.assertAlmostEqual(float(phase_rhs(np.pi/2,1.)),0.)

    def test_junction_fixed_point_and_overdamped_force(self):
        phi=np.arcsin(.6)
        np.testing.assert_allclose(junction_rhs(np.array([phi,0.]),.6,2),0,atol=1e-15)
        state=np.array([.5,.2]);rhs=junction_rhs(state,1.2,3.)
        self.assertAlmostEqual(3*rhs[1]+state[1]+np.sin(state[0]),1.2)

    def test_circle_roots_and_stability_from_flow(self):
        funcs=[lambda x:1+2*np.cos(x),lambda x:np.sin(2*x),lambda x:np.sin(x)**3,
               lambda x:np.sin(x)+np.cos(x),lambda x:3+np.cos(2*x),lambda x:np.sin(3*x)]
        for row,f in zip(circle_solutions(),funcs):
            for root,kind in zip(row['roots'],row['stability']):
                self.assertAlmostEqual(f(root),0.)
                stable=kind.startswith('stable')
                self.assertEqual(f(root-1e-3)>0,stable);self.assertEqual(f(root+1e-3)<0,stable)
        theta=np.linspace(0,2*np.pi,10001)
        self.assertAlmostEqual(float(np.trapezoid(1/(3+np.cos(2*theta)),theta)),np.pi/np.sqrt(2))

    def test_network_global_phase_symmetry_without_driver(self):
        a,_,_,_=initialize(Config(n=30));phi=np.linspace(-2,2,30)[None,:]
        np.testing.assert_allclose(network_rhs(phi,.1,a,0),network_rhs(phi+1.234,.1,a,0),atol=3e-15)

    def test_identical_sims_reduce_to_scalar_driver(self):
        for topology in ('ring','random','hub'):
            a,_,_,_=initialize(Config(n=30,topology=topology));phi=np.full((1,30),.2);scalar=np.array([.2])
            for _ in range(100):
                phi=rk4(phi,.02,lambda x:network_rhs(x,.5,a,1))
                scalar=rk4(scalar,.02,lambda x:phase_rhs(x,.5))
            np.testing.assert_allclose(phi,np.broadcast_to(scalar,phi.shape),atol=2e-15)

    def test_recovery_censoring_and_temporary_crossing(self):
        a=np.full((8,3),.1);self.assertIsNone(recovery_time(a,0)['first_attainment'])
        a[2:4,1:]=0;r=recovery_time(a,0)
        self.assertEqual(r['first_attainment'],40);self.assertFalse(r['last_40_all_within'])


if __name__=='__main__':unittest.main(verbosity=2)
