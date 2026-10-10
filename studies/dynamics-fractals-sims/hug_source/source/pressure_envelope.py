"""A pressure-gated, mirrored enclosure with a slowly relaxing shape memory.

This deliberately small prescribed-response model is not calibrated to clay.
It does not solve fluid flow, wall stress, mass transport, or physical fracture.
Pressure difference is imposed externally and must be nonnegative here.
The normalized opening limit is a chosen parameter, not a measured strength.
"""
from dataclasses import dataclass, field
import math

from hug_envelope import arm_points, smoothstep


@dataclass
class PressureEnvelope:
    pressure_limit: float = 1.0
    imprint: float = field(default=0.0, init=False)
    elapsed: float = field(default=0.0, init=False)
    opening_age: float | None = field(default=None, init=False)

    def __post_init__(self):
        if not math.isfinite(self.pressure_limit) or self.pressure_limit <= 0:
            raise ValueError('Opening pressure limit must be finite and positive.')

    def step(self, pressure_difference, dt, points=65):
        """Hold pressure constant for dt seconds, then return the shape.

        m'=(p-m)/tau is solved exactly within a step; p is pressure / limit.
        Loading time is .8 s, recovery time 6 s. Small periodic axis changes
        depend on m: a simple, fading imprint with a breathing motion.
        Reciprocal axis scales preserve the closed ellipse's area. This
        is a chosen geometry rule, not an incompressible-fluid simulation.
        Opening is latched once p >= 1 and completes smoothly in .8 s.
        Lowering pressure does not automatically rejoin an opened envelope.
        """
        if not all(math.isfinite(x) and x >= 0 for x in (pressure_difference, dt)):
            raise ValueError('Pressure difference and elapsed time must be finite and nonnegative.')
        p = pressure_difference/self.pressure_limit
        tau = .8 if p > self.imprint else 6.0
        self.imprint = p + (self.imprint-p)*math.exp(-dt/tau)
        self.elapsed += dt
        if p >= 1.0 and self.opening_age is None:
            self.opening_age = 0.0
        if self.opening_age is not None:
            self.opening_age += dt
        bend = 1.0 if self.opening_age is None else 1.0-smoothstep(self.opening_age/.8)
        sx = 1.0+self.imprint*(.04+.02*math.sin(2.0*math.pi*self.elapsed/3.0))
        sy = 1.0/sx
        norm, entropy = arm_points(bend, sx, sy, points)
        gap = entropy[0][0]-norm[0][0]
        return dict(pressure_ratio=p, imprint=self.imprint, elapsed=self.elapsed, opening_age=self.opening_age,
                    opening_triggered=self.opening_age is not None,
                    connected=gap <= 1e-12, endpoint_gap=gap, bend=bend,
                    eigenvalues=[sx,sy], eigenvectors=[[1.,0.],[0.,1.]],
                    Norm=norm, Entropy=entropy)
