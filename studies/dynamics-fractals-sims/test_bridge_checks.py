"""Independent analytic or structural checks for the sixth batch."""
import math
import unittest
import numpy as np
from models import integrate
from bridge_checks import (references, reversible, reversible_jacobian, potential,
    potential_rate, diagonal_exact, classify, linear_flow, channel_steady,
    channel_tau, channel_mean, channel_profile, discrete_channel)


class ReversibilityTests(unittest.TestCase):
    def test_vector_field_reverser_identity(self):
        # For R=-I the reversal condition f(Rz)=-R f(z) becomes f(-z)=f(z).
        for x in np.linspace(-3,3,13):
            for y in np.linspace(-3,3,11):
                np.testing.assert_allclose(reversible(0,[-x,-y]),reversible(0,[x,y]),atol=1e-14)

    def test_jacobian_matches_centered_differences(self):
        z=np.array([.37,-1.1]);eps=1e-6
        columns=[(np.array(reversible(0,z+eps*e))-reversible(0,z-eps*e))/(2*eps) for e in np.eye(2)]
        np.testing.assert_allclose(reversible_jacobian(z),np.array(columns).T,atol=3e-10)

    def test_four_fixed_points_and_eigenvalues_per_cell(self):
        for sx,sy,expected in [(-1,-1,[-3,-1]),(1,1,[1,3]),(-1,1,[-math.sqrt(3),math.sqrt(3)]),(1,-1,[-math.sqrt(3),math.sqrt(3)])]:
            point=np.array([sx,sy])*math.pi/2
            np.testing.assert_allclose(reversible(0,point),0,atol=2e-15)
            np.testing.assert_allclose(sorted(np.linalg.eigvals(reversible_jacobian(point))),expected,atol=1e-14)

    def test_global_periodicity(self):
        np.testing.assert_allclose(reversible(0,[.2+2*math.pi,-.7-4*math.pi]),reversible(0,[.2,-.7]),atol=3e-15)

    def test_exact_diagonal_solution_and_fourth_order_error(self):
        errors=[]
        for step in [.04,.02,.01]:
            path=integrate(reversible,[.3,.3],2,step)
            errors.append(max(abs(x-diagonal_exact(t,.3)) for t,x,y in path))
        self.assertTrue(all(12<a/b<20 for a,b in zip(errors,errors[1:])),errors)

    def test_reflected_trajectory_reverses_order(self):
        forward=np.array(integrate(reversible,[.2,.4],1,.005))[:,1:]
        reversed_path=np.array(integrate(reversible,-forward[-1],1,.005))[:,1:]
        np.testing.assert_allclose(reversed_path,-forward[::-1],atol=1e-8,rtol=0)

    def test_potential_derivative_is_strictly_negative_off_equilibria(self):
        mobility=np.array([[2.,1.],[1.,2.]])
        for z in ([.2,.4],[-1.2,-.8],[1.,-2.]):
            grad=np.cos(z)
            np.testing.assert_allclose(reversible(0,z),-mobility@grad,atol=1e-14)
            self.assertAlmostEqual(float(grad@reversible(0,z)),potential_rate(z),places=13)
            self.assertLess(potential_rate(z),0)
            numerical=(potential(np.array(z)+1e-6*np.array(reversible(0,z)))-potential(np.array(z)-1e-6*np.array(reversible(0,z))))/2e-6
            self.assertAlmostEqual(numerical,potential_rate(z),places=8)

    def test_local_attraction_and_area_contraction(self):
        sink=np.array([-math.pi/2]*2)
        for offset in ([.2,0],[0,.2],[-.15,.1]):
            path=np.array(integrate(reversible,sink+offset,8,.01))[:,1:]
            self.assertLess(np.linalg.norm(path[-1]-sink),1e-3*np.linalg.norm(offset))
            self.assertLessEqual(max(np.diff([potential(z) for z in path])),1e-14)
        self.assertAlmostEqual(np.trace(reversible_jacobian(sink)),-4)
        self.assertAlmostEqual(np.trace(reversible_jacobian(-sink)),4)


class LinearTests(unittest.TestCase):
    def test_saved_six_classes_and_zero_mode(self):
        for row in references()['linear_reference']:
            computed=classify(row['matrix'])['classification']
            expected=row['classification']
            if row['name']=='symmetric a=-1,b=1':
                self.assertIn('zero eigenvalue',computed)
            else:
                self.assertEqual(computed,expected)

    def test_exact_rotation_and_spiral_norm(self):
        for damping in [-.2,0,.2]:
            a=[[damping,-1],[1,damping]]
            for t in [0,.7,2,5]:
                expected=math.exp(damping*t)*np.array([math.cos(t),math.sin(t)])
                np.testing.assert_allclose(linear_flow(a,[1,0],t),expected,atol=2e-14)

    def test_repeated_eigenvalue_jordan_block(self):
        a=[[-1,1],[0,-1]]
        for t in [0,.1,2,5]:
            np.testing.assert_allclose(linear_flow(a,[0,1],t),math.exp(-t)*np.array([t,1]),atol=1e-14)
        self.assertEqual(classify(a)['classification'],'stable node')

    def test_reciprocal_modes_and_threshold(self):
        for b in [.5,1,1.5]:
            a=np.array([[-1,b],[b,-1]])
            for v,eigen in [(np.array([1.,1.]),-1+b),(np.array([1.,-1.]),-1-b)]:
                np.testing.assert_allclose(linear_flow(a,v,2),math.exp(eigen*2)*v,atol=1e-14)
        for b in np.linspace(-3,3,31):
            self.assertGreaterEqual(classify([[-1,b],[b,-1]])['discriminant'],0)

    def test_nonnormal_stable_node_can_temporarily_grow(self):
        a=[[-1,10],[0,-2]]
        self.assertEqual(classify(a)['classification'],'stable node')
        expected=np.array([10*(math.exp(-.7)-math.exp(-1.4)),math.exp(-1.4)])
        np.testing.assert_allclose(linear_flow(a,[0,1],.7),expected,atol=1e-14)
        self.assertGreater(np.linalg.norm(expected),2.5)
        self.assertLess(np.linalg.norm(linear_flow(a,[0,1],10)),.001)

    def test_nonlinear_imaginary_linearization_does_not_decide_attraction(self):
        r0=.2
        for sign in [-1,0,1]:
            def rhs(t,z):
                x,y=z;r2=x*x+y*y
                return (-y+sign*x*r2,x+sign*y*r2)
            final=np.array(integrate(rhs,[r0,0],4,.005)[-1][1:])
            exact=r0/math.sqrt(1-2*sign*r0*r0*4)
            self.assertAlmostEqual(np.linalg.norm(final),exact,places=10)

    def test_similarity_and_positive_timescale_preserve_class(self):
        transform=np.array([[1.,2.],[-.2,1.]])
        inverse=np.linalg.inv(transform)
        for a in ([[0,-1],[1,0]],[[-1,1],[0,-2]],[[-.2,-1],[1,-.2]],[[1,0],[0,-1]]):
            for scale in [1e-9,1,1e9]:
                self.assertEqual(classify(scale*transform@np.array(a)@inverse)['classification'],classify(a)['classification'])


class ChannelTests(unittest.TestCase):
    def test_saved_steady_speeds_and_decay_times(self):
        for row in references()['water_channels']:
            self.assertAlmostEqual(channel_steady(row['mu'],row['G_Pam'],row['H_m'])/row['steady_mean_ms'],1,places=13)
            self.assertAlmostEqual(channel_tau(row['rho'],row['mu'],row['H_m'])/row['tau_s'],1,places=13)

    def test_saved_startup_means_against_integrated_fourier_solution(self):
        for row in references()['water_channels']:
            exact=channel_mean(1,row['rho'],row['mu'],row['G_Pam'],row['H_m'])
            self.assertLess(abs(exact/row['mean_velocity_ms']-1),1e-6)

    def test_density_and_viscosity_swaps_have_different_effects(self):
        p=references()['water_properties']['298.15'];h,d=p['H2O'],p['D2O']
        self.assertGreater(channel_tau(d['rho'],h['mu']),channel_tau(h['rho'],h['mu']))
        self.assertLess(channel_tau(h['rho'],d['mu']),channel_tau(h['rho'],h['mu']))
        self.assertLess(channel_steady(d['mu']),channel_steady(h['mu']))
        self.assertAlmostEqual(channel_steady(d['mu'])/channel_steady(h['mu']),h['mu']/d['mu'],places=14)
        for t in [.02,.1]:
            self.assertLess(channel_mean(t,d['rho'],h['mu']),channel_mean(t,h['rho'],h['mu']))

    def test_fourier_solution_obeys_channel_pde_and_boundaries(self):
        rho,mu=997.,.00089;y=np.linspace(.0001,.0009,9);t=.08;eps_t=1e-5;eps_y=1e-7
        ut=(channel_profile(y,t+eps_t,rho,mu)-channel_profile(y,t-eps_t,rho,mu))/(2*eps_t)
        uyy=(channel_profile(y+eps_y,t,rho,mu)-2*channel_profile(y,t,rho,mu)+channel_profile(y-eps_y,t,rho,mu))/eps_y**2
        np.testing.assert_allclose(rho*ut,10+mu*uyy,rtol=2e-6,atol=2e-5)
        np.testing.assert_allclose(channel_profile([0,.001],t,rho,mu),0,atol=1e-18)

    def test_spatial_refinement_matches_continuum(self):
        for p in references()['water_properties']['298.15'].values():
            errors=[]
            for n in [32,64,128]:
                y,u=discrete_channel(p['rho'],p['mu'],n)
                exact=channel_profile(y,.1,p['rho'],p['mu'])
                errors.append(np.linalg.norm(u-exact)/np.linalg.norm(exact))
            self.assertTrue(all(3.5<a/b<4.6 for a,b in zip(errors,errors[1:])),errors)
            self.assertLess(errors[-1],4e-5)

    def test_time_refinement_against_exact_discrete_mode_evolution(self):
        rho,mu,n=997.,.00089,32
        y=np.arange(1,n)/n*.001;k=np.arange(1,n)
        basis=np.sin(np.pi*np.outer(np.arange(1,n),k)/n)
        eigen=-4*(mu/rho)/(.001/n)**2*np.sin(k*np.pi/(2*n))**2
        steady=10*y*(.001-y)/(2*mu)
        exact=steady-basis@(np.exp(eigen*.1)*(2/n*basis.T@steady))
        errors=[]
        for step in [.004,.002,.001]:
            _,u=discrete_channel(rho,mu,n,dt=step)
            errors.append(np.linalg.norm(u[1:-1]-exact))
        self.assertTrue(all(3.8<a/b<4.2 for a,b in zip(errors,errors[1:])),errors)

    def test_pressure_gradient_linearity_and_zero_drive(self):
        for gradient in [0,1,10,100]:
            y,u=discrete_channel(997.,.00089,32,gradient=gradient)
            _,base=discrete_channel(997.,.00089,32,gradient=1)
            np.testing.assert_allclose(u,gradient*base,atol=1e-17)
        self.assertEqual(channel_mean(0,997.,.00089),0)


if __name__=='__main__':
    unittest.main()
