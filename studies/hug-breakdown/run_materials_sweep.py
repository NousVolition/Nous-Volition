"""Materials sweep: shelter liquid {water, hard water, H2O2 100 %} x surround
{air, cool dense smoke, hot smoke 200 C, CO2, helium} x push P {5, 10, 20},
base sigma = 1, anxiety 0.1, t_end 20, n = 64. Blow-ups retried once at dt/2.
Saves results/materials_{results.csv,results.json,map.png,snapshots.png}.
Model only (2D, no gravity). Usage: python run_materials_sweep.py
"""
import csv, json, os, time
from functools import partial
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from materials import (HARD_WATER, WATER, H2O2_100, AIR, SMOKE_COOL, SMOKE_HOT, CO2, HELIUM,
                       pair_params, job, table_rows)

OUT = Path(__file__).resolve().parent/"results"
LIQ = {"water": WATER, "hard water": HARD_WATER, "H2O2 100%": H2O2_100}
GAS = {"air": AIR, "cool smoke": SMOKE_COOL, "hot smoke": SMOKE_HOT, "CO2": CO2, "helium": HELIUM}
PUSHES = [5.0, 10.0, 20.0]
SNAPS = (3.0, 20.0)
KEYS = ["leak_final", "leak_max", "min_integrity", "integrity_end", "t_closure_half",
        "t_closure_lost", "fragments_end", "break_mode", "weber", "water_mass_drift", "label"]


def cases():
    out = [((lk, gk), pair_params(L, G, push=P, base_sigma=1.0, t_end=20.0))
           for lk, L in LIQ.items() for gk, G in GAS.items() for P in PUSHES]
    return sorted(out, key=lambda c: -c[1].push)        # hardest (largest scaled push) first


def fmt(r, k):
    v = r.get(k, "")
    return round(v, 5) if isinstance(v, float) else v


def main(workers=int(os.environ.get("WORKERS", 7))):
    OUT.mkdir(exist_ok=True)
    start = time.time()
    with Pool(workers) as pool:
        rows = pool.map(partial(job, snap_times=SNAPS), cases(), chunksize=1)
    rows.sort(key=lambda r: (list(LIQ).index(r["group"][0]), list(GAS).index(r["group"][1]),
                             r["params"]["push_phys"]))
    for r in rows:
        p = r["params"]
        print(f"{r['group'][0]:10s} in {r['group'][1]:10s} P={p['push_phys']:4.0f} "
              f"rho_l/rho_g={p['rho_ratio']:8.1f} mu_l/mu_g={p['mu_ratio']:5.1f} sig={p['sigma_phys']:.3f} "
              f"leak={r.get('leak_final', np.nan):.3f} close_min={r.get('min_integrity', np.nan):.3f} "
              f"end={r.get('integrity_end', np.nan):.3f} t_open={r.get('t_closure_lost')} "
              f"frags={r.get('fragments_end', '-')} -> {r['label']} ({r.get('break_mode', '')}) "
              f"dt={r.get('dt_used', '-')} {'; '.join(r['attempts'][:-1]) if len(r['attempts']) > 1 else ''}")
    with open(OUT/"materials_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["liquid", "gas", "push", "rho_ratio", "mu_ratio", "sigma_model", "dt_used"] + KEYS + ["attempts"])
        for r in rows:
            p = r["params"]
            w.writerow([*r["group"], p["push_phys"], round(p["rho_ratio"], 3), round(p["mu_ratio"], 3),
                        round(p["sigma_phys"], 4), r.get("dt_used", "")] + [fmt(r, k) for k in KEYS]
                       + [" | ".join(r["attempts"])])
    plots(rows)
    for r in rows:
        r.pop("snapshots", None)
    meta = dict(scope="2D two-phase NS + Cahn-Hilliard model, no gravity; model only, not the Clay problem",
                runtime_seconds=round(time.time() - start, 1), materials=table_rows(), runs=rows)
    (OUT/"materials_results.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"runtime {time.time() - start:.0f} s")


def plots(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"hold": "#4caf50", "bend+recover": "#cddc39", "bent": "#ffc107", "break+heal": "#ff7043",
              "break": "#c62828", "blow-up": "#9e9e9e", "stopped (too slow)": "#616161"}
    ylab = [f"{l} / {g}" for l in LIQ for g in GAS]
    fig, ax = plt.subplots(figsize=(8, 9))
    for r in rows:
        i = ylab.index(f"{r['group'][0]} / {r['group'][1]}")
        j = PUSHES.index(r["params"]["push_phys"])
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, color=colors[r["label"]]))
        txt = r["label"] if "leak_final" not in r else (
            f"{r['label']} ({r['break_mode']})\nleak {r['leak_final']:.2f} close {r['min_integrity']:.2f}")
        ax.text(j, i, txt, ha="center", va="center", fontsize=6.5)
    ax.set_xlim(-0.5, len(PUSHES) - 0.5), ax.set_ylim(-0.5, len(ylab) - 0.5)
    ax.set_xticks(range(len(PUSHES)), [f"P={p:g}" for p in PUSHES])
    ax.set_yticks(range(len(ylab)), ylab, fontsize=7)
    ax.invert_yaxis()
    ax.set_title("Fluid shelter, real materials (2D, no gravity), base sigma=1, A=0.1", fontsize=9)
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()], list(colors),
              fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    fig.savefig(OUT/"materials_map.png", dpi=130)
    plt.close(fig)
    show = [r for r in rows if r["params"]["push_phys"] == 20.0]
    fig, axes = plt.subplots(len(LIQ), len(GAS), figsize=(2.1*len(GAS), 2.2*len(LIQ)), squeeze=False)
    for r in show:
        a = axes[list(LIQ).index(r["group"][0])][list(GAS).index(r["group"][1])]
        a.set_xticks([]), a.set_yticks([])
        a.set_title(f"{r['group'][0]} / {r['group'][1]}\nP=20 {r['label']}", fontsize=6)
        if 20.0 in r.get("snapshots", {}):
            phi, c = r["snapshots"][20.0]
            a.imshow(phi.T, origin="lower", cmap="Blues", vmin=-1, vmax=1)
            a.contour(c.T, levels=[0.5], colors="crimson", linewidths=0.6)
    fig.suptitle("t = 20: shelter liquid (blue), inner dye edge (red); blank = no result", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/"materials_snapshots.png", dpi=130)
    plt.close(fig)


def dt_check(workers=4):
    """Re-run the marginal P=20 cases at dt = 0.002 (python run_materials_sweep.py dtcheck)."""
    from dataclasses import replace
    picks = [("H2O2 100%", "air"), ("H2O2 100%", "CO2"), ("water", "CO2"), ("water", "hot smoke")]
    items = [((l, g), replace(pair_params(LIQ[l], GAS[g], push=20.0, t_end=20.0), dt=0.002)) for l, g in picks]
    with Pool(workers) as pool:
        rows = pool.map(job, items, chunksize=1)
    out = []
    for r in rows:
        out.append(dict(liquid=r["group"][0], gas=r["group"][1], push=20.0, dt=0.002, label=r["label"],
                        **{k: r.get(k) for k in KEYS[:-1]}))
        print(out[-1])
    (OUT/"materials_dtcheck.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    import sys
    dt_check() if sys.argv[1:] == ["dtcheck"] else main()
