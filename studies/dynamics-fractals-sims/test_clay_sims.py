"""Constitutive, coupling, jump, energy and participant checks for current clay SIMS."""
import copy
import hashlib
import json
import unittest
import numpy as np
from scipy.linalg import expm
from clay_sims import (ROOT,source,ClayNetwork,protocol,initial,path,sample_grid,
                      adaptive,energy_control,reproduction_check)
from sims_response import graph_cases,operators


class ClaySimsTests(unittest.TestCase):
    def setUp(self):
        self.m=source.materials()[0]
        self.l=operators(graph_cases()[0][1])[1]
        self.net=ClayNetwork(self.m,self.l)

    def test_source_snapshot_hashes(self):
        for row in json.loads((ROOT/'clay_sources.json').read_text())['files']:
            self.assertEqual(hashlib.sha256((ROOT/row['local_path']).read_bytes()).hexdigest(),row['sha256'])

    def test_four_published_coefficient_rows(self):
        expected=[[10,19000,2300000,15000,600000],[20,24000,6700000,25000,1500000],
                  [30,23000,7900000,31000,1200000],[40,20000,8500000,30000,1300000]]
        np.testing.assert_array_equal([list(m.values()) for m in source.materials()],expected)

    def test_source_zero_load_is_zero(self):
        for t in (0,20,50,120,420):self.assertEqual(source.state_at(dict(self.m,stress_Pa=0),t)['total'],0)

    def test_source_loading_formula(self):
        for m in source.materials():
            t=37.;s=m['stress_Pa'];a=source.state_at(m,20+t)
            exact=s/m['G_M_Pa']+s/m['G_K_Pa']*(1-np.exp(-m['G_K_Pa']*t/m['eta_K_Pa_s']))+s*t/m['eta_M_Pa_s']
            self.assertAlmostEqual(a['total'],exact,places=15)

    def test_source_loading_and_release_jumps(self):
        for m in source.materials():
            for t,sign in [(20,1),(120,-1)]:
                left=source.state_at(m,t,'left');right=source.state_at(m,t,'right')
                self.assertAlmostEqual(right['total']-left['total'],sign*m['stress_Pa']/m['G_M_Pa'],places=15)
                for k in ('delayed','retained'):self.assertEqual(left[k],right[k])

    def test_source_recovery_and_retained_limit(self):
        for m in source.materials():
            released=source.state_at(m,120);later=source.state_at(m,180)
            self.assertAlmostEqual(later['delayed'],released['delayed']*np.exp(-60*m['G_K_Pa']/m['eta_K_Pa_s']),places=15)
            self.assertEqual(later['retained'],m['stress_Pa']*100/m['eta_M_Pa_s'])
            self.assertAlmostEqual(source.state_at(m,5000)['total'],later['retained'],places=15)

    def test_uncoupled_network_reproduces_exact_source_at_every_sample(self):
        for m in source.materials():
            net=ClayNetwork(m,np.zeros((1,1)),0);z,g,_=path(net,np.zeros((1,2)))
            expected=np.array([[source.state_at(m,t,side)[key] for key in ('delayed','retained','total')] for t,side in sample_grid()])
            np.testing.assert_allclose(np.column_stack((z[:,0],g[:,0])),expected,rtol=1e-12,atol=1e-15)

    def test_arbitrary_uncoupled_prestrain(self):
        net=ClayNetwork(self.m,np.zeros((3,3)),0);z=np.array([[.001,.002],[-.001,.003],[0,-.004]])
        load=np.array([10.,-10.,0]);t=17.;a=net.evolve(z,load,[t])[0]
        u=load/net.gk+(z[:,0]-load/net.gk)*np.exp(-net.gk*t/net.ek)
        w=z[:,1]+t*load/net.em
        np.testing.assert_allclose(a,np.column_stack((u,w)),atol=1e-15)

    def test_population_mean_matches_source_on_all_graphs(self):
        for _,g in graph_cases():
            net=ClayNetwork(self.m,operators(g)[1]);_,strain,_=path(net,initial(20261020))
            expected=[source.state_at(self.m,t,side)['total'] for t,side in sample_grid()]
            np.testing.assert_allclose(strain.mean(axis=1),expected,atol=2e-17)

    def test_elastic_and_neighbor_stresses_balance(self):
        z=initial(4);load=np.linspace(-10,10,20);g=self.net.gamma(z,load)
        stress=self.net.gm*(g-z.sum(axis=1))
        np.testing.assert_allclose(stress+self.net.k*self.l@g,load,atol=1e-12)

    def test_neighbor_forces_sum_to_zero(self):
        z=initial(9);s=self.net.stress(z,np.full(20,10.))
        self.assertAlmostEqual(float(s.sum()),200,places=10)

    def test_relabeling_equivariance(self):
        perm=np.random.default_rng(8).permutation(20);z=initial(9);load=np.linspace(-10,10,20)
        other=ClayNetwork(self.m,self.l[np.ix_(perm,perm)])
        np.testing.assert_allclose(other.evolve(z[perm],load[perm],[5,70]),self.net.evolve(z,load,[5,70])[:,perm],atol=1e-16)

    def test_reflection_requires_reflected_load_and_state(self):
        z=initial(8);s=np.full(20,10.)
        np.testing.assert_allclose(self.net.evolve(-z,-s,[10,100]),-self.net.evolve(z,s,[10,100]),atol=1e-16)

    def test_uniform_state_has_single_clay_response(self):
        z=np.tile([.001,-.0003],(20,1));s=np.full(20,10.)
        scalar=ClayNetwork(self.m,np.zeros((1,1)),0).evolve(z[:1],s[:1],[10,100])
        np.testing.assert_allclose(self.net.evolve(z,s,[10,100]),np.repeat(scalar,20,axis=1),atol=1e-16)

    def test_original_joined_outline_stays_joined_under_clay_shear(self):
        from hug_sims import source as old_geometry
        a,b=old_geometry.arm_points(1,points=65)
        for strain in (-.004,0,.004):
            aa,bb=(source.shear_points(p,strain) for p in (a,b))
            self.assertEqual(aa[0],bb[0]);self.assertEqual(aa[-1],bb[-1])
            def area(points):
                x=np.array(points);return abs(np.sum(x[:,0]*np.roll(x[:,1],-1)-x[:,1]*np.roll(x[:,0],-1)))/2
            self.assertAlmostEqual(area(a+b[::-1]),area(aa+bb[::-1]),places=12)

    def test_modal_solution_against_full_augmented_matrix_exponential(self):
        l=operators([[1],[0]])[1];net=ClayNetwork(self.m,l);z=initial(4,2);s=np.array([10.,-4.]);zero=np.zeros_like(z)
        b=net.rhs(zero,s).ravel()
        a=np.column_stack([net.rhs(e.reshape(2,2),np.zeros(2)).ravel() for e in np.eye(4)])
        augmented=np.zeros((5,5));augmented[:4,:4]=a;augmented[:4,4]=b
        expected=(expm(37*augmented)@np.r_[z.ravel(),1])[:4].reshape(2,2)
        np.testing.assert_allclose(net.evolve(z,s,[37])[0],expected,atol=1e-16)

    def test_constant_load_semigroup(self):
        z=initial(7);s=np.full(20,10.)
        once=self.net.evolve(z,s,[93])[0]
        twice=self.net.evolve(self.net.evolve(z,s,[31])[0],s,[62])[0]
        np.testing.assert_allclose(once,twice,atol=1e-16)

    def test_decay_modes_and_retained_uniform_mode(self):
        self.assertLessEqual(self.net.rates.max(),0)
        self.assertEqual(np.count_nonzero(self.net.rates==0),1)
        z=np.tile([0,.002],(20,1))
        np.testing.assert_allclose(self.net.evolve(z,np.zeros(20),[5000])[0],z,atol=1e-16)

    def test_elastic_jump_work_equals_energy_change(self):
        z=initial(9);s0=np.zeros(20);s1=np.full(20,10.)
        jump=self.net.gamma(z,s1)-self.net.gamma(z,s0)
        work=np.sum((s0+s1)*jump/2)
        self.assertAlmostEqual(work,float(self.net.energy(z,s1)-self.net.energy(z,s0)),places=13)

    def test_continuous_work_energy_dissipation_identity(self):
        z=initial(6);z[:,0]=np.linspace(-.001,.001,20);s=np.full(20,10.);f=self.net.rhs(z,s);h=.0001
        derivative=(self.net.energy(z+h*f,s)-self.net.energy(z-h*f,s))/(2*h)
        gdot=f.sum(axis=1)@self.net.b.T
        power=np.sum(s*gdot-self.net.ek*f[:,0]**2-self.net.em*f[:,1]**2)
        self.assertAlmostEqual(float(derivative),float(power),places=10)

    def test_unloaded_energy_decreases(self):
        z=initial(7);states=self.net.evolve(z,np.zeros(20),np.arange(0,301,10))
        self.assertTrue(np.all(np.diff(self.net.energy(states,np.zeros(20)))<=1e-12))
        self.assertLess(energy_control(self.net,z)['max_budget_error'],1e-10)

    def test_independent_solvers_resolve_load_jumps(self):
        net=ClayNetwork(self.m,operators([[1],[0]])[1]);z=initial(9,2);expected,strain,_=path(net,z)
        for method in ('DOP853','Radau'):
            actual,g=adaptive(net,z,method)
            np.testing.assert_allclose(actual,expected,atol=1e-10,rtol=1e-9)
            np.testing.assert_allclose(g,strain,atol=1e-10,rtol=1e-9)

    def test_fixed_design_and_saved_accuracy(self):
        d=json.loads((ROOT/'clay_sims_results.json').read_text());cfg=protocol()
        self.assertEqual(d['main_runs'],384);self.assertEqual(d['uncoupled_runs'],128);self.assertTrue(d['accuracy_gates_passed'])
        for name in cfg['graphs']:
            for s in cfg['material_rows_stress_Pa']:
                rows=[r for r in d['runs'] if r['graph']==name and r['stress_Pa']==s]
                self.assertEqual([r['seed'] for r in rows],cfg['seeds'])
                for row in rows:
                    np.testing.assert_array_equal(row['initial_retained_strain'],initial(row['seed'])[:,1])

    def test_reproduction_rejects_changed_outcomes_and_failed_gates(self):
        d=json.loads((ROOT/'clay_sims_results.json').read_text());other=copy.deepcopy(d)
        other['runs'][0]['final_mean_strain']+=.001
        self.assertFalse(reproduction_check(d,other))
        other=copy.deepcopy(d);other['controls'][0]['independent_solvers'][0]['max_strain_error']=1
        self.assertFalse(reproduction_check(d,other))


if __name__=='__main__':unittest.main()
