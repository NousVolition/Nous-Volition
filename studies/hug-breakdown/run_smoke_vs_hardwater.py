"""SEPARATE TEST requested by the user: smoke vs hard water, head to head.
(a) hard-water shelter ring in air (sigma = base 1 x 72.8/72.8, rho ratio 829.3);
(b) smoke shelter ring in air: cool dense smoke (1 g/m3 soot), rho ratio 1.0008,
    viscosity ratio 1.0000014, sigma = 0 (a gas-particle suspension has no
    surface tension). Phase field kept (Cahn-Hilliard still keeps an edge).
(b2) same smoke, MISCIBLE: no Cahn-Hilliard, the ring diffuses like the dye
    (closer to real smoke, which just mixes).
(b3) hot smoke ring (200 C, rho ratio 0.62 to air, mu ratio 1.42, sigma 0).
Same geometry, anxiety A = 0.1, push P in {0, 2, 5, 10, 20}, t_end 20.
Saves results/smoke_vs_hardwater.{png,json}. Model only, 2D, no gravity.
"""
import json, os, time
from functools import partial
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from materials import HARD_WATER, SMOKE_COOL, SMOKE_HOT, AIR, pair_params, job

OUT = Path(__file__).resolve().parent/"results"
PUSHES = [0.0, 2.0, 5.0, 10.0, 20.0]
SNAPS = (2.0, 5.0, 20.0)
ARMS = {"hard water ring": dict(liquid=HARD_WATER),
        "cool smoke ring (sigma=0)": dict(liquid=SMOKE_COOL),
        "cool smoke ring, miscible": dict(liquid=SMOKE_COOL, miscible=True),
        "hot smoke ring 200C (sigma=0)": dict(liquid=SMOKE_HOT)}


def cases():
    return [((arm, P), pair_params(a["liquid"], AIR, push=P, base_sigma=1.0, t_end=20.0,
                                   miscible=a.get("miscible", False)))
            for arm, a in ARMS.items() for P in PUSHES]


def main(workers=int(os.environ.get("WORKERS", 7))):
    OUT.mkdir(exist_ok=True)
    start = time.time()
    with Pool(workers) as pool:
        rows = pool.map(partial(job, snap_times=SNAPS), cases(), chunksize=1)
    summary = []
    for r in rows:
        arm, P = r["group"]
        p = r["params"]
        s = dict(arm=arm, push=P, rho_ratio=p["rho_ratio"], mu_ratio=p["mu_ratio"],
                 sigma=p["sigma_phys"], miscible=p["miscible"], label=r["label"],
                 **{k: r.get(k) for k in ("break_mode", "leak_final", "leak_max", "min_integrity",
                                          "integrity_end", "t_closure_half", "t_closure_lost",
                                          "fragments_end", "water_mass_drift", "attempts")},
                 t=[h["t"] for h in r.get("history", [])],
                 leak=[h["leak"] for h in r.get("history", [])],
                 closure=[h["integrity"] for h in r.get("history", [])])
        summary.append(s)
        print(f"{arm:30s} P={P:4.0f} leak={s['leak_final'] if s['leak_final'] is None else round(s['leak_final'], 3)} "
              f"close_min={s['min_integrity'] if s['min_integrity'] is None else round(s['min_integrity'], 3)} "
              f"t(closure<0.5)={s['t_closure_half']} t(closure<0.1)={s['t_closure_lost']} "
              f"frags={s['fragments_end']} -> {s['label']} ({s['break_mode']})")
    plots(rows)
    meta = dict(test="smoke vs hard water (user's separate test)",
                scope=("2D, no gravity, model only. A smoke ring has no surface tension and ~air "
                       "density: nothing holds it together, so smearing/mixing is the honest result."),
                runtime_seconds=round(time.time() - start, 1), runs=summary)
    (OUT/"smoke_vs_hardwater.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"runtime {time.time() - start:.0f} s")


def plots(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    arms, get = list(ARMS), lambda arm, P: next(r for r in rows if r["group"] == (arm, P))
    fig = plt.figure(figsize=(15, 9.5))
    gs = fig.add_gridspec(3, 8)
    cols = plt.cm.viridis(np.linspace(0, 0.9, len(PUSHES)))
    for k, (metric, name) in enumerate((("leak", "dye leak"), ("integrity", "ring closure"))):
        for a_i, arm in enumerate(arms[:2]):
            ax = fig.add_subplot(gs[0, 4*k + 2*a_i:4*k + 2*a_i + 2])
            for P in PUSHES:
                h = get(arm, P).get("history", [])
                ax.plot([x["t"] for x in h], [x[metric] for x in h], color=cols[PUSHES.index(P)],
                        label=f"P={P:g}")
            ax.set_title(f"{arm}: {name} vs t", fontsize=8)
            ax.set_ylim(-0.02, 1.02), ax.tick_params(labelsize=7)
            if k == 0 and a_i == 0:
                ax.legend(fontsize=6)
    w, x = 0.2, np.arange(len(PUSHES))
    ax1, ax2 = fig.add_subplot(gs[1, 0:4]), fig.add_subplot(gs[1, 4:8])
    for a_i, arm in enumerate(arms):
        leak = [get(arm, P).get("leak_final", np.nan) for P in PUSHES]
        tl = [get(arm, P).get("t_closure_half") for P in PUSHES]
        ax1.bar(x + (a_i - 1.5)*w, leak, w, label=arm)
        ax2.bar(x + (a_i - 1.5)*w, [20.5 if t is None else t for t in tl], w, label=arm,
                hatch=None)
    ax1.axhline(0.2, color="k", ls=":", lw=0.8)
    ax1.set_xticks(x, [f"P={P:g}" for P in PUSHES]), ax2.set_xticks(x, [f"P={P:g}" for P in PUSHES])
    ax1.set_title("final dye leak at t=20 (break threshold 0.2 dotted)", fontsize=8)
    ax2.set_title("time ring closure first < 0.5 (bar at 20.5 = never)", fontsize=8)
    ax1.legend(fontsize=7)
    for j, P in enumerate((5.0, 20.0)):
        for i, arm in enumerate(arms[:2]):
            r = get(arm, P)
            for m, t in enumerate((5.0, 20.0)):
                a = fig.add_subplot(gs[2, 4*j + 2*i + m])
                a.set_xticks([]), a.set_yticks([])
                a.set_title(f"{arm.split(' (')[0]}\nP={P:g} t={t:g}", fontsize=7)
                if t in r.get("snapshots", {}):
                    phi, c = r["snapshots"][t]
                    a.imshow(phi.T, origin="lower", cmap="Blues", vmin=-1, vmax=1)
                    a.contour(c.T, levels=[0.5], colors="crimson", linewidths=0.5)
    fig.suptitle("SEPARATE TEST: smoke vs hard water shelter ring in air (2D model, no gravity; "
                 "ring phase blue, inner dye edge red)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT/"smoke_vs_hardwater.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
