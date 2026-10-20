"""Checks for materials.py (real-fluid table + mapping onto the fluid shelter). Model only."""
import re, sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fluid_shelter import FluidParams, FluidShelter, FOG_EXCESS, run as fluid_run
from materials import (ALL, SOURCES, AIR, WATER, HARD_WATER, H2O2_100, H2O2_3, HELIUM, CO2,
                       SMOKE_COOL, SMOKE_HOT, MaterialShelter, pair_params, hard_water, run)

QUICK = dict(n=48)


@pytest.mark.parametrize("key", list(ALL))
def test_every_material_has_a_cited_source(key):
    m = ALL[key]
    assert m.source.strip()
    cited = [k for k in SOURCES if re.search(rf"\b{k}\b", m.source)]
    assert cited or m.source.startswith("estimate"), m.source
    assert all(v > 0 for v in (m.density, m.viscosity)) and m.sigma_air >= 0
    for lo, hi in [r for r in (m.density_range, m.viscosity_range) if r]:
        assert lo <= hi


def test_hard_water_differs_from_pure_water_by_under_one_percent():
    for hd in (120.0, 180.0, 250.0):
        m = hard_water(hd)
        drho, dmu = m.density/WATER.density - 1, m.viscosity/WATER.viscosity - 1
        assert 0 < drho < 0.01 and 0 < dmu < 0.01
    assert abs(HARD_WATER.density/WATER.density - 1) < 1e-3     # ~0.02 % at 180 mg/L
    assert abs(H2O2_3.density/WATER.density - 1) < 0.02         # household 3 % ~ water


def test_parameter_mapping_gives_expected_ratios():
    p = pair_params(H2O2_100, AIR, push=10.0)
    assert p.rho_ratio == pytest.approx(1450/1.204) and p.scale == 1.0
    assert p.mu_ratio == pytest.approx(1.25e-3/1.81e-5)
    assert p.sigma == pytest.approx(0.0804/0.0728) and p.push == 10.0
    w = pair_params(WATER, AIR)
    assert w.rho_ratio == pytest.approx(829.1, rel=1e-3) and w.mu_ratio == pytest.approx(55.3, rel=1e-2)
    assert w.band_excess == pytest.approx(FOG_EXCESS)
    he = pair_params(WATER, HELIUM, push=5.0, base_sigma=1.0)
    s = HELIUM.density/AIR.density
    assert he.scale == pytest.approx(s) and he.rho_gas == 1.0
    assert he.rho_ratio == pytest.approx(WATER.density/HELIUM.density)
    assert he.push*s == pytest.approx(5.0) and he.sigma*s == pytest.approx(1.0)
    assert he.mu_air*s == pytest.approx(0.01*HELIUM.viscosity/AIR.viscosity)
    sm = pair_params(SMOKE_COOL, AIR)                       # smoke ring: no surface tension
    assert sm.sigma == 0.0 and 1.0 < sm.rho_ratio < 1.001 and sm.mu_ratio == pytest.approx(1.0, abs=1e-5)
    hot = pair_params(SMOKE_HOT, AIR)                       # lighter ring -> ring is rho0 = 1
    assert hot.rho_ratio < 1 and hot.rho_gas*hot.rho_ratio == pytest.approx(1.0)
    for q in (he, hot, pair_params(WATER, CO2)):
        sim = MaterialShelter(replace(q, **QUICK))
        rho, _ = sim.density(sim.phi, sim.fog)
        assert 1.0 - 1e-9 <= rho.min() < 1.01         # Dodd-Ferrante rho0 = 1 <= min density
        assert rho.max() == pytest.approx(max(q.rho_gas, q.rho_gas*q.rho_ratio), rel=1e-2)


def test_water_in_air_reproduces_the_original_fluid_shelter():
    p = pair_params(WATER, AIR, push=10.0, n=32, t_end=0.5)
    base = FluidParams(**{k: getattr(p, k) for k in FluidParams.__dataclass_fields__})
    a, b = run(p), fluid_run(base)
    for x, y in zip(a["history"], b["history"]):
        assert x["leak"] == pytest.approx(y["leak"], rel=1e-9, abs=1e-12)
        assert x["max_speed"] == pytest.approx(y["max_speed"], rel=1e-9)


def test_smoke_ring_leaks_more_than_hard_water_ring_at_same_push():
    hw = run(pair_params(HARD_WATER, AIR, push=10.0, t_end=4.0, **QUICK))
    sm = run(pair_params(SMOKE_COOL, AIR, push=10.0, t_end=4.0, **QUICK))
    print(f"leak hard water {hw['leak_final']:.3f} vs smoke {sm['leak_final']:.3f}")
    assert sm["leak_final"] > 0.1 > hw["leak_final"]
    assert sm["leak_final"] > 5*hw["leak_final"]
    assert sm["min_integrity"] < hw["min_integrity"]


@pytest.mark.parametrize("liq,gas,misc", [(H2O2_100, HELIUM, False), (HARD_WATER, CO2, False),
                                          (SMOKE_COOL, AIR, True), (SMOKE_HOT, AIR, False)])
def test_phase_mass_and_tracers_are_conserved(liq, gas, misc):
    p = pair_params(liq, gas, push=5.0, t_end=0.5, miscible=misc, **QUICK)
    sim = MaterialShelter(p)
    m0, a0, c0, f0 = (1 + sim.phi).sum(), (1 - sim.phi).sum(), sim.c.sum(), sim.fog.sum()
    while sim.t < p.t_end:
        sim.step()
    assert abs((1 + sim.phi).sum() - m0) < 1e-9*m0
    assert abs((1 - sim.phi).sum() - a0) < 1e-9*a0
    assert abs(sim.c.sum() - c0) < 1e-9*c0 and abs(sim.fog.sum() - f0) < 1e-9*f0
