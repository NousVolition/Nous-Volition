"""Combined shelter: the real-fluid water layer WITH a clay lining.

Model only. Reuses fluid_shelter.FluidShelter (water/fog/air, Cahn-Hilliard
surface tension, real density ratio 829 in the sweep, real viscosity ratio)
and adds, on the INNER side of the water (between the anxious air core and
the water), the clay wall of hug_breakdown: a Brinkman lining -K g chi u
(an acceleration, as in the clay model) whose integrity g yields/recovers by
hug_breakdown.update_integrity with the clay model's yield speed and rates.
Shelter integrity = max(ring closure, lining min g): the shelter counts as
open only where BOTH layers are open. Not the Clay problem; not about people.
"""
from dataclasses import dataclass, asdict
import numpy as np
import fluid_shelter
from fluid_shelter import FluidParams, FluidShelter
from hug_breakdown import Params as ClayParams, update_integrity, classify

CLAY = ClayParams()   # yield speed/width/rates copied from the clay defaults


@dataclass
class CombinedParams(FluidParams):
    stiffness: float = 25.0              # lining K = 1/eta
    lining_half: float = 0.08            # lining half-thickness, normalised radius
    lining_edge: float = 0.05
    yield_speed: float = CLAY.yield_speed
    yield_width: float = CLAY.yield_width
    yield_rate: float = CLAY.yield_rate
    recover_rate: float = CLAY.recover_rate


class CombinedShelter(FluidShelter):
    def __init__(self, p):
        super().__init__(p)
        r0, w, e = 1 - p.layer, p.lining_half, p.lining_edge   # inner water edge
        self.chi = 0.5*(np.tanh((self.rho_n - (r0 - w))/e) - np.tanh((self.rho_n - (r0 + w))/e))
        self.lining = self.chi > 0.5
        self.g = np.ones_like(self.chi)

    def extra_accel(self, u, v):
        drag = self.p.stiffness*self.g*self.chi
        return -drag*u, -drag*v

    def step(self):
        super().step()
        self.g = update_integrity(self.g, self.speed(), self.p, self.last_dt)

    def lining_g(self):
        return float(self.g[self.lining].min())

    def diagnostics(self):
        return dict(lining_g=self.lining_g())


def run(p, **kw):
    r = fluid_shelter.run(p, sim_cls=CombinedShelter, **kw)
    h = r["history"]
    shelter = [max(x["integrity"], x["lining_g"]) for x in h]
    broke, recovered, label = classify(h[-1]["leak"], min(shelter), shelter[-1])
    ring_min, ring_end = r["min_integrity"], h[-1]["integrity"]
    r.update(ring_closure_min=ring_min, ring_closure_end=ring_end,
             ring_reclosed=ring_min < 0.9 and ring_end > 0.9,
             lining_g_min=min(x["lining_g"] for x in h), lining_g_end=h[-1]["lining_g"],
             shelter_min=min(shelter), shelter_end=shelter[-1],
             broke=broke, recovered=recovered, label=label, params=asdict(p))
    r["lining_healed"] = r["lining_g_min"] < 0.9 and r["lining_g_end"] > 0.9
    return r
