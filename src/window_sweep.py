"""
Does the moving-average (MA) window matter? Persistence policy, c=3, thr=4, w = 1,2,3,5,8.
w=1 means no smoothing. Run from repo root:  python src/window_sweep.py
"""
import numpy as np, pandas as pd
from phase1_experiment import make_trace, run, WORKLOADS, N_SEEDS

rows = []
for wname, p in WORKLOADS.items():
    data = [make_trace(s, *p) for s in range(N_SEEDS)]
    for w in (1, 2, 3, 5, 8):
        for seed, d in enumerate(data):
            rows.append(dict(workload=wname, window=w, seed=seed, **run(*d, "persistence", window=w)))
df = pd.DataFrame(rows); df.to_csv("results/window_sweep.csv", index=False)
cols = ["recs", "false_recs", "sustained_gap", "delay"]
print(df.groupby(["workload", "window"])[cols].mean().round(2).to_string())
