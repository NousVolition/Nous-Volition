"""Checks for the combined water + clay-lining shelter (model only)."""
import sys
from dataclasses import replace, asdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fluid_shelter
from combined_shelter import CombinedParams, CombinedShelter, run
from fluid_shelter import FluidParams

QUICK = CombinedParams(n=48, t_end=2.0, rho_ratio=10.0, stiffness=60.0)


def test_lining_integrity_stays_in_unit_interval_and_yields():
    sim = CombinedShelter(replace(QUICK, push=20.0, stiffness=8.0))
    while sim.t < 2.0:
        sim.step()
        assert sim.g.min() >= 0.0 and sim.g.max() <= 1.0
    assert sim.lining_g() < 0.9          # the push really stressed the lining


def test_zero_stiffness_reproduces_fluid_only_model():
    p = replace(QUICK, n=32, t_end=0.5, push=10.0, stiffness=0.0)
    fluid = fluid_shelter.run(FluidParams(**{k: v for k, v in asdict(p).items()
                                             if k in FluidParams.__dataclass_fields__}))
    comb = run(p)
    strip = lambda h: [{k: v for k, v in x.items() if k != "lining_g"} for x in h]
    assert strip(comb["history"]) == fluid["history"]


def test_lining_reduces_leak_at_a_breaking_push():
    p = replace(QUICK, push=20.0, t_end=6.0)
    water = run(replace(p, stiffness=0.0))
    lined = run(p)
    assert water["leak_final"] > 0.2
    assert lined["leak_final"] < 0.5*water["leak_final"]


def test_phase_mass_conserved_with_lining():
    sim = CombinedShelter(replace(QUICK, push=20.0, t_end=1.0))
    water0, dye0 = (1 + sim.phi).sum(), sim.c.sum()
    while sim.t < 1.0:
        sim.step()
    assert abs((1 + sim.phi).sum() - water0) < 1e-9*water0
    assert abs(sim.c.sum() - dye0) < 1e-9*dye0
