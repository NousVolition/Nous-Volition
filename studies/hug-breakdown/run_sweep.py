"""Sweep push P x hug stiffness K at fixed anxiety; save JSON, CSV, heatmap.

Usage: python run_sweep.py [--quick]
"""
import csv, json, sys, time
from dataclasses import replace
from pathlib import Path
import numpy as np
from hug_breakdown import Params, run, LEAK_BREAK, INTEGRITY_BREAK, RECOVERED

OUT = Path(__file__).parent/"results"
PUSHES = [2.0, 5.0, 10.0, 20.0, 40.0]
STIFFNESSES = [3.0, 8.0, 25.0, 60.0]
LABELS = ["hold", "bend+recover", "bent", "break+heal", "break"]


def main(quick=False):
    OUT.mkdir(exist_ok=True)
    base = Params(t_end=8.0 if quick else 30.0)
    cases = [("sweep", replace(base, push=P, stiffness=K))
             for K in STIFFNESSES for P in PUSHES]
    cases += [("control_no_push", replace(base, push=0.0, stiffness=K)) for K in STIFFNESSES]
    cases += [("control_no_anxiety", replace(base, anxiety=0.0, push=PUSHES[-1], stiffness=K))
              for K in STIFFNESSES]
    cases += [("control_no_wall", replace(base, stiffness=0.0, push=P)) for P in (0.0, PUSHES[-1])]
    if not quick:   # resolution spot check at N=96 on two boundary cases
        cases += [("resolution_n96", replace(base, n=96, push=P, stiffness=25.0)) for P in (10.0, 20.0)]
    rows, start = [], time.time()
    for group, p in cases:
        r = run(p)
        r["group"] = group
        rows.append(r)
        print(f"{group:20s} K={p.stiffness:5.1f} P={p.push:5.1f} A={p.anxiety:.2f} n={p.n} "
              f"leak={r['leak_final']:.3f} min_g={r['min_integrity']:.3f} "
              f"g_end={r['integrity_end']:.3f} -> {r['label']}", flush=True)
    keys = ["group", "n", "anxiety", "push", "stiffness", "leak_final", "leak_max",
            "min_integrity", "integrity_end", "peak_wall_speed", "broke", "recovered", "label"]
    with open(OUT/"results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r in rows:
            p = r["params"]
            w.writerow([r["group"], p["n"], p["anxiety"], p["push"], p["stiffness"]] +
                       [round(r[k], 5) if isinstance(r[k], float) else r[k] for k in keys[5:]])
    meta = dict(scope=("2D periodic Navier-Stokes with Brinkman wall and forcing, used as an "
                       "engine for a SIMS-style metaphor. Not the Clay setup; says nothing "
                       "about Clay or about real people."),
                thresholds=dict(leak_break=LEAK_BREAK, integrity_break=INTEGRITY_BREAK,
                                recovered=RECOVERED),
                base_params=base.__dict__, runtime_seconds=round(time.time() - start, 1),
                runs=rows)
    (OUT/"results.json").write_text(json.dumps(meta, indent=1))
    heatmap([r for r in rows if r["group"] == "sweep"], OUT/"hold_break_map.png")


def heatmap(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    grid = np.zeros((len(STIFFNESSES), len(PUSHES)), int)
    text = [["" for _ in PUSHES] for _ in STIFFNESSES]
    for r in rows:
        i = STIFFNESSES.index(r["params"]["stiffness"])
        j = PUSHES.index(r["params"]["push"])
        grid[i, j] = LABELS.index(r["label"])
        text[i][j] = f"{r['label']}\nleak {r['leak_final']:.2f}\nmin g {r['min_integrity']:.2f}"
    cmap = ListedColormap(["#4caf50", "#cddc39", "#ffc107", "#ff7043", "#c62828"])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(grid, cmap=cmap, vmin=-0.5, vmax=len(LABELS) - 0.5, origin="lower", aspect="auto")
    for i in range(len(STIFFNESSES)):
        for j in range(len(PUSHES)):
            ax.text(j, i, text[i][j], ha="center", va="center", fontsize=7)
    ax.set_xticks(range(len(PUSHES)), [str(p) for p in PUSHES])
    ax.set_yticks(range(len(STIFFNESSES)), [str(k) for k in STIFFNESSES])
    ax.set_xlabel("initial push P (fades as exp(-t/1.5))")
    ax.set_ylabel("hug stiffness K = 1/eta")
    ax.set_title("Hold / break / recover, anxiety A = 0.1 (2D NS model only)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cmap.colors]
    ax.legend(handles, LABELS, fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    fig.savefig(path, dpi=130)


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
