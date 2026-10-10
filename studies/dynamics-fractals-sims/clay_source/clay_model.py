"""Engineering-shear Burgers response using published wet-kaolin fits.

Cooke & van der Elst (2012), doi:10.1029/2011GL050186, Table 1 and Eq. 1.
Independent idealized pulse for each row; not the original stepped experiment.
Time, stress, modulus and viscosity units: s, Pa, Pa, Pa.s. No yield threshold.
"""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = 20.0
HOLD = 100.0
RELEASE = START + HOLD
END = RELEASE + 300.0


def materials():
    with (ROOT / 'source-data/cooke-2012-table-1.csv').open(newline='') as f:
        return [{key: float(value) for key, value in row.items()}
                for row in csv.DictReader(f)]


def state_at(material, seconds, side='right'):
    """Closed-form pulse, including explicit left limits at the two jumps.

    e: instantaneous Maxwell spring, k: recoverable Kelvin strain,
    v: retained Maxwell dashpot strain. The plateau is the infinite-time
    limit within this idealized model, not a prediction about drying or aging.
    """
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Time must be finite and nonnegative.')
    if side not in ('left', 'right'):
        raise ValueError('side must be left or right')
    stress, gm, em, gk, ek = (material[k] for k in
        ('stress_Pa', 'G_M_Pa', 'eta_M_Pa_s', 'G_K_Pa', 'eta_K_Pa_s'))
    if stress < 0 or min(gm, em, gk, ek) <= 0:
        raise ValueError('Nonnegative stress and positive coefficients required.')
    tau = ek / gk
    x = seconds - START
    if x < 0 or (x == 0 and side == 'left'):
        applied = e = k = v = 0.0
        phase = 'Before loading'
    elif x < HOLD or (x == HOLD and side == 'left'):
        applied = stress
        e = stress / gm
        k = stress / gk * -math.expm1(-x / tau)
        v = stress * x / em
        phase = 'Under shear load'
    else:
        applied = e = 0.0
        k = stress / gk * -math.expm1(-HOLD / tau) * math.exp(-(x-HOLD)/tau)
        v = stress * HOLD / em
        phase = 'Released · recovering'
    return dict(seconds=seconds, side=side, stress_Pa=applied,
                elastic=e, delayed=k, retained=v, total=e+k+v,
                final_retained=stress*HOLD/em, phase=phase)


def sample_times():
    result = []
    for t in range(int(END) + 1):
        if t in (START, RELEASE):
            result.append((float(t), 'left'))
        result.append((float(t), 'right'))
    return result


def trajectory(material):
    return [state_at(material, t, side) for t, side in sample_times()]


def shear_points(points, strain, magnification=1.0):
    """Display map only: x'=x+(magnification*engineering shear)*y, y'=y."""
    return [[x + magnification*strain*y, y] for x, y in points]
