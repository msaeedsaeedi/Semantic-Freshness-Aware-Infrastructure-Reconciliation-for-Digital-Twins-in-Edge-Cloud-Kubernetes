# Semantic Freshness-Aware Infrastructure Reconciliation for Digital Twins in Edge-Cloud Kubernetes

This repository contains the code, datasets, and results for our research project on **semantic freshness-aware reconciliation** for Digital Twin systems deployed across the edge-cloud continuum.

**Group:** 23I-0777 Mohammad Saeed, 23I-0524 Muhammad Kaleem Akhtar  
**Course:** Cloud Computing Research Assignment

---

## Research Question

Under what workload, network, and energy conditions does a semantic freshness-aware reconciliation policy reduce unnecessary Kubernetes infrastructure reconciliation without degrading Digital Twin freshness or increasing IoT device energy consumption, relative to periodic and naive event-driven baselines?

---

## Base Article

Our work reproduces and extends:

> P. S. Souza, T. Ferreto, and R. N. Calheiros, "EdgeSimPy: Python-Based Modeling and Simulation of Edge Computing Resource Management Policies,"  
> *Future Generation Computer Systems*, vol. 148, pp. 446–459, 2023.  
> DOI: https://doi.org/10.1016/j.future.2023.06.013  
> GitHub: https://github.com/EdgeSimPy/edgesimpy

---

## Repository Structure

```text
.
├── data/
│   ├── README.md                    # Dataset documentation
│   └── sample_dataset2.json         # EdgeSimPy reference dataset
├── results/
│   └── preliminary_results.csv      # Output of the preliminary simulation
├── src/
│   └── simulate_reconciliation.py   # Simulation of the three policies
└── README.md
```

---

## Setup

### Requirements

- Python 3.10 or later (tested on 3.14)
- `pip` and `venv`

### Installation

```bash
# Clone the repository
git clone https://github.com/msaeedsaeedi/Semantic-Freshness-Aware-Infrastructure-Reconciliation-for-Digital-Twins-in-Edge-Cloud-Kubernetes.git
cd Semantic-Freshness-Aware-Infrastructure-Reconciliation-for-Digital-Twins-in-Edge-Cloud-Kubernetes

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install EdgeSimPy from GitHub (it is not on PyPI)
pip install git+https://github.com/EdgeSimPy/edgesimpy.git

# Install supporting libraries
pip install numpy pandas matplotlib
```

> **Note:** The PyPI package name is `edgesimpy`, but the Python import name is `edge_sim_py`. The install command above pulls from source to avoid version mismatch with the tutorials.

---

## Running the Preliminary Experiment

```bash
python src/simulate_reconciliation.py
```

This runs a 1000-tick simulation of three reconciliation policies over 6 services and prints a comparison table:

| Policy | Reconciliations | Avg AoI | Total Overhead |
|---|---:|---:|---:|
| Periodic | 20 | 2.0 | 200 |
| Event-Driven | 61 | 2.0 | 610 |
| **Semantic (proposed)** | **35** | **2.0** | **550** |

Results are also written to `results/preliminary_results.csv`.

---

## The Three Policies

1. **Periodic baseline:** Reconciles every fixed interval (50 ticks), regardless of state change.
2. **Naive event-driven baseline:** Reconciles whenever any service's demand changes beyond a fixed threshold.
3. **Semantic freshness-aware (proposed):** Reconciles only when a change is *significant* and *persists* across multiple telemetry updates. Uses a moving-average Digital Twin to smooth transient noise.

---

## Reproduction Notes

- Random seed is fixed at `42` in `src/simulate_reconciliation.py` for reproducibility.
- Simulation parameters (thresholds, intervals, costs) are declared at the top of the script.
- The full research manuscript is maintained in Overleaf and will be linked here upon submission.

---

## License

This project is released for academic use. The EdgeSimPy dependency retains its own license (see the [EdgeSimPy repository](https://github.com/EdgeSimPy/edgesimpy)).

---

## Citation

If you reference this work, please cite the base article (EdgeSimPy) and this repository.

---

**Reproducibility:** The code and reproducibility materials for this study are publicly available at:  
https://github.com/msaeedsaeedi/Semantic-Freshness-Aware-Infrastructure-Reconciliation-for-Digital-Twins-in-Edge-Cloud-Kubernetes
