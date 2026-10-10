"""Orbit conservation/independent integration and clay-SIMS reduction tests."""
import copy
import json
import unittest
import numpy as np
from scipy.integrate import quad
from orbits import (ROOT,protocol,kepler,orbit,orbit_control,load_factor,applied_load,
                    material,uniform_path,uniform_quadrature,path,adaptive,gates_pass,reproduction_check)
from clay_sims import ClayNetwork,initial,source,sample_grid,path as old_path
from sims_response import graph_cases,operators


class OrbitTests(unittest.TestCase):
    def setUp(self):
        self.moons=protocol()['moons'];self.moon=self.moons[0]

    def test_names_and_requested_groups(self):
        self.assertEqual([m['name'] for m in self.moons],['Pasiphae','Elara','Himalia','Europa','Callisto','Thebe'])
        self.assertEqual([m['requested_group'] for m in self.moons],['CO']*3+['Eccentric']*3)
        self.assertEqual(protocol()['aliases_assumed'],{'Dasiphae':'Pasiphae','thebes':'Thebe'})

    def test_source_transcription(self):
        expected=[(508,23463200,.412,734.4215),(507,11710700,.212,258.8861),
                  (506,11439000,.160,249.9090),(502,671100,.009,3.525463),
                  (504,1882700,.007,16.690440),(514,221900,.018,.676105)]
        self.assertEqual([(m['code'],m['a_km'],m['e'],m['period_days']) for m in self.moons],expected)
        self.assertEqual(protocol()['source_epoch_TDB'],'2000-01-01.5')

    def test_kepler_high_eccentricity_and_wrapped_anomalies(self):
        m=np.linspace(-40,40,2001)
        for e in (0,.412,.95,.999):
            E=kepler(m,e);wrapped=(m+np.pi)%(2*np.pi)-np.pi
            np.testing.assert_allclose(E-e*np.sin(E),wrapped,atol=2.1e-14,rtol=0)

    def test_invalid_eccentricity_and_anomalies(self):
        for e in (-.1,1,2,float('nan')):
            with self.assertRaises(ValueError):kepler(0,e)
        with self.assertRaises(ValueError):kepler(float('inf'),.1)

    def test_invalid_axis_and_period(self):
        for field in ('a_km','period_days'):
            for v in (0,-1,float('inf')):
                m=dict(self.moon);m[field]=v
                with self.assertRaises(ValueError):orbit(m,0)

    def test_circular_radius_and_speed(self):
        for m in self.moons:
            xy,v=orbit(m,np.linspace(0,m['period_days'],361),0)
            np.testing.assert_allclose(np.linalg.norm(xy,axis=-1),m['a_km'],rtol=3e-15)
            np.testing.assert_allclose(np.linalg.norm(v,axis=-1),2*np.pi*m['a_km']/m['period_days'],rtol=3e-15)

    def test_apsides_for_each_moon(self):
        for m in self.moons:
            xy,_=orbit(m,np.array([0,m['period_days']/2]))
            np.testing.assert_allclose(np.linalg.norm(xy,axis=-1),m['a_km']*np.array([1-m['e'],1+m['e']]),rtol=2e-15)

    def test_periodic_return(self):
        for m in self.moons:
            x,v=orbit(m,np.array([0,m['period_days']]))
            np.testing.assert_allclose(x[0],x[1],atol=1e-7)
            np.testing.assert_allclose(v[0],v[1],atol=1e-8)

    def test_velocity_is_position_derivative(self):
        for m in self.moons:
            t=.23*m['period_days'];dt=m['period_days']*1e-6
            x,_=orbit(m,np.array([t-dt,t+dt]));_,v=orbit(m,t)
            np.testing.assert_allclose((x[1]-x[0])/(2*dt),v,rtol=1e-8)

    def test_energy_and_angular_momentum(self):
        for m in self.moons:
            x,v=orbit(m,np.linspace(0,m['period_days'],721));a=m['a_km'];n=2*np.pi/m['period_days'];mu=n*n*a**3
            energy=np.sum(v*v,axis=-1)/2-mu/np.linalg.norm(x,axis=-1)
            h=x[:,0]*v[:,1]-x[:,1]*v[:,0]
            np.testing.assert_allclose(energy,-mu/(2*a),rtol=5e-15)
            np.testing.assert_allclose(h,np.sqrt(mu*a*(1-m['e']**2)),rtol=5e-15)

    def test_equal_areas_in_equal_times(self):
        m=self.moon;a=m['a_km'];p=m['period_days'];e=m['e']
        edges=np.linspace(0,2*np.pi,9);E=kepler(edges,e)
        # Continuous eccentric anomaly for the second half of the orbit.
        E=np.unwrap(E); area=.5*a*a*np.sqrt(1-e*e)*(E-e*np.sin(E))
        # Kepler residual <=2e-14 rad; differences of two areas amplify its relative bound.
        np.testing.assert_allclose(np.diff(area),np.pi*a*a*np.sqrt(1-e*e)/8,rtol=1e-13)

    def test_time_reversal(self):
        x,v=orbit(self.moon,np.array([-.17,.17])*self.moon['period_days'])
        np.testing.assert_allclose(x[0],x[1]*[1,-1],rtol=1e-13)
        np.testing.assert_allclose(v[0],v[1]*[-1,1],rtol=1e-13)

    def test_cartesian_solver_independent_of_kepler(self):
        r=orbit_control(self.moon,self.moon['e'])
        self.assertLess(r['max_position_error_over_a'],1e-8)
        self.assertLess(r['max_velocity_error_over_a_per_period'],1e-7)

    def test_load_mean_normalization(self):
        for m in self.moons:
            self.assertAlmostEqual(quad(lambda q:float(load_factor(q,m['e'])),0,1,epsabs=1e-12)[0],1,places=12)

    def test_load_endpoint_limits(self):
        e=.412
        self.assertEqual(applied_load(20,e,'left'),0)
        self.assertEqual(applied_load(120,e,'right'),0)
        self.assertGreater(applied_load(20,e,'right'),20)
        self.assertAlmostEqual(applied_load(20,e),applied_load(120,e,'left'),places=12)
        self.assertEqual(applied_load(121,e),0)

    def test_circular_clay_matches_original_step_formula(self):
        z,loads=uniform_path(0);m=material()
        for i,(t,side) in enumerate(sample_grid()):
            expected=source.state_at(m,t,side)['total']
            self.assertAlmostEqual(z[i].sum()+loads[i]/m['G_M_Pa'],expected,places=12)

    def test_independent_clay_convolution(self):
        for e in (0,.009,.412):
            z,_=uniform_path(e)
            for i,(t,side) in enumerate(sample_grid()):
                if t in (35,70,120,420):
                    np.testing.assert_allclose(z[i],uniform_quadrature(t,e),atol=1e-12,rtol=0)

    def test_equal_retained_mean_and_recovery(self):
        m=material();expected=20*100/m['eta_M_Pa_s']
        for e in (0,.007,.018,.16,.212,.412):
            z,_=uniform_path(e)
            self.assertAlmostEqual(z[-1,1],expected,places=12)
            self.assertGreater(z[-1,0],0)
            self.assertLess(z[-1,0],z[120,0])

    def test_network_uniform_reduction_and_spread_invariance(self):
        starts=np.array([initial(20261020),initial(20261021)])
        for name,graph in graph_cases():
            _,l=operators(graph);net=ClayNetwork(material(),l)
            _,base,_=path(net,starts,0)
            for e in (.018,.412):
                z,g,loads=path(net,starts,e);u,_=uniform_path(e)
                np.testing.assert_allclose(g.mean(axis=-1),(u.sum(axis=-1)+loads/net.gm)[:,None]+np.zeros((len(g),2)),atol=1e-12,rtol=0)
                np.testing.assert_allclose(g.std(axis=-1),base.std(axis=-1),atol=1e-12,rtol=0)

    def test_full_coordinate_clay_solver(self):
        _,l=operators(graph_cases()[0][1]);net=ClayNetwork(material(),l);start=initial(20261020)
        z,g,_=path(net,start,.412);az,ag=adaptive(net,start,.412,'Radau')
        np.testing.assert_allclose(az,z,atol=1e-9,rtol=0)
        np.testing.assert_allclose(ag,g,atol=1e-9,rtol=0)

    def test_network_circular_regression(self):
        _,l=operators(graph_cases()[0][1]);net=ClayNetwork(material(),l);start=initial(20261020)
        z,g,loads=path(net,start,0);az,ag,al=old_path(net,start)
        np.testing.assert_allclose(z,az,atol=1e-12,rtol=0)
        np.testing.assert_allclose(g,ag,atol=1e-12,rtol=0)

    def test_saved_counts_and_paired_starts(self):
        d=json.loads((ROOT/'orbit_results.json').read_text());self.assertEqual(d['main_runs'],672)
        self.assertEqual(len(d['orbit_controls']),12);self.assertEqual(len(d['runs']),672)
        self.assertTrue(d['accuracy_gates_passed']);self.assertTrue(gates_pass(d))
        by_seed={}
        for r in d['runs']:
            by_seed.setdefault(r['seed'],r['initial_retained_strain'])
            self.assertEqual(r['initial_retained_strain'],by_seed[r['seed']])
        self.assertEqual(len(by_seed),32)

    def test_reproduction_rejects_changed_outcome_and_gate_failure(self):
        d=json.loads((ROOT/'orbit_results.json').read_text());other=copy.deepcopy(d)
        other['runs'][0]['final_mean_strain']+=.001
        self.assertFalse(reproduction_check(d,other))
        other=copy.deepcopy(d);other['controls'][0]['paired_spread_error']=.01
        self.assertFalse(reproduction_check(d,other))


if __name__=='__main__':unittest.main()
