"""Combined shelter sweep (water + clay lining, real density ratio 829) and a
comparison with the already-computed clay-only and water-only results.
Saves results/combined_results.{csv,json}, results/combined_compare.png.
"""
import csv, json, time
from dataclasses import replace
from multiprocessing import Pool
import numpy as np
from combined_shelter import CombinedParams, run
from fluid_shelter import RHO_RATIO_REAL
from run_sweep import OUT

PUSHES = [0.0, 2.0, 5.0, 10.0, 20.0, 40.0]
SIGMAS, KS = [1.0, 3.0], [25.0, 60.0]
KEYS = ["leak_final", "leak_max", "shelter_min", "shelter_end", "ring_closure_min",
        "ring_closure_end", "ring_reclosed", "lining_g_min", "lining_g_end",
        "lining_healed", "fragments_end", "break_mode", "water_mass_drift", "label"]


def job(p):
    for dt in (p.dt, p.dt/2):                 # one retry at halved dt
        try:
            r = run(replace(p, dt=dt))
            r.pop("snapshots")
            r["dt_used"] = dt
            return r
        except FloatingPointError as e:
            err = str(e)[:80]
    return dict(params=p.__dict__, label="blow-up", error=err, dt_used="both")


def previous():
    """Clay-only and water-only rows from the earlier result files (not rerun)."""
    rows = []
    for r in json.load(open(OUT/"results.json"))["runs"]:
        q = r["params"]
        if r["group"] in ("sweep", "control_no_push") and q["anxiety"] == 0.1 \
                and q["stiffness"] in KS and q["n"] == 64:
            rows.append(dict(model=f"clay K={q['stiffness']:g}", push=q["push"],
                             leak=r["leak_final"], heal=r["integrity_end"], label=r["label"]))
    for r in json.load(open(OUT/"fluid_results.json"))["runs"]:
        q = r["params"]
        if r["group"] in ("sweep", "control_no_push") and q["sigma"] in SIGMAS \
                and abs(q["rho_ratio"] - RHO_RATIO_REAL) < 1e-6 and q["anxiety"] == 0.1:
            rows.append(dict(model=f"water s={q['sigma']:g}", push=q["push"],
                             leak=r.get("leak_final", np.nan),
                             heal=r.get("integrity_end", np.nan), label=r["label"]))
    return rows


def main():
    base = CombinedParams(rho_ratio=RHO_RATIO_REAL, t_end=20.0)
    cases = [replace(base, push=P, sigma=s, stiffness=K)
             for s in SIGMAS for K in KS for P in PUSHES]
    start = time.time()
    with Pool(8) as pool:
        rows = pool.map(job, cases)
    with open(OUT/"combined_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sigma", "stiffness", "push", "dt_used"] + KEYS)
        for r in rows:
            q = r["params"]
            w.writerow([q["sigma"], q["stiffness"], q["push"], r["dt_used"]] +
                       [round(r[k], 4) if isinstance(r.get(k), float) else r.get(k, "")
                        for k in KEYS])
            print(f"s={q['sigma']:g} K={q['stiffness']:g} P={q['push']:g} dt={r['dt_used']} "
                  + " ".join(f"{k}={r[k]:.3f}" if isinstance(r.get(k), float) else f"{k}={r.get(k)}"
                             for k in KEYS))
    prev = previous()
    comb = [dict(model=f"combined s={r['params']['sigma']:g} K={r['params']['stiffness']:g}",
                 push=r["params"]["push"], leak=r.get("leak_final", np.nan),
                 heal=r.get("shelter_end", np.nan), label=r["label"]) for r in rows]
    meta = dict(scope="2D model only; water layer + clay lining; not the Clay problem.",
                base_params=base.__dict__, runtime_seconds=round(time.time() - start, 1),
                comparison=prev + comb, runs=rows)
    (OUT/"combined_results.json").write_text(json.dumps(meta, indent=1, default=float))
    plot(prev + comb)


def plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    style = {"clay": ("--", "s"), "water": (":", "o"), "combined": ("-", "^")}
    for m in sorted({r["model"] for r in rows}):
        pts = sorted([r for r in rows if r["model"] == m], key=lambda r: r["push"])
        ls, mk = style[m.split()[0]]
        x = [r["push"] + 0.5 for r in pts]           # +0.5 so P=0 shows on log axis
        for ax, key in zip(axes, ("leak", "heal")):
            ax.plot(x, [r[key] for r in pts], ls, marker=mk, label=m, ms=4)
            for xi, r in zip(x, pts):
                if r["label"] == "blow-up":
                    ax.plot(xi, 0, "kx", ms=7)
    axes[0].axhline(0.2, color="grey", lw=0.6)
    axes[1].axhline(0.9, color="grey", lw=0.6)
    axes[0].set_ylabel("final leak fraction (break above 0.2)")
    axes[1].set_ylabel("integrity at end (healed above 0.9)\nclay g / water closure / combined max")
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks([p + 0.5 for p in PUSHES], [f"{p:g}" for p in PUSHES])
        ax.set_xlabel("initial push P")
    axes[1].legend(fontsize=7, loc="lower left")
    fig.suptitle("Clay-only vs water-only vs water + clay lining (2D NS model; x = blow-up)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT/"combined_compare.png", dpi=130)


if __name__ == "__main__":
    main()
