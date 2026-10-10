# Datasets

## sample_dataset2.json

- **Source:** EdgeSimPy official tutorials repository
- **URL:** https://raw.githubusercontent.com/EdgeSimPy/edgesimpy-tutorials/master/datasets/sample_dataset2.json
- **Type:** Edge-cloud topology and workload configuration
- **Contents:**
  - 16 NetworkSwitches
  - 33 NetworkLinks
  - 16 BaseStations
  - 6 EdgeServers
  - 6 Users
  - 6 Services (containerized workloads)
  - 6 Applications
- **Role in this project:** Defines the physical topology and workload scale for our semantic freshness-aware reconciliation experiments. The preliminary simulator (`src/simulate_reconciliation.py`) uses the same scale (6 servers, 6 services) with synthetic demand traces layered on top.