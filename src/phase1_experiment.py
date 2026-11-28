"""
Phase 1: standalone simulation (main experiment).
Per-service reconciliation, 3 workloads, 50 seeds, same traces for every policy,
ablation (smoothing on/off), paired 95% bootstrap CIs.
Run from repo root:  python src/phase1_experiment.py
Outputs: results/final_raw.csv, final_table.csv, final_stats.csv, matched_T.csv, fig1_tradeoff.png
"""
import random, math, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

T, S, N_SEEDS = 1000, 6, 50
BASE, TELE, W = 20.0, 5, 3
THR, CONF, NEED, CAP = 4.0, 3, 4.0, 100
WORKLOADS = {  # drift_std, jump_prob, spike_prob, spike_len (ticks)
    "drift-heavy": (1.0, 0.005, 0.01, 3),
    "default": (0.5, 0.01, 0.03, 2),
    "spiky": (0.5, 0.01, 0.08, 7),
}

def make_trace(seed, drift, jump_p, spike_p, spike_len):
    rng = random.Random(seed)
    sust = np.zeros((T, S)); true = np.zeros((T, S)); jumps = []
    for s in range(S):
        d, left = BASE, 0
        for t in range(T):
            d += rng.gauss(0, drift)
            if rng.random() < jump_p:
                j = rng.choice([-8, 8]); d += j; jumps.append((s, t, np.sign(j)))
            d = max(1.0, min(60.0, d))
            if left == 0 and rng.random() < spike_p: left = spike_len
            sust[t, s] = d; true[t, s] = d + (10 if left > 0 else 0)
            left = max(0, left - 1)
    return sust, true, jumps

def run(sust, true, jumps, kind, window=W, thr=THR, c=CONF, interval=50):
    """Per-service reconciliation. Each (service, tick) update counts as one reconciliation."""
    hist, dt = [], np.full(S, BASE)
    last = sust[0].copy(); pend = np.zeros(S, int)
    events = []; gs = gr = 0.0
    for t in range(T):
        tele = t % TELE == 0
        if tele:
            hist.append(true[t]); hist = hist[-window:]; dt = np.mean(hist, axis=0)
        fire = np.zeros(S, bool)
        if kind == "periodic": fire[:] = (t % interval == 0)
        elif kind == "event": fire = np.abs(dt - last) > thr
        elif kind == "persistence" and tele:
            pend = np.where(np.abs(dt - last) > thr, pend + 1, 0); fire = pend >= c
        for s in np.where(fire)[0]:
            events.append((t, s, last[s], dt[s])); last[s] = dt[s]; pend[s] = 0
        gs += np.mean(np.abs(last - sust[t])); gr += np.mean(np.abs(last - true[t]))
    false = sum(abs(sust[t, s] - prev) <= NEED for t, s, prev, _ in events)
    by_s = {s: [(t, new) for t, ss, _, new in events if ss == s] for s in range(S)}
    delays = []
    for s, t0, sg in jumps:
        pre, d = sust[max(t0 - 1, 0), s], CAP
        for t, new in by_s[s]:
            if t >= t0 and (new - pre) * sg >= NEED: d = min(t - t0, CAP); break
        delays.append(d)
    return dict(recs=len(events), false_recs=false, sustained_gap=gs / T, raw_gap=gr / T,
                delay=float(np.mean(delays)) if delays else np.nan)

def boot_ci(x, rng, n=5000):
    x = np.asarray(x); m = [rng.choice(x, len(x)).mean() for _ in range(n)]
    return np.percentile(m, [2.5, 97.5])

if __name__ == "__main__":
    rows, sweep, matchedT = [], [], {}
    for wname, p in WORKLOADS.items():
        data = [make_trace(s, *p) for s in range(N_SEEDS)]
        sem_recs = np.mean([run(*d, "persistence", window=1)["recs"] for d in data])
        Tm = min(range(5, 101), key=lambda k: abs(S * math.ceil(T / k) - sem_recs))
        pols = {"Event raw": dict(kind="event", window=1),
                "Event MA": dict(kind="event"),
                "Persistence (proposed)": dict(kind="persistence", window=1),
                "Persistence + MA (w=3)": dict(kind="persistence", window=3),
                "Periodic T=50": dict(kind="periodic"),
                f"Periodic matched (T={Tm})": dict(kind="periodic", interval=Tm)}
        matchedT[wname] = Tm
        for pn, kw in pols.items():
            for seed, d in enumerate(data):
                rows.append(dict(workload=wname, policy=pn, seed=seed, **run(*d, **kw)))
        for k in (10, 15, 20, 30, 40, 50, 75, 100):   # periodic frontier for the figure
            r = [run(*d, "periodic", interval=k) for d in data]
            sweep.append(dict(workload=wname, T=k, recs=np.mean([x["recs"] for x in r]),
                              gap=np.mean([x["sustained_gap"] for x in r])))
    df = pd.DataFrame(rows).replace(r"Periodic matched \(T=\d+\)", "Periodic matched", regex=True)
    df.to_csv("results/final_raw.csv", index=False)
    pd.Series(matchedT, name="matched_T").to_csv("results/matched_T.csv")
    cols = ["recs", "false_recs", "sustained_gap", "raw_gap", "delay"]
    tab = df.groupby(["workload", "policy"])[cols].agg(["mean", "std"]).round(2)
    tab.to_csv("results/final_table.csv"); print(tab.to_string())

    # Paired differences: Persistence minus comparator, 95% bootstrap CI
    rng = np.random.default_rng(0); st = []
    for w in WORKLOADS:
        sem = df[(df.workload == w) & (df.policy == "Persistence (proposed)")].sort_values("seed")
        for comp in ("Periodic matched", "Event raw", "Event MA", "Persistence + MA (w=3)"):
            oth = df[(df.workload == w) & (df.policy == comp)].sort_values("seed")
            for m in cols:
                diff = sem[m].values - oth[m].values; lo, hi = boot_ci(diff, rng)
                st.append(dict(workload=w, vs=comp, metric=m, mean_diff=round(diff.mean(), 2),
                               ci_lo=round(lo, 2), ci_hi=round(hi, 2), significant=(lo > 0 or hi < 0)))
    sdf = pd.DataFrame(st); sdf.to_csv("results/final_stats.csv", index=False)
    print("\nPaired differences (Persistence minus X); negative = persistence lower. significant = CI excludes 0")
    print(sdf[sdf.metric.isin(["recs", "sustained_gap", "delay"])].to_string(index=False))

    # Figure: cost vs sustained gap, periodic frontier line, one panel per workload
    sw = pd.DataFrame(sweep); fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=False)
    mk = {"Event raw": "^", "Event MA": "v", "Persistence + MA (w=3)": "D", "Persistence (proposed)": "o", "Periodic matched": "s"}
    for ax, w in zip(axs, WORKLOADS):
        f = sw[sw.workload == w]; ax.plot(f.recs, f.gap, "-", color="gray", label="Periodic (sweep of T)")
        for pn, m in mk.items():
            q = df[(df.workload == w) & (df.policy == pn)]
            ax.scatter(q.recs.mean(), q.sustained_gap.mean(), marker=m, s=70, label=pn, zorder=3)
        ax.set_title(w); ax.set_xlabel("Reconciliations (per-service, 1000 ticks)"); ax.grid(alpha=.3)
    axs[0].set_ylabel("Sustained gap (lower is better)"); axs[0].legend(fontsize=7)
    plt.tight_layout(); plt.savefig("results/fig1_tradeoff.png", dpi=300)
    print("\nSaved results/fig1_tradeoff.png")
