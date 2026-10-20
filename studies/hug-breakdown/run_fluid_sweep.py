"""Fluid-shelter sweep: push P x surface tension sigma at the REAL water/air
density ratio, plus controls and a density-ratio trend check.
Saves results/fluid_*.{csv,json,png}. Usage: python run_fluid_sweep.py
"""
import csv, json, time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from fluid_shelter import FluidParams, run, RHO_RATIO_REAL
from run_sweep import PUSHES, LABELS, OUT

SIGMAS = [0.3, 1.0, 3.0, 10.0]
RATIOS = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0, RHO_RATIO_REAL]
SNAPS = (3.0, 20.0)


def job(item):
    group, p = item
    try:
        r = run(p, snap_times=SNAPS)
    except FloatingPointError as e:
        r = dict(params=p.__dict__, label="blow-up", error=str(e)[:80], snapshots={})
    r["group"] = group
    return r


def main():
    OUT.mkdir(exist_ok=True)
    base = FluidParams(rho_ratio=RHO_RATIO_REAL, t_end=20.0)
    cases = [("sweep", replace(base, push=P, sigma=s)) for s in SIGMAS for P in PUSHES]
    cases += [("control_no_surface_tension", replace(base, push=P, sigma=0.0)) for P in PUSHES]
    cases += [("control_no_push", replace(base, push=0.0, sigma=s)) for s in (0.0, 1.0)]
    cases += [("control_no_anxiety", replace(base, anxiety=0.0, push=PUSHES[-1], sigma=1.0))]
    cases += [("density_ratio_trend", replace(base, rho_ratio=r, push=10.0, sigma=1.0))
              for r in RATIOS[:-1]]               # the real ratio is already in the sweep
    start = time.time()
    with Pool(8) as pool:
        rows = pool.map(job, cases)
    for r in rows:
        p = r["params"]
        print(f"{r['group']:27s} rho={p['rho_ratio']:6.1f} sigma={p['sigma']:5.1f} "
              f"P={p['push']:5.1f} A={p['anxiety']:.2f} leak={r.get('leak_final', np.nan):.3f} "
              f"closure_min={r.get('min_integrity', np.nan):.3f} end={r.get('integrity_end', np.nan):.3f} "
              f"frags={r.get('fragments_end', '-')} We={r.get('weber', np.nan):.1f} "
              f"-> {r['label']} ({r.get('break_mode', '')})")
    keys = ["leak_final", "leak_max", "min_integrity", "integrity_end", "thinnest_min",
            "peak_ring_speed", "weber", "fragments_end", "break_mode", "water_mass_drift",
            "broke", "recovered", "label"]
    with open(OUT/"fluid_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "rho_ratio", "sigma", "push", "anxiety"] + keys)
        for r in rows:
            p = r["params"]
            w.writerow([r["group"], round(p["rho_ratio"], 2), p["sigma"], p["push"], p["anxiety"]] +
                       [round(r[k], 5) if isinstance(r.get(k), float) else r.get(k, "") for k in keys])
    plots(rows)
    for r in rows:
        r.pop("snapshots", None)
    meta = dict(scope=("2D two-phase (water/fog/air) Navier-Stokes + Cahn-Hilliard surface "
                       "tension, model of the SIMS metaphor. Not the Clay setup."),
                base_params=base.__dict__, runtime_seconds=round(time.time() - start, 1),
                runs=rows)
    (OUT/"fluid_results.json").write_text(json.dumps(meta, indent=1, default=float))


def plots(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    labels = LABELS + ["blow-up"]
    sweep = [r for r in rows if r["group"] in ("sweep", "control_no_surface_tension")]
    sig = [0.0] + SIGMAS
    grid = np.zeros((len(sig), len(PUSHES)), int)
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for r in sweep:
        i, j = sig.index(r["params"]["sigma"]), PUSHES.index(r["params"]["push"])
        grid[i, j] = labels.index(r["label"])
        txt = r["label"] if r["label"] == "blow-up" else (
            f"{r['label']}\n{r['break_mode']}\nleak {r['leak_final']:.2f}\nclose {r['min_integrity']:.2f}")
        ax.text(j, i, txt, ha="center", va="center", fontsize=6.5)
    cmap = ListedColormap(["#4caf50", "#cddc39", "#ffc107", "#ff7043", "#c62828", "#9e9e9e"])
    ax.imshow(grid, cmap=cmap, vmin=-0.5, vmax=len(labels) - 0.5, origin="lower", aspect="auto")
    ax.set_xticks(range(len(PUSHES)), [str(p) for p in PUSHES])
    ax.set_yticks(range(len(sig)), [str(s) for s in sig])
    ax.set_xlabel("initial push P (same fading burst as the clay map)")
    ax.set_ylabel("surface tension sigma (0 = force off)")
    ax.set_title("Fluid shelter (water/fog/air, real density ratio 829), A = 0.1")
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in cmap.colors], labels,
              fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    fig.savefig(OUT/"fluid_hold_break_map.png", dpi=130)
    plt.close(fig)
    show = [r for r in sweep if r["params"]["sigma"] in (0.0, 1.0, 10.0) and r["snapshots"]]
    show = [r for r in show if r["params"]["push"] in (5.0, 20.0, 40.0)]
    fig, axes = plt.subplots(2, len(show), figsize=(2.2*len(show), 4.6), squeeze=False)
    for j, r in enumerate(show):
        for i, t in enumerate(SNAPS):
            phi, c = r["snapshots"][t]
            a = axes[i][j]
            a.imshow(phi.T, origin="lower", cmap="Blues", vmin=-1, vmax=1)
            a.contour(c.T, levels=[0.5], colors="crimson", linewidths=0.6)
            a.set_xticks([]), a.set_yticks([])
            a.set_title(f"s={r['params']['sigma']} P={r['params']['push']} t={t:g}", fontsize=6)
    fig.suptitle("water (blue) and inner dye edge (red)", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/"fluid_snapshots.png", dpi=130)
    plt.close(fig)
    trend = sorted([r for r in rows if r["group"] == "density_ratio_trend" or
                    (r["group"] == "sweep" and r["params"]["sigma"] == 1.0 and r["params"]["push"] == 10.0)],
                   key=lambda r: r["params"]["rho_ratio"])
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ok = [r for r in trend if "leak_final" in r]
    ax.semilogx([r["params"]["rho_ratio"] for r in ok], [r["leak_final"] for r in ok], "o-", label="leak")
    ax.semilogx([r["params"]["rho_ratio"] for r in ok], [r["min_integrity"] for r in ok], "s-", label="min closure")
    ax.set_xlabel("water/air density ratio (real = 829)")
    ax.legend(fontsize=7)
    ax.set_title("Density-ratio trend, P = 10, sigma = 1", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT/"fluid_density_trend.png", dpi=130)


if __name__ == "__main__":
    main()
