"""Independent analytic and numerical checks for batch 3."""
import math
import unittest
from models import integrate
from oscillations import (radial_rate,radial_field,radial_trajectory,stable_radius,
    gradient,potential,dulac_weighted,selkov,selkov_equilibrium,selkov_hopf_bounds,
    selkov_trap,vdp,vdp_lienard,cubic,duffing,duffing_energy,duffing_period,
    cycle_metrics,upcrossings,undamped_pendulum,pendulum_period,
    cubic_damping,cubic_damping_approx,swing,swing_averaged,planar_pitchfork,hopf_normal_form)


class OscillationTests(unittest.TestCase):
    def test_radial_side_classifications(self):
        for kind,signs in [('stable',(1,-1)),('unstable',(-1,1)),('half_stable',(-1,-1))]:
            self.assertEqual(radial_rate(1,kind),0)
            for radius,sign in zip((.8,1.2),signs):
                self.assertGreater(sign*radial_rate(radius,kind),0)

    def test_cartesian_unit_cycle_closure(self):
        for kind in ('stable','unstable','half_stable'):
            rows = integrate(radial_field(kind),[1,0],2*math.pi,2*math.pi/1000)
            self.assertLess(math.dist(rows[-1][1:],(1,0)),1e-8)

    def test_stable_radius_against_exact(self):
        for radius in (.25,1.5):
            rows = integrate(radial_field('stable'),[radius,0],5,.01)
            error = max(abs(math.hypot(*r[1:])-stable_radius(r[0],radius)) for r in rows)
            self.assertLess(error,2e-8)

    def test_unstable_stop_before_escape(self):
        rows,stopped = radial_trajectory('unstable',1.02)
        self.assertTrue(stopped)
        self.assertLess(math.hypot(*rows[-1][1:]),2)
        t = rows[-1][0]
        exact = 1/math.sqrt(1-(1-1/1.02**2)*math.exp(.2*t))
        self.assertAlmostEqual(math.hypot(*rows[-1][1:]),exact,6)

    def test_gradient_potential_directional_derivative(self):
        for x,y in [(.3,.7),(-1,2),(2,-.2)]:
            dx,dy = gradient(0,(x,y)); h=1e-6
            derivative=(potential(x+h*dx,y+h*dy)-potential(x-h*dx,y-h*dy))/(2*h)
            self.assertAlmostEqual(derivative,-dx*dx-dy*dy,places=7)

    def test_gradient_sampled_potential_decreases(self):
        rows=integrate(gradient,[.5,.7],5,.01)
        vals=[potential(*r[1:]) for r in rows]
        self.assertTrue(all(b<=a+1e-10 for a,b in zip(vals,vals[1:])))

    def test_dulac_divergences_by_finite_differences(self):
        for which,points in [('population',[(.4,.7),(1.5,2),(3,.2)]),
                             ('polynomial',[(-1,.5),(0,0),(1,2)])]:
            for x,y in points:
                h=1e-5
                div=(dulac_weighted(which,x+h,y)[0]-dulac_weighted(which,x-h,y)[0])/(2*h)
                div+=(dulac_weighted(which,x,y+h)[1]-dulac_weighted(which,x,y-h)[1])/(2*h)
                expected=-1/y if which=='population' else -math.exp(-2*x)
                self.assertAlmostEqual(div,expected,places=7)

    def test_dulac_domain_rejects_axes(self):
        for point in [(0,1),(1,0),(-1,1)]:
            with self.assertRaises(ValueError): dulac_weighted('population',*point)

    def test_annulus_trapping_and_nonzero_field(self):
        self.assertGreater(radial_rate(.5,'stable'),0)
        self.assertLess(radial_rate(1.5,'stable'),0)
        for r in (.5,1,1.5):
            for angle in (0,.7,2,4):
                x,y=r*math.cos(angle),r*math.sin(angle)
                dx,dy=radial_field('stable')(0,(x,y))
                self.assertAlmostEqual((x*dy-y*dx)/(r*r),1)

    def test_selkov_equilibrium_and_linearization(self):
        for b in (.2,.5,1):
            a=.1; eq=selkov_equilibrium(a,b); x,y=eq['x'],eq['y']
            self.assertLess(math.hypot(*selkov(a,b)(0,(x,y))),1e-14)
            A=-1+2*x*y; B=a+x*x; C=-2*x*y; D=-B
            self.assertAlmostEqual(eq['trace'],A+D)
            self.assertAlmostEqual(eq['determinant'],A*D-B*C)

    def test_selkov_trace_zero_boundaries(self):
        lo,hi=selkov_hopf_bounds(.1)
        for b in (lo,hi): self.assertAlmostEqual(selkov_equilibrium(.1,b)['trace'],0)
        self.assertEqual(selkov_equilibrium(.1,(lo+hi)/2)['stability'],'repeller')
        for a in (.125,.2,1):
            for b in (.1,.4,.8,2): self.assertLess(selkov_equilibrium(a,b)['trace'],0)

    def test_selkov_polygon_boundary_inward(self):
        for a,b in [(.1,.5),(.2,1)]:
            trap=selkov_trap(a,b); Y,L=trap['Y'],trap['L']; rhs=selkov(a,b)
            for i in range(21):
                fraction=i/20
                self.assertLessEqual(rhs(0,(fraction*(L-Y),Y))[1],-a+1e-12)
                point=(L-Y+fraction*Y,Y*(1-fraction))
                self.assertLessEqual(sum(rhs(0,point)),-1+1e-12)
                self.assertGreaterEqual(rhs(0,(0,fraction*Y))[0],0)
                self.assertGreater(rhs(0,(fraction*L,0))[1],0)

    def test_lienard_coordinate_transformation(self):
        for mu in (.1,1,10):
            for x,v in [(.3,1),(2,-.4),(-1,.7)]:
                y=v/mu+cubic(x)
                dx,dy=vdp_lienard(mu)(0,(x,y))
                dv=vdp(mu)(0,(x,v))[1]
                self.assertAlmostEqual(dx,v)
                self.assertAlmostEqual(dy,dv/mu+(x*x-1)*v)

    def test_lienard_signs_for_vdp(self):
        self.assertAlmostEqual(cubic(math.sqrt(3)),0)
        for x in (.1,.5,1,1.7): self.assertLess(cubic(x),0)
        for x in (1.8,2,10):
            self.assertGreater(cubic(x),0)
            self.assertGreater(x*x-1,0)
        for x in (.2,1,3): self.assertAlmostEqual(cubic(-x),-cubic(x))

    def test_vdp_zero_mu_is_center(self):
        rows=integrate(vdp(0),[.5,0],20,.02)
        self.assertLess(max(abs(math.hypot(*r[1:])-.5) for r in rows),1e-8)

    def test_duffing_conserves_energy(self):
        rows=integrate(duffing(.1),[1.5,0],40,.02)
        energy=duffing_energy(1.5,0,.1)
        self.assertLess(max(abs(duffing_energy(*r[1:],.1)-energy) for r in rows),1e-7)

    def test_duffing_period_from_independent_integral(self):
        periods=[]
        for amplitude in (.5,1.5):
            rows=integrate(duffing(.1),[amplitude,0],80,.02)
            measured=cycle_metrics(rows,after=30)['mean_period']
            exact=duffing_period(amplitude,.1)
            self.assertAlmostEqual(measured,exact,places=5)
            periods.append(exact)
        self.assertLess(periods[1],periods[0])
        self.assertAlmostEqual(duffing_period(1,0),2*math.pi,places=12)

    def test_crossing_interpolation_and_insufficient_cycles(self):
        self.assertEqual(upcrossings([(0,-1,2),(2,1,4)]),[(1,3)])
        self.assertEqual(upcrossings([(0,1,2),(2,-1,4)]),[])
        with self.assertRaises(ValueError): cycle_metrics([(0,-1,2),(2,1,4)])

    def test_pendulum_frequency_correction(self):
        errors=[]
        for amplitude in (.1,.2):
            frequency=2*math.pi/pendulum_period(amplitude)
            self.assertLess(frequency,1)
            errors.append(abs(frequency-(1-amplitude**2/16)))
        self.assertGreater(errors[1]/errors[0],15)
        self.assertLess(errors[1]/errors[0],17)
        rows=integrate(undamped_pendulum,[.8,0],90,.02)
        self.assertAlmostEqual(cycle_metrics(rows,after=40)['mean_period'],pendulum_period(.8),5)

    def test_cubic_damping_energy_identity(self):
        for x,v in [(1,2),(-1,.4),(.2,-.5)]:
            dx,dv=cubic_damping(2)(0,(x,v))
            self.assertAlmostEqual(x*dx+v*dv,-2*v**4)
        self.assertEqual(cubic_damping_approx(0,1,2),1)

    def test_swing_at_rest_stays_at_rest(self):
        for gamma in (0,1):
            rows=integrate(swing(.1,gamma),[0,0],20,.01)
            self.assertTrue(all(r[1:]==(0,0) for r in rows))

    def test_swing_averaged_quadratures_match_supplied_polar_equations(self):
        epsilon=.1; gamma=.3; radius=.4; phase=.7
        A,B=radius*math.cos(phase),-radius*math.sin(phase)
        dA,dB=swing_averaged(epsilon,gamma)(0,(A,B))
        dr=(A*dA+B*dB)/radius
        dphi=(B*dA-A*dB)/radius**2
        self.assertAlmostEqual(dr,epsilon*radius*math.sin(2*phase)/4)
        self.assertAlmostEqual(dphi,epsilon*(gamma+math.cos(2*phase)/2)/2)

    def test_swing_seed_grows_near_parametric_resonance(self):
        rows=integrate(swing(.1,0),[.005,0],120,.02)
        detuned=integrate(swing(.1,1),[.005,0],120,.02)
        self.assertGreater(max(abs(r[1]) for r in rows),.05)
        self.assertLess(max(abs(r[1]) for r in detuned),.015)

    def test_planar_pitchfork_branches(self):
        for sign in (-1,1):
            x=sign*math.sqrt(.5)
            self.assertLess(math.hypot(*planar_pitchfork(.5)(0,(x,0))),1e-14)
            rows=integrate(planar_pitchfork(.5),[sign*.1,.5],40,.02)
            self.assertLess(math.dist(rows[-1][1:],(x,0)),1e-10)

    def test_hopf_cycle_radius_and_origin_persistence(self):
        for mu in (-.5,.5):
            self.assertEqual(hopf_normal_form(mu)(0,(0,0)),(0,0))
            rows=integrate(hopf_normal_form(mu),[.2,0],40,.02)
            target=math.sqrt(mu) if mu>0 else 0
            self.assertAlmostEqual(math.hypot(*rows[-1][1:]),target,7)


if __name__=='__main__':
    unittest.main()
