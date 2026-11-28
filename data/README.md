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
- **Role in this project:** Defines the edge topology and workload scale for Phase 2 (`src/edgesimpy_experiment.py`): 6 edge servers and 6 services. The same seeded synthetic demand traces used in Phase 1 (`src/phase1_experiment.py`) drive the services. Because the dataset has one service per server, Phase 2 confines placement to 3 of the 6 servers (two services each) so that migration can change load balance.
