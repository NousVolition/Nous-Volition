"""Checks for the water/fog/air 'fluid shelter' model (model only)."""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fluid_shelter import FluidParams, FluidShelter, run

QUICK = FluidParams(n=48, t_end=2.0, rho_ratio=10.0)


def advance(p):
    sim = FluidShelter(p)
    while sim.t < p.t_end - 1e-9:
        sim.step()
    return sim


def test_phase_field_stays_bounded_under_a_hard_push():
    r = run(replace(QUICK, push=20.0, sigma=1.0))
    assert max(h["phi_max"] for h in r["history"]) < 1.1


def test_mass_of_each_phase_and_tracer_is_conserved():
    p = replace(QUICK, push=20.0, sigma=1.0, t_end=1.0)
    sim = FluidShelter(p)
    water0, air0 = (1 + sim.phi).sum(), (1 - sim.phi).sum()
    dye0, fog0 = sim.c.sum(), sim.fog.sum()
    while sim.t < p.t_end:
        sim.step()
    assert abs((1 + sim.phi).sum() - water0) < 1e-9*water0
    assert abs((1 - sim.phi).sum() - air0) < 1e-9*air0
    assert abs(sim.c.sum() - dye0) < 1e-9*dye0
    assert abs(sim.fog.sum() - fog0) < 1e-9*fog0


def test_velocity_stays_divergence_free():
    sim = advance(replace(QUICK, push=20.0, t_end=0.5))
    div = np.fft.ifft2(1j*(sim.kx*sim.uh + sim.ky*sim.vh))
    assert np.max(np.abs(div)) < 1e-10*max(sim.speed().max(), 1e-12)


def test_still_circular_drop_stays_near_rest():
    p = replace(QUICK, shape="drop", ring_a=1.2, ring_b=1.2, anxiety=0.0, push=0.0,
                noise=0.0, sigma=1.0, t_end=3.0)
    sim = advance(p)
    spurious = sim.speed().max()
    print(f"spurious current max |u| = {spurious:.2e} (sigma=1, rho ratio 10)")
    assert spurious < 2e-2           # capillary speed scale sigma/mu_water ~ 1.8


def test_without_surface_tension_the_shelter_mixes_more():
    p = replace(QUICK, push=5.0, t_end=8.0)
    loose = advance(replace(p, sigma=0.0))
    held = advance(replace(p, sigma=3.0))
    assert loose.leak_fraction() > 0.1 > 10*held.leak_fraction()
    assert loose.thinnest_sector() < held.thinnest_sector() - 0.3
    assert loose.interface_length() > held.interface_length()


def test_runs_are_deterministic_for_fixed_seed():
    p = replace(QUICK, n=32, t_end=0.5, push=10.0, noise=0.05)
    a, b = run(replace(p, seed=7)), run(replace(p, seed=7))
    c = run(replace(p, seed=8))
    assert a["history"] == b["history"]
    assert a["history"] != c["history"]
