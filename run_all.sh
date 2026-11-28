#!/usr/bin/env bash
set -e
# Run the full pipeline from the repository root (bash). Total time: roughly 20-40 minutes.
python src/phase1_experiment.py     # Phase 1 main results + fig1
python src/window_sweep.py          # moving-average window sweep
python src/sensitivity.py           # theta / c sensitivity
python src/edgesimpy_experiment.py  # Phase 2 in EdgeSimPy (slowest)
python src/make_figures.py          # fig2, fig3, Phase 2 statistics
