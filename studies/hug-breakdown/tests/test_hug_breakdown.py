"""Checks for the 2D Navier-Stokes hug-breakdown model (model only)."""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hug_breakdown import HugSim, Params, push_amplitude, run, update_integrity, classify

QUICK = Params(n=48, t_end=6.0)


def test_velocity_from_streamfunction_is_divergence_free():
    sim = HugSim(replace(QUICK, noise=1.0, seed=3))
    u, v = sim.velocity(sim.w_hat)
    div = np.fft.ifft2(1j*sim.kx*np.fft.fft2(u) + 1j*sim.ky*np.fft.fft2(v))
    assert np.max(np.abs(div)) < 1e-10*np.max(np.abs(u))


def test_unforced_no_wall_energy_decays_viscously():
    p = replace(QUICK, stiffness=0.0, anxiety=0.0, push=0.0, noise=0.5, nu=0.02)
    sim = HugSim(p)
    energies = [sim.energy()]
    for _ in range(300):
        sim.step()
        energies.append(sim.energy())
    assert np.all(np.diff(energies) <= 1e-12)
    assert energies[-1] < 0.9*energies[0]


def test_stiff_wall_without_push_keeps_dye_inside():
    r = run(replace(QUICK, stiffness=60.0, push=0.0))
    assert r["leak_final"] < 0.05
    assert r["label"] == "hold"


def test_without_wall_dye_spreads_out():
    walled = run(replace(QUICK, stiffness=60.0, push=0.0, t_end=15.0))
    open_ = run(replace(QUICK, stiffness=0.0, push=0.0, t_end=15.0))
    assert open_["leak_final"] > 0.2
    assert open_["leak_final"] > 5*walled["leak_final"]


def test_push_fades_away():
    p = replace(QUICK, push=40.0)
    assert push_amplitude(p, 0.0) == 40.0
    assert abs(push_amplitude(p, 50*p.push_tau)) < 1e-12*p.push
    sim = HugSim(p)
    fx_late, _ = sim.forcing(50*p.push_tau)
    fx_none, _ = HugSim(replace(p, push=0.0)).forcing(0.0)
    assert np.max(np.abs(fx_late - fx_none)) < 1e-12


def test_integrity_stays_in_unit_interval_under_hard_push():
    p = replace(QUICK, stiffness=3.0, push=40.0, t_end=3.0)
    sim = HugSim(p)
    for _ in range(int(p.t_end/p.dt)):
        sim.step()
        assert sim.g.min() >= 0.0 and sim.g.max() <= 1.0
    assert sim.min_integrity() < 0.9   # it really was stressed


def test_yield_above_threshold_and_recovery_when_stress_removed():
    p = Params()
    g = np.ones(4)
    high = np.full(4, 4*p.yield_speed)
    for _ in range(400):                       # 2 time units of high stress
        g = update_integrity(g, high, p, 0.005)
    assert g.max() < 0.05
    low = np.full(4, 0.2*p.yield_speed)
    below = update_integrity(np.ones(4), low, p, 0.005)
    assert np.all(below > 0.999)               # below threshold: no yield
    for _ in range(4000):                      # 20 time units without stress
        g = update_integrity(g, np.zeros(4), p, 0.005)
    assert g.min() > 0.99
    assert np.all((g >= 0) & (g <= 1))


def test_classification_rules():
    assert classify(0.01, 0.95, 0.99)[2] == "hold"
    assert classify(0.05, 0.5, 0.95)[2] == "bend+recover"
    assert classify(0.30, 0.5, 0.95)[2] == "break+heal"
    assert classify(0.05, 0.05, 0.2)[2] == "break"


def test_runs_are_deterministic_for_fixed_seed():
    p = replace(QUICK, n=32, t_end=1.0, push=10.0, noise=0.05)
    a, b = run(replace(p, seed=7)), run(replace(p, seed=7))
    c = run(replace(p, seed=8))
    assert a["history"] == b["history"]
    assert a["history"] != c["history"]
