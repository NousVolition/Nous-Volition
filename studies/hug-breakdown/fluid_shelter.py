"""'Fluid shelter': the hug built from real fluids instead of clay.

Model only. Inner air core (the anxious fluid, with dye) is wrapped by a water
layer, then a fog layer, then outside air. Surface tension at the water/air
interfaces is what holds the water layer together. Engine: 2D incompressible,
variable-density, variable-viscosity Navier-Stokes coupled to a Cahn-Hilliard
phase field (phi = +1 water, -1 air), pseudo-spectral on [0, 2pi)^2, 2/3
dealiased, SSP-RK3 time steps:
  - pressure: constant-coefficient projection with extrapolated pressure
    (Dodd & Ferrante 2014 splitting), so the density ratio can be raised;
  - viscosity: div(mu (grad u + grad u^T)) / rho, explicit;
  - surface tension: force lam * mu_c * grad(phi), lam = 3 sigma eps/(2 sqrt 2),
    mu_c = (phi^3 - phi)/eps^2 - lap(phi);
  - Cahn-Hilliard: phi_t + div(u phi) = M lap(mu_c), explicit (M is small).
    The interface is kept by CH even when sigma = 0 (force switched off).
Same anxiety swirl and fading push as the clay model (hug_breakdown.py), as
forces per unit volume (equal to the clay accelerations in air, rho_air = 1).
Real ratios at 20 C (see README): rho_w/rho_a = 829, mu_w/mu_a = 55.4. The
sweep uses the real density ratio; the default rho_ratio = 10 keeps tests fast.
Not the Clay problem (that is 3D, single phase, constant viscosity, no walls).
"""
from dataclasses import dataclass, asdict
import numpy as np
from hug_breakdown import push_amplitude, shelter_forcing, classify

RHO_RATIO_REAL = 998.2/1.204        # water / air density, 20 C
MU_RATIO_REAL = 1.002e-3/1.81e-5    # water / air dynamic viscosity, 20 C
FOG_EXCESS = 0.5e-3/1.204           # thick fog: 0.5 g/m^3 liquid water per air


@dataclass
class FluidParams:
    n: int = 64
    dt: float = 0.004         # max step (CFL-limited below this)
    t_end: float = 25.0
    rho_ratio: float = 10.0   # water/air density ratio (real: 829)
    mu_air: float = 0.01      # = clay-model viscosity in the air core
    mu_ratio: float = MU_RATIO_REAL
    sigma: float = 1.0        # surface tension (nondimensional)
    eps: float = 0.075        # interface width (~0.75 grid cells at n=64)
    mobility: float = 1e-4    # Cahn-Hilliard mobility M
    kappa: float = 0.002      # dye/fog diffusion
    anxiety: float = 0.1
    push: float = 0.0
    push_tau: float = 1.5
    ring_a: float = 1.6
    ring_b: float = 1.3
    layer: float = 0.2        # water half-thickness, normalised radius
    fog: float = 0.2          # fog band width outside the water
    shape: str = "ring"       # "ring" shelter or still "drop" (tests)
    noise: float = 1e-3
    seed: int = 0


class FluidShelter:
    def __init__(self, p):
        self.p, n = p, p.n
        x = 2*np.pi*np.arange(n)/n
        self.X, self.Y = np.meshgrid(x - np.pi, x - np.pi, indexing="ij")
        k = np.fft.fftfreq(n, 1.0/n)
        self.kx, self.ky = k[:, None], k[None, :]
        self.k2 = self.kx**2 + self.ky**2
        self.k2inv = np.where(self.k2 > 0, 1/np.where(self.k2 > 0, self.k2, 1), 0)
        self.mask = (np.abs(self.kx) < n/3) & (np.abs(self.ky) < n/3)
        rho = np.sqrt((self.X/p.ring_a)**2 + (self.Y/p.ring_b)**2)
        self.rho_n, R = rho, 0.5*(p.ring_a + p.ring_b)
        d, h, s = (rho - 1)*R, p.layer*R, np.sqrt(2)*p.eps
        if p.shape == "drop":
            H = 0.5*(1 - np.tanh((rho - 1)*R/s))
        else:
            H = 0.5*(np.tanh((d + h)/s) - np.tanh((d - h)/s))
        self.phi = 2*H - 1
        w = p.layer
        self.c = 0.5*(1 - np.tanh((rho - (1 - w))/0.05)) * (p.shape == "ring")
        self.fog = 0.5*(np.tanh((rho - 1 - w)/0.05) - np.tanh((rho - 1 - w - p.fog)/0.05))
        self.outside = rho > 1 + w
        self.anx_x, self.anx_y, self.push_bump = shelter_forcing(
            self.X, self.Y, rho, self.kx, self.ky)
        rng = np.random.default_rng(p.seed)
        z = np.fft.fft2(p.noise*rng.standard_normal((n, n)))*self.mask*self.k2inv
        self.uh, self.vh = 1j*self.ky*z, -1j*self.kx*z      # divergence-free noise
        self.p_hat = np.zeros((n, n), complex)
        theta = np.arctan2(self.Y/p.ring_b, self.X/p.ring_a)
        self.bins = ((theta + np.pi)/(2*np.pi)*48).astype(int) % 48
        self.band = rho < 1.9
        self.bin_water0 = self.bin_water()
        self.t = 0.0

    def d(self, fh, axis):
        return np.real(np.fft.ifft2(1j*(self.kx if axis == 0 else self.ky)*fh))

    def fields(self, st):
        return [np.real(np.fft.ifft2(q)) for q in st]

    def density(self, phi, fog):
        H = np.clip((1 + phi)/2, 0, 1)
        return 1 + (self.p.rho_ratio - 1)*H + FOG_EXCESS*fog*(1 - H), H

    def rhs(self, st, t):
        """Time derivative of the spectral state (u, v, phi, dye, fog)."""
        p, f2 = self.p, np.fft.fft2
        uh, vh, ph, ch, fh = st
        u, v, phi, c, fog = self.fields(st)
        rho, H = self.density(phi, fog)
        mu = p.mu_air*(1 + (p.mu_ratio - 1)*H)
        ux, uy, vx, vy = self.d(uh, 0), self.d(uh, 1), self.d(vh, 0), self.d(vh, 1)
        sxx, sxy, syy = f2(2*mu*ux), f2(mu*(uy + vx)), f2(2*mu*vy)
        visc_x, visc_y = self.d(sxx, 0) + self.d(sxy, 1), self.d(sxy, 0) + self.d(syy, 1)
        lam = 3*p.sigma*p.eps/(2*np.sqrt(2))
        mu_c = (phi**3 - phi)/p.eps**2 + np.real(np.fft.ifft2(self.k2*ph))
        gx, gy = self.d(ph, 0), self.d(ph, 1)
        a, b = p.anxiety, push_amplitude(p, t)
        fx, fy = a*self.anx_x + b*self.push_bump, a*self.anx_y
        corr = 1/rho - 1.0                       # rho0 = rho_air = 1 (Dodd-Ferrante)
        px, py = self.d(self.p_hat, 0), self.d(self.p_hat, 1)   # lagged pressure
        ex, ey = self.extra_accel(u, v)                          # hook (0 here)
        rx = f2(-(u*ux + v*uy) + (visc_x + lam*mu_c*gx + fx)/rho - corr*px + ex)*self.mask
        ry = f2(-(u*vx + v*vy) + (visc_y + lam*mu_c*gy + fy)/rho - corr*py + ey)*self.mask
        self.p_hat = -1j*(self.kx*rx + self.ky*ry)*self.k2inv    # pressure / rho0
        div = lambda q: (1j*self.kx*f2(u*q) + 1j*self.ky*f2(v*q))*self.mask
        dph = -div(phi) - p.mobility*self.k2*f2(mu_c)            # Cahn-Hilliard
        return [rx, ry, dph, -div(c) - p.kappa*self.k2*ch, -div(fog) - p.kappa*self.k2*fh]

    def extra_accel(self, u, v):
        """Extra acceleration for subclasses (combined_shelter adds a lining)."""
        return 0.0, 0.0

    def diagnostics(self):
        """Extra per-sample history fields for subclasses."""
        return {}

    def project(self, st):
        """Leray projection onto divergence-free velocity; zero mean drift."""
        uh, vh = st[0], st[1]
        q = (self.kx*uh + self.ky*vh)*self.k2inv
        uh, vh = uh - self.kx*q, vh - self.ky*q
        uh[0, 0] = vh[0, 0] = 0
        return [uh, vh] + st[2:]

    def step(self):
        """SSP-RK3 step; dt shrinks so that CFL = max|u| dt/dx <= 0.2."""
        p = self.p
        st = [self.uh, self.vh] + [np.fft.fft2(q) for q in (self.phi, self.c, self.fog)]
        umax = float(np.hypot(*self.fields(st[:2])).max())
        dt = min(p.dt, 0.2*(2*np.pi/p.n)/max(umax, 1e-12))
        t = self.t
        comb = lambda w0, s0, w1, s1, k: [w0*a + w1*(b + dt*c) for a, b, c in zip(s0, s1, k)]
        s1 = self.project(comb(0, st, 1, st, self.rhs(st, t)))
        s2 = self.project(comb(0.75, st, 0.25, s1, self.rhs(s1, t + dt)))
        s3 = self.project(comb(1/3, st, 2/3, s2, self.rhs(s2, t + 0.5*dt)))
        self.uh, self.vh = s3[0], s3[1]
        self.phi, self.c, self.fog = self.fields(s3[2:])
        self.t, self.last_dt = t + dt, dt

    def bin_water(self, peak=False):
        H = np.clip((1 + self.phi)/2, 0, 1)*self.band
        if peak:
            out = np.zeros(48)
            np.maximum.at(out, self.bins.ravel(), H.ravel())
            return out
        return np.bincount(self.bins.ravel(), H.ravel(), minlength=48)

    def integrity(self):
        """Ring closure: in every one of 48 angular sectors, the largest water
        fraction found (1 = a full water cell still blocks that direction;
        near 0 = a gap has opened). This is the fluid analogue of clay g."""
        return float(self.bin_water(peak=True).min())

    def thinnest_sector(self):
        """Least water in any sector, relative to t = 0 (thinning)."""
        return float(np.min(self.bin_water()/self.bin_water0))

    def leak_fraction(self):
        """Share of (non-negative part of) dye beyond the outer water edge."""
        c = np.maximum(self.c, 0)
        return float(c[self.outside].sum()/c.sum())

    def interface_length(self):
        """Total length of the water/air interface, integral of |grad H|."""
        hh = np.fft.fft2(np.clip((1 + self.phi)/2, 0, 1))
        return float(np.hypot(self.d(hh, 0), self.d(hh, 1)).sum()*(2*np.pi/self.p.n)**2)

    def speed(self):
        u, v = np.real(np.fft.ifft2(self.uh)), np.real(np.fft.ifft2(self.vh))
        return np.hypot(u, v)

    def fragments(self):
        """Count water pieces (phi > 0), periodic 4-neighbour connectivity."""
        on = self.phi > 0
        lab = np.where(on, np.arange(on.size).reshape(on.shape), on.size)
        while True:
            new = lab
            for sh, ax in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
                new = np.minimum(new, np.where(on, np.roll(lab, sh, ax), on.size))
            if np.array_equal(new, lab):
                return len(np.unique(lab[on]))
            lab = new


def run(p, sample_every=0.25, snap_times=(), sim_cls=None):
    sim = (sim_cls or FluidShelter)(p)
    water0, history, min_g, next_t = (1 + sim.phi).sum(), [], 1.0, sample_every
    snaps, pending = {}, sorted(snap_times)
    while sim.t < p.t_end - 1e-9:
        sim.step()
        if pending and sim.t >= pending[0] - 1e-9:
            snaps[pending.pop(0)] = (sim.phi.copy(), sim.c.copy())
        if sim.t >= next_t - 1e-9 or sim.t >= p.t_end - 1e-9:
            next_t += sample_every
            g = sim.integrity()
            min_g = min(min_g, g)
            sp = sim.speed()
            history.append(dict(t=round(sim.t, 6), leak=sim.leak_fraction(),
                                integrity=g, thinnest=sim.thinnest_sector(), max_speed=float(sp.max()),
                                ring_speed=float(sp[np.abs(sim.rho_n - 1) < p.layer + 0.1].max()),
                                phi_max=float(np.abs(sim.phi).max()), **sim.diagnostics()))
            if not np.isfinite(history[-1]["max_speed"]) or history[-1]["max_speed"] > 1e3:
                raise FloatingPointError(f"fluid run blew up at t={sim.t:.2f}: {asdict(p)}")
    last = history[-1]
    broke, recovered, label = classify(last["leak"], min_g, last["integrity"])
    frags = sim.fragments()
    u_ring = max(h["ring_speed"] for h in history)
    h = 2*p.layer*0.5*(p.ring_a + p.ring_b)
    mode = ("pinch-off" if frags > 1 else "rupture" if min_g < 0.1
            else "seep" if broke else "none")
    return dict(params=asdict(p), leak_final=last["leak"],
                leak_max=max(x["leak"] for x in history), min_integrity=min_g,
                thinnest_min=min(x["thinnest"] for x in history),
                integrity_end=last["integrity"], peak_ring_speed=u_ring,
                weber=(p.rho_ratio*u_ring**2*h/p.sigma) if p.sigma > 0 else float("inf"),
                water_mass_drift=float(abs((1 + sim.phi).sum() - water0)/water0),
                fragments_end=frags, break_mode=mode, broke=broke,
                recovered=recovered, label=label, history=history, snapshots=snaps)
