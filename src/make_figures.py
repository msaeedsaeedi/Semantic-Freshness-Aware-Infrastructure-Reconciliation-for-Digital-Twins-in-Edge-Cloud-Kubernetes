"""
Builds paper figures 2 and 3 and the Phase 2 statistics from the CSV files (nothing is hard-coded).
Run from repo root after the experiments:  python src/make_figures.py
Outputs: results/fig2_window.png, results/fig3_edgesimpy.png, results/edgesimpy_stats.csv
(Figure 1 is written by phase1_experiment.py)
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

WL = ["drift-heavy", "default", "spiky"]

# ---- Figure 2: effect of the moving-average window (persistence policy) ----
w = pd.read_csv("results/window_sweep.csv")
g = w.groupby(["workload", "window"])[["sustained_gap", "delay"]].mean().reset_index()
fig, axs = plt.subplots(1, 2, figsize=(8, 3.2))
for wl in WL:
    d = g[g.workload == wl]
    axs[0].plot(d.window, d.sustained_gap, marker="o", label=wl)
    axs[1].plot(d.window, d.delay, marker="o", label=wl)
axs[0].set_ylabel("Sustained gap"); axs[1].set_ylabel("Delay after a real jump (ticks)")
for a in axs: a.set_xlabel("Moving-average window w (1 = no smoothing)"); a.grid(alpha=.3)
axs[0].legend(fontsize=7); plt.tight_layout(); plt.savefig("results/fig2_window.png", dpi=300); plt.close()

# ---- Figure 3: EdgeSimPy results ----
e = pd.read_csv("results/edgesimpy_results.csv")
order = ["event", "periodic_matched", "persistence"]
names = {"event": "Event (raw)", "periodic_matched": "Periodic (matched)", "persistence": "Persistence"}
fig, axs = plt.subplots(1, 3, figsize=(10, 3.2))
for ax, col, ttl in zip(axs, ["migrations", "sustained_gap", "load_imbalance"],
                        ["Migrations per run", "Sustained gap", "Load imbalance"]):
    for k, p in enumerate(order):
        m = [e[(e.workload == wl) & (e.policy == p)][col] for wl in WL]
        ax.bar(np.arange(3) + k * 0.27, [x.mean() for x in m], 0.27, yerr=[x.std() for x in m],
               capsize=2, label=names[p])
    ax.set_xticks(np.arange(3) + 0.27); ax.set_xticklabels(WL, fontsize=8); ax.set_title(ttl, fontsize=10)
axs[0].legend(fontsize=7); plt.tight_layout(); plt.savefig("results/fig3_edgesimpy.png", dpi=300); plt.close()

# ---- Phase 2 paired statistics (persistence minus comparator) ----
rng = np.random.default_rng(0); rows = []
def ci(x): m = [rng.choice(x, len(x)).mean() for _ in range(5000)]; return np.percentile(m, [2.5, 97.5])
for wl in WL:
    a = e[(e.workload == wl) & (e.policy == "persistence")].sort_values("seed")
    for comp in ("periodic_matched", "event"):
        b = e[(e.workload == wl) & (e.policy == comp)].sort_values("seed")
        for m in ("recs", "migrations", "sustained_gap", "load_imbalance"):
            d = a[m].values - b[m].values; lo, hi = ci(d)
            rows.append(dict(workload=wl, vs=comp, metric=m, mean_diff=round(d.mean(), 2),
                             ci_lo=round(lo, 2), ci_hi=round(hi, 2), significant=bool(lo > 0 or hi < 0)))
s = pd.DataFrame(rows); s.to_csv("results/edgesimpy_stats.csv", index=False); print(s.to_string(index=False))
print(e.groupby(["workload", "policy"])[["recs", "migrations", "sustained_gap", "load_imbalance"]].mean().round(2))
