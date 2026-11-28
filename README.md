# Persistence-Based Reconciliation for Digital Twins in Edge-Cloud Kubernetes

Code, data and results for the paper *Persistence-Based Reconciliation for Digital Twins in Edge-Cloud Kubernetes*
(M. K. Akhtar, M. Saeed, B. Hussain; FAST-NUCES Islamabad).

A Digital Twin that triggers infrastructure actions (for example Kubernetes pod migrations) on every telemetry change
causes churn; a fixed timer reacts slowly. We study a **persistence rule**: reconcile a service only when its telemetry
stays more than `theta` away from the last reconciled state for `c` consecutive samples. It is compared with periodic and
naive event-driven policies on three synthetic workloads with known ground truth, and inside the
[EdgeSimPy](https://github.com/EdgeSimPy/EdgeSimPy) simulator.

> All results are from simulation with synthetic workloads. No real Kubernetes cluster was used.

## Headline results (see the paper for tables, seeds and confidence intervals)

| Comparison | Result |
|---|---|
| Persistence vs periodic at equal reconciliation count | sustained gap 14-43% lower, reaction to real jumps 31-50% sooner |
| Persistence vs naive event-driven | 62-77% fewer reconciliations (Phase 1), 51-74% fewer migrations (EdgeSimPy), at the cost of ~20-23 ticks slower reaction |
| Moving-average smoothing | does not help; the window sweep shows lag only |

## Repository layout

```
data/                    EdgeSimPy topology (sample_dataset2.json) and notes
src/phase1_experiment.py main Phase 1 experiment, ablation, paired statistics, Figure 1
src/window_sweep.py      moving-average window sweep
src/sensitivity.py       sensitivity to theta and c
src/edgesimpy_experiment.py   Phase 2 inside EdgeSimPy (slowest)
src/make_figures.py      Figures 2 and 3 and Phase 2 statistics
results/                 all CSV files and figures used in the paper
poster/build_poster.py   builds Final_Poster.pdf (A0) from results/*.csv
Final_Poster.pdf         conference poster, generated from the results
run_all.ps1 / run_all.sh run everything in order
```

## Setup (Python 3.10+)

```
python -m venv venv
venv\Scripts\activate          # Windows;  source venv/bin/activate on Linux/macOS
pip install -r requirements.txt
```

`requirements.txt` installs EdgeSimPy v1.1.0 directly from GitHub at the exact commit used for the results (the package is not published on PyPI), so `git` must be available.

## Reproduce

Run from the repository root, in this order (about 20-40 minutes in total; Phase 2 is the slowest because each run is a separate simulator process):

```
python src/phase1_experiment.py
python src/window_sweep.py
python src/sensitivity.py
python src/edgesimpy_experiment.py
python src/make_figures.py
```

All randomness is seeded (traces are generated from the seed, and every policy replays the same trace), so the CSV files are reproducible.

Optional: rebuild the poster from the result files (needs `pip install segno` and Google Chrome or Chromium):

```
python poster/build_poster.py
```

## Modeling notes and limitations

- Phase 1 counts reconciliations **per service**; one reconciliation is one possible migration.
- Sustained gap is measured against the demand **without** transient spikes, because the policy is meant to ignore them. Delay and false-reconciliation definitions are in the paper (Section IV).
- Phase 2 confines placement to 3 of the 6 servers, because the dataset has one service per server and no migration could then improve balance.
- Workloads are synthetic, and the periodic baseline is matched to the same reconciliation count.
- In Phase 2, tick 0 is used for the initial placement, so the periodic baseline performs one round fewer (6 reconciliations) than the count it was matched to. Persistence therefore uses about 4-7 more reconciliations than matched periodic (see the paper, Section V-D). Phase 2 metrics average over the ticks after all services are placed (988 of 1000).

## Citation and license

See `CITATION.cff`. Code is released under the MIT License (`LICENSE`).
