"""A prescribed, timed 'hug' for the two named mirror halves.

This is a two-dimensional geometry experiment, not material clay, a contact
solver, or Navier-Stokes. Norm is the left arm; Entropy is its spatial mirror.
Their names are supplied labels. No entropy or personality is measured.
The full bend is nonlinear. Only the separate axis stretch is a linear map.
The closed pose is also reused by hugged_ring.py to prepare smooth,
divergence-free initial data for the existing unforced fluid experiment.
"""
import argparse
import json
import math
from pathlib import Path

CYCLE_SECONDS = 8.0


def smoothstep(t):
    """Quintic interpolation, with zero first and second endpoint derivatives."""
    t = min(1.0, max(0.0, t))
    return t*t*t*(10.0 + t*(-15.0 + 6.0*t))


def arm_points(bend, horizontal_scale=1.0, vertical_scale=1.0, points=65):
    """Shared arm geometry; return exact left/right spatial mirrors."""
    if not isinstance(points, int) or points < 3:
        raise ValueError('At least three arm points are required.')
    norm, entropy = [], []
    for i in range(points):
        angle = -math.pi/2.0 + math.pi*i/(points-1)
        cosine = 0.0 if i in (0, points-1) else math.cos(angle)
        horizontal = horizontal_scale*(1.0-bend+bend*cosine)
        vertical = math.sin(angle)*vertical_scale
        norm.append([-horizontal, vertical])
        entropy.append([horizontal, vertical])
    return norm, entropy


def state_at(seconds, points=65):
    """Sample mirrored arms, with length units arbitrary and time in seconds.

    0-1: straight; 1-3: round inward; 3-5: joined and gently stretch;
    5-7: disengage and open; 7-8: straight. Outside the cycle, stay open.
    The joined stretch has a horizontal factor s and vertical factor 1/s,
    preserving the area of the closed ellipse. This is a chosen rule.
    """
    if not math.isfinite(seconds):
        raise ValueError('Time must be finite.')
    if not isinstance(points, int) or points < 3:
        raise ValueError('At least three arm points are required.')
    t = min(CYCLE_SECONDS, max(0.0, seconds))
    bend, scale = 0.0, 1.0
    if t < 1.0:
        phase = 'Straight arms'
    elif t < 3.0:
        phase = 'Round inward'
        bend = smoothstep((t-1.0)/2.0)
    elif t <= 5.0:
        phase, bend = 'Connected · gentle stretch', 1.0
        u = (t-3.0)/2.0
        pulse = 64.0*u**3*(1.0-u)**3
        scale = 1.0 + .08*pulse
    elif t < 7.0:
        phase = 'Release and open'
        bend = 1.0 - smoothstep((t-5.0)/2.0)
    else:
        phase = 'Arms open · cycle complete'
    norm, entropy = arm_points(bend, scale, 1.0/scale, points)
    gap = entropy[0][0] - norm[0][0]
    return dict(seconds=t, phase=phase, bend=bend,
                connected=gap <= 1e-12, endpoint_gap=gap,
                stretch_matrix=[[scale, 0.0], [0.0, 1.0/scale]],
                eigenvectors=[[1.0, 0.0], [0.0, 1.0]],
                eigenvalues=[scale, 1.0/scale], Norm=norm, Entropy=entropy)


def report():
    frames = [state_at(i/8.0) for i in range(65)]
    return dict(
        title='Norm and Entropy: a timed hug',
        model='Prescribed geometry; a visual and numerical prototype, not a physical clay or fluid solver.',
        interpretation='Here mirroring means spatial reflection of the left arm across x=0. The earlier field-copy test reflected velocity values; these are different operations.',
        duration_seconds=CYCLE_SECONDS,
        choice='The 8-second schedule and 8 percent horizontal stretch are illustrative choices, not measurements.',
        timing={'straight':[0,1], 'round_inward':[1,3], 'connected':[3,5], 'release_and_open':[5,7], 'open':[7,8]},
        geometry='Arms join at both tips to form a closed ellipse during the hold; they separate during release.',
        stretch='During the hold, horizontal eigenvalue s and vertical eigenvalue 1/s preserve enclosed area. The full bending motion is nonlinear.',
        scope='No forces, permeability rule, material response, or Navier-Stokes time evolution is implemented.',
        max_mirror_error=max(abs(a[0]+b[0])+abs(a[1]-b[1]) for f in frames for a,b in zip(f['Norm'],f['Entropy'])),
        checkpoints=[state_at(t, points=9) for t in (0, 2, 3, 4, 5, 6, 7, 8)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    result = report()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({key: result[key] for key in ('title', 'duration_seconds', 'max_mirror_error', 'scope')}, indent=2))
