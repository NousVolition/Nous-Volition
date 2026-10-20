"""A breathable clay 'hug' around a forced 2D Navier-Stokes fluid.

Model only. The 2D incompressible Navier-Stokes equation (vorticity form,
pseudo-spectral, periodic box [0, 2pi)^2, 2/3 dealiasing, RK2/Heun) is the
engine for a SIMS-style metaphor:
  - hug wall: an elliptic ring, Brinkman penalization -K*g*chi*u (K = 1/eta);
  - clay integrity g in [0, 1]: yields where the fluid moves fast through the
    wall, recovers toward 1 where it does not (smooth tanh switch);
  - anxiety: steady, divergence-free swirl-cell forcing confined inside the ring;
  - push: a fading jet P*exp(-t/tau) inside the ring, aimed at the wall;
  - dye: c = 1 inside at t = 0, advected with small diffusion.
It is 2D, has a wall and forcing, so it is not the Clay problem setup and says
nothing about it. Labels describe this model, not real people.
"""
from dataclasses import dataclass, asdict
import numpy as np

LEAK_BREAK = 0.2       # break if final leak fraction exceeds this ...
INTEGRITY_BREAK = 0.1  # ... or wall integrity ever drops below this
RECOVERED = 0.9        # recovered: dipped below 0.9, back above 0.9 at end


@dataclass
class Params:
    n: int = 64
    nu: float = 0.01          # viscosity
    kappa: float = 0.002      # dye diffusion
    dt: float = 0.005
    t_end: float = 30.0
    stiffness: float = 25.0   # K = 1/eta, the hug pushback
    anxiety: float = 0.1      # A
    push: float = 0.0         # P
    push_tau: float = 1.5
    ring_a: float = 1.6       # ellipse semiaxes (wall centreline)
    ring_b: float = 1.3
    wall_half: float = 0.12   # wall half-thickness, in normalised radius
    edge: float = 0.05        # tanh edge width, in normalised radius
    yield_speed: float = 0.25 # clay yields where wall speed exceeds this
    yield_width: float = 0.05 # smoothness of the yield switch
    yield_rate: float = 2.0
    recover_rate: float = 0.25
    noise: float = 1e-3       # seeded initial vorticity noise
    seed: int = 0


def push_amplitude(p, t):
    """The drug/shock burst: smooth in t, fades to zero."""
    return p.push*np.exp(-t/p.push_tau)


def update_integrity(g, speed, p, dt):
    """Exact step of dg/dt = -a(s) g + b(s) (1 - g), with
    a = yield_rate*S, b = recover_rate*(1-S), S = (1+tanh((s-s_y)/w))/2.
    The exact solution relaxes toward b/(a+b) in [0, 1], so g never leaves
    [0, 1]: clay yields where it is pushed through, recovers where it is not."""
    s = 0.5*(1 + np.tanh((speed - p.yield_speed)/p.yield_width))
    a, b = p.yield_rate*s, p.recover_rate*(1 - s)
    g_eq = b/(a + b)
    return g_eq + (g - g_eq)*np.exp(-(a + b)*dt)


def shelter_forcing(X, Y, rho, kx, ky):
    """Shared by both shelters. Anxiety: divergence-free swirl cells from a
    stream function, confined well inside (rho < 0.7). Push: Gaussian jet
    bump at x = +0.6 (force along +x, toward the right-hand wall)."""
    inner = 0.5*(1 - np.tanh((rho - 0.7)/0.1))
    ph = np.fft.fft2(inner*np.sin(2*X)*np.sin(2*Y))
    anx_x = np.real(np.fft.ifft2(1j*ky*ph))
    anx_y = np.real(np.fft.ifft2(-1j*kx*ph))
    return anx_x, anx_y, np.exp(-((X - 0.6)**2 + Y**2)/0.35**2)


class HugSim:
    def __init__(self, p):
        self.p, n = p, p.n
        x = 2*np.pi*np.arange(n)/n
        self.X, self.Y = np.meshgrid(x - np.pi, x - np.pi, indexing="ij")
        k = np.fft.fftfreq(n, 1.0/n)
        self.kx, self.ky = k[:, None], k[None, :]
        self.k2 = self.kx**2 + self.ky**2
        self.k2inv = np.where(self.k2 > 0, 1.0/np.where(self.k2 > 0, self.k2, 1), 0)
        self.mask = (np.abs(self.kx) < n/3) & (np.abs(self.ky) < n/3)
        rho = np.sqrt((self.X/p.ring_a)**2 + (self.Y/p.ring_b)**2)
        w, e = p.wall_half, p.edge
        self.rho = rho
        self.chi = 0.5*(np.tanh((rho - (1 - w))/e) - np.tanh((rho - (1 + w))/e))
        self.wall = self.chi > 0.5
        self.outside = rho > 1 + w
        self.anx_x, self.anx_y, self.push_bump = shelter_forcing(
            self.X, self.Y, rho, self.kx, self.ky)
        rng = np.random.default_rng(p.seed)
        self.w_hat = np.fft.fft2(p.noise*rng.standard_normal((n, n)))*self.mask
        c0 = 0.5*(1 - np.tanh((rho - (1 - w - e))/e))
        self.c_hat = np.fft.fft2(c0)
        self.dye_total = c0.sum()
        self.g = np.ones((n, n))
        self.t = 0.0

    def velocity(self, w_hat):
        psi = w_hat*self.k2inv          # -lap(psi) = omega
        return (np.real(np.fft.ifft2(1j*self.ky*psi)),
                np.real(np.fft.ifft2(-1j*self.kx*psi)))

    def wall_force(self, u, v, g=None):
        """Brinkman penalization force -K g chi u in velocity space."""
        drag = self.p.stiffness*(self.g if g is None else g)*self.chi
        return -drag*u, -drag*v

    def forcing(self, t):
        a, b = self.p.anxiety, push_amplitude(self.p, t)
        return a*self.anx_x + b*self.push_bump, a*self.anx_y

    def rhs(self, w_hat, c_hat, t):
        p, f2, f2i = self.p, np.fft.fft2, np.fft.ifft2
        u, v = self.velocity(w_hat)
        wx = np.real(f2i(1j*self.kx*w_hat))
        wy = np.real(f2i(1j*self.ky*w_hat))
        fx, fy = self.forcing(t)
        px, py = self.wall_force(u, v)
        curl = 1j*self.kx*f2(fy + py) - 1j*self.ky*f2(fx + px)   # curl of force
        dw = (-f2(u*wx + v*wy) + curl)*self.mask - p.nu*self.k2*w_hat
        c = np.real(f2i(c_hat))
        dc = -(1j*self.kx*f2(u*c) + 1j*self.ky*f2(v*c))*self.mask \
            - p.kappa*self.k2*c_hat                       # conservative form
        return dw, dc

    def step(self):
        dt, t = self.p.dt, self.t
        a1, b1 = self.rhs(self.w_hat, self.c_hat, t)
        a2, b2 = self.rhs(self.w_hat + dt*a1, self.c_hat + dt*b1, t + dt)
        self.w_hat = self.w_hat + 0.5*dt*(a1 + a2)
        self.c_hat = self.c_hat + 0.5*dt*(b1 + b2)
        u, v = self.velocity(self.w_hat)
        self.g = update_integrity(self.g, np.hypot(u, v), self.p, dt)
        self.t = t + dt

    def energy(self):
        u, v = self.velocity(self.w_hat)
        return 0.5*np.mean(u*u + v*v)

    def leak_fraction(self):
        c = np.real(np.fft.ifft2(self.c_hat))
        return float(c[self.outside].sum()/self.dye_total)

    def min_integrity(self):
        return float(self.g[self.wall].min())

    def max_wall_speed(self):
        u, v = self.velocity(self.w_hat)
        return float(np.hypot(u, v)[self.wall].max())


def classify(leak_final, min_g, g_end):
    broke = leak_final > LEAK_BREAK or min_g < INTEGRITY_BREAK
    yielded = min_g < RECOVERED
    recovered = yielded and g_end > RECOVERED
    if broke:
        label = "break+heal" if recovered else "break"
    elif yielded:
        label = "bend+recover" if recovered else "bent"
    else:
        label = "hold"
    return broke, recovered, label


def run(p, sample_every=0.25):
    sim = HugSim(p)
    steps = int(round(p.t_end/p.dt))
    every = max(1, int(round(sample_every/p.dt)))
    history, min_g = [], 1.0
    for i in range(1, steps + 1):
        sim.step()
        min_g = min(min_g, sim.min_integrity())
        if i % every == 0 or i == steps:
            history.append(dict(t=round(sim.t, 6), leak=sim.leak_fraction(),
                                min_integrity=sim.min_integrity(),
                                energy=float(sim.energy()),
                                wall_speed=sim.max_wall_speed()))
    last = history[-1]
    if not np.isfinite(last["energy"]):
        raise FloatingPointError(f"run blew up: {asdict(p)}")
    broke, recovered, label = classify(last["leak"], min_g, last["min_integrity"])
    return dict(params=asdict(p), leak_final=last["leak"],
                leak_max=max(h["leak"] for h in history),
                min_integrity=min_g, integrity_end=last["min_integrity"],
                peak_wall_speed=max(h["wall_speed"] for h in history),
                broke=broke, recovered=recovered, label=label, history=history)
