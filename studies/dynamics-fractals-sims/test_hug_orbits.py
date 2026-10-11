"""Direct Hug geometry, recovery, work and orbit-input checks."""
import copy
import json
import unittest
import numpy as np
from hug_orbits import (ROOT,protocol,cases,trajectory,convolution,outline,area,gates_pass,
                        reproduction_check,clay,hug_geometry)
from orbits import uniform_path


class HugOrbitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.saved=json.loads((ROOT/'hug_orbit_results.json').read_text())

    def test_complete_paired_design(self):
        self.assertEqual(self.saved['main_hug_trajectories'],28)
        self.assertEqual(self.saved['independent_Radau_controls'],28)
        self.assertEqual(self.saved['additional_sims_runs'],0)
        for m in clay.materials():
            r=[x for x in self.saved['runs'] if x['material_row_stress_Pa']==m['stress_Pa']]
            self.assertEqual([(x['case'],x['e']) for x in r],cases())
            for row in r:self.assertEqual(list(zip(row['time'],row['side'])),clay.sample_times())

    def test_saved_accuracy_and_geometry_gates(self):
        self.assertTrue(self.saved['accuracy_gates_passed']);self.assertTrue(gates_pass(self.saved))
        for r in self.saved['runs']:
            self.assertEqual(r['geometry_checks']['checked_outline_states'],2*len(clay.sample_times()))
            self.assertEqual(r['geometry_checks']['max_join_gap'],0)

    def test_zero_strain_is_the_original_closed_hug(self):
        np.testing.assert_array_equal(outline(0),hug_geometry.arm_points(1,points=65))

    def test_both_joins_remain_closed_through_actual_trajectories(self):
        for r in self.saved['runs']:
            for s in r['snapshots']:
                for key in ('actual_arms','display_arms'):
                    a,b=s[key]
                    self.assertEqual(a[0],b[0]);self.assertEqual(a[-1],b[-1])

    def test_area_is_preserved_for_both_shear_directions(self):
        original=area(outline(0))
        for r in self.saved['runs']:
            for mag in (1,200):
                for sign in (-1,1):
                    self.assertAlmostEqual(area(outline(sign*r['maximum_sampled_strain'],mag)),original,places=12)

    def test_inverse_shear_recovers_original_outline(self):
        original=np.array(outline(0))
        for g in (-.008,.003,.008):
            for mag in (1,200):
                actual=np.array(outline(g,mag));actual[...,0]-=mag*g*actual[...,1]
                np.testing.assert_allclose(actual,original,atol=1e-14,rtol=0)

    def test_display_magnification_is_not_material_strain(self):
        p=np.array(outline(0))
        for r in self.saved['runs']:
            for s in r['snapshots']:
                actual=np.array(s['actual_arms']);display=np.array(s['display_arms'])
                np.testing.assert_allclose(actual[...,0]-p[...,0],s['strain']*p[...,1],atol=1e-14,rtol=0)
                np.testing.assert_allclose(display[...,0]-p[...,0],200*s['strain']*p[...,1],atol=1e-14,rtol=0)
                np.testing.assert_array_equal(actual[...,1],p[...,1])

    def test_all_circular_cases_reduce_to_original_clay_pulse(self):
        for m in clay.materials():
            r=next(x for x in self.saved['runs'] if x['material_row_stress_Pa']==m['stress_Pa'] and x['case']=='Circular control')
            expected=[clay.state_at(m,t,side)['total'] for t,side in clay.sample_times()]
            np.testing.assert_allclose(r['total_strain'],expected,atol=1e-12,rtol=0)

    def test_20_pa_direct_hug_matches_previous_orbit_sims_mean(self):
        for r in self.saved['runs']:
            if r['material_row_stress_Pa']!=20:continue
            z,p=uniform_path(r['e']);g=p/24000+z.sum(axis=-1)
            np.testing.assert_allclose(r['total_strain'],g,atol=1e-12,rtol=0)

    def test_load_jumps_change_elastic_strain_only(self):
        grid=clay.sample_times()
        for r in self.saved['runs']:
            gm=next(m['G_M_Pa'] for m in clay.materials() if m['stress_Pa']==r['material_row_stress_Pa'])
            for t in (20.,120.):
                i=grid.index((t,'left'));j=grid.index((t,'right'))
                for key in ('retained_strain','delayed_strain'):self.assertEqual(r[key][i],r[key][j])
                self.assertAlmostEqual(r['total_strain'][j]-r['total_strain'][i],(r['load_Pa'][j]-r['load_Pa'][i])/gm,places=12)

    def test_release_recovery_is_exponential_with_constant_retained_strain(self):
        grid=clay.sample_times();release=grid.index((120.,'right'))
        for r in self.saved['runs']:
            m=next(m for m in clay.materials() if m['stress_Pa']==r['material_row_stress_Pa'])
            t=np.array(r['time']);mask=t>=120
            expected=r['delayed_strain'][release]*np.exp(-(t[mask]-120)*m['G_K_Pa']/m['eta_K_Pa_s'])
            np.testing.assert_allclose(np.array(r['delayed_strain'])[mask],expected,atol=1e-12,rtol=0)
            np.testing.assert_allclose(np.array(r['retained_strain'])[mask],r['retained_strain'][release],atol=1e-14,rtol=0)
            self.assertTrue(np.all(np.diff(np.array(r['total_strain'])[mask])<=1e-14))

    def test_equal_impulse_retains_same_mean_within_each_material_row(self):
        for r in self.saved['runs']:
            m=next(m for m in clay.materials() if m['stress_Pa']==r['material_row_stress_Pa'])
            self.assertAlmostEqual(r['final_retained_strain'],m['stress_Pa']*100/m['eta_M_Pa_s'],places=12)
            self.assertGreater(r['final_total_strain'],r['final_retained_strain'])

    def test_independent_convolution_for_eccentric_40_pa_case(self):
        r=next(x for x in self.saved['runs'] if x['material_row_stress_Pa']==40 and x['case']=='Pasiphae')
        m=clay.materials()[-1];grid=clay.sample_times()
        for t in (35.,70.,120.,420.):
            i=grid.index((t,'right'));actual=[r['delayed_strain'][i],r['retained_strain'][i]]
            np.testing.assert_allclose(actual,convolution(m,r['e'],t),atol=1e-10,rtol=0)

    def test_work_energy_and_elastic_jump_accounting(self):
        for r in self.saved['runs']:
            m=next(m for m in clay.materials() if m['stress_Pa']==r['material_row_stress_Pa']);energy=r['energy']
            self.assertGreater(energy['jump_work_on_J_m3'],0);self.assertLess(energy['jump_work_off_J_m3'],0)
            self.assertAlmostEqual(energy['jump_work_on_J_m3']+energy['jump_work_off_J_m3'],0,places=12)
            self.assertAlmostEqual(energy['final_stored_energy_J_m3'],.5*m['G_K_Pa']*r['delayed_strain'][-1]**2,places=12)
            self.assertAlmostEqual(energy['total_work_J_m3']-energy['dissipation_J_m3'],energy['final_stored_energy_J_m3'],places=9)

    def test_independent_solvers_for_eccentric_input(self):
        m=clay.materials()[-1];a,p,_=trajectory(m,.412);b,q,_=trajectory(m,.412,'Radau')
        np.testing.assert_array_equal(p,q);np.testing.assert_allclose(a,b,atol=1e-9,rtol=0)

    def test_reproduction_rejects_changed_response_and_failed_geometry(self):
        d=self.saved;other=copy.deepcopy(d);other['runs'][0]['final_total_strain']+=.001
        self.assertFalse(reproduction_check(d,other))
        other=copy.deepcopy(d);other['runs'][0]['geometry_checks']['max_join_gap']=.1
        self.assertFalse(reproduction_check(d,other))


if __name__=='__main__':unittest.main()
