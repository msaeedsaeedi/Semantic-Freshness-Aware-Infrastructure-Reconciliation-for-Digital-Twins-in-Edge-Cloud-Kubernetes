"""
Sensitivity of the persistence policy to threshold theta and persistence count c.
For every setting, periodic is re-matched to the same reconciliation count.
Run from repo root:  python src/sensitivity.py      Output: results/sensitivity.csv
"""
import math, numpy as np, pandas as pd
from phase1_experiment import make_trace, run, WORKLOADS, T, S

N = 30
rows = []
for wl, p in WORKLOADS.items():
    data = [make_trace(s, *p) for s in range(N)]
    for thr in (3, 4, 5, 6):
        for c in (2, 3, 4):
            r = [run(*d, "persistence", window=1, thr=thr, c=c) for d in data]
            recs = np.mean([x["recs"] for x in r])
            Tm = min(range(5, 101), key=lambda k: abs(S * math.ceil(T / k) - recs))
            q = [run(*d, "periodic", interval=Tm) for d in data]
            gp, gq = np.mean([x["sustained_gap"] for x in r]), np.mean([x["sustained_gap"] for x in q])
            dp, dq = np.mean([x["delay"] for x in r]), np.mean([x["delay"] for x in q])
            rows.append(dict(workload=wl, theta=thr, c=c, recs=recs, periodic_recs=S * math.ceil(T / Tm),
                             gap=gp, periodic_gap=gq, gap_gain_pct=100 * (1 - gp / gq),
                             delay=dp, periodic_delay=dq, delay_gain_pct=100 * (1 - dp / dq)))
df = pd.DataFrame(rows).round(2); df.to_csv("results/sensitivity.csv", index=False)
print(df.pivot_table(index=["workload", "theta"], columns="c", values="gap_gain_pct").to_string())
