"""
Phase 2 (v2): the same three policies inside the EdgeSimPy simulator.
- Topology: data/sample_dataset2.json (6 edge servers, 6 services, 16 switches, 33 links ...)
- Workload: the SAME seeded traces as Phase 1 (imported from phase1_experiment.py)
- Policies: periodic, naive event-driven (raw telemetry), persistence (proposed)
- Placement uses 3 of the 6 servers (ACTIVE); load imbalance = max server load - mean load.
- A reconciliation = refresh the twin's state of one service and, if it helps, migrate it
  to the server with the lowest believed load.
Run everything (several minutes, parallel on multi-core PCs):  python src/edgesimpy_experiment.py
Run one case:                      python src/edgesimpy_experiment.py --one persistence spiky 0
Output: results/edgesimpy_results.csv
"""
import sys, os, json, math, subprocess, warnings
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase1_experiment import make_trace, WORKLOADS, T, S, BASE, TELE, THR, CONF   # shared settings

DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_dataset2.json"))
N_SEEDS = 10
ACTIVE = (1, 2, 3)   # placement is confined to 3 of the 6 servers (2 services each) so that
                     # load balancing is a real problem; with 1 service per server no move can help.


def run_one(policy, workload, seed, interval=50):
    from edge_sim_py import Simulator, Service, EdgeServer
    sust, true, _ = make_trace(seed, *WORKLOADS[workload])
    st = dict(last=sust[0].copy(), pend=np.zeros(S, int), dt=np.full(S, BASE),
              recs=0, migs=0, gap=0.0, imb=0.0, n=0, target={})

    def home(x):                                             # where x is, or is about to be (pending migration)
        if x.server is None: return None
        return st["target"][x.id] if (x.being_provisioned and x.id in st["target"]) else x.server.id

    def believed_load(server_id, exclude=None):
        return sum(st["last"][x.id - 1] for x in Service.all()
                   if home(x) == server_id and x.id != exclude)

    def reconcile(svc, fresh):
        st["recs"] += 1
        st["last"][svc.id - 1] = fresh                      # twin state refreshed
        cur = home(svc)
        best, best_load = None, None
        for e in [e for e in EdgeServer.all() if e.id in ACTIVE]:
            if e.id != cur and e.has_capacity_to_host(service=svc):
                l = believed_load(e.id, exclude=svc.id)
                if best is None or l < best_load: best, best_load = e, l
        d = st["last"][svc.id - 1]
        if best is not None and best_load + d < believed_load(cur):   # only if it improves balance
            st["target"][svc.id] = best.id
            svc.provision(target_server=best); st["migs"] += 1

    def algo(parameters):
        t = sim.schedule.steps
        if t >= T: return
        if t == 0:                                           # identical round-robin placement for all policies
            servers = [e for e in EdgeServer.all() if e.id in ACTIVE]
            for k, svc in enumerate(Service.all()):
                for j in range(len(servers)):
                    e = servers[(k + j) % len(servers)]
                    if e.has_capacity_to_host(service=svc):
                        svc.provision(target_server=e); break
            return
        if t % TELE == 0: st["dt"] = true[t].copy()          # raw telemetry sample (twin)
        ready = [x for x in Service.all() if x.server is not None and not x.being_provisioned]
        if policy == "periodic" and t % interval == 0:
            fire = {x.id for x in ready}
        elif policy == "event":
            fire = {x.id for x in ready if abs(st["dt"][x.id-1] - st["last"][x.id-1]) > THR}
        elif policy == "persistence" and t % TELE == 0:
            for x in Service.all():
                i = x.id - 1
                st["pend"][i] = st["pend"][i] + 1 if abs(st["dt"][i] - st["last"][i]) > THR else 0
            fire = {x.id for x in ready if st["pend"][x.id-1] >= CONF}
        else:
            fire = set()
        for x in ready:
            if x.id in fire:
                st["pend"][x.id-1] = 0; reconcile(x, st["dt"][x.id-1])
        placed = [x for x in Service.all() if x.server is not None]
        if len(placed) == S:                                 # metrics on true sustained demand
            st["gap"] += float(np.mean(np.abs(st["last"] - sust[t])))
            loads = {e.id: 0.0 for e in EdgeServer.all() if e.id in ACTIVE}
            for x in placed: loads[home(x)] += sust[t][x.id - 1]
            v = list(loads.values()); st["imb"] += max(v) - float(np.mean(v)); st["n"] += 1

    sim = Simulator(tick_duration=1, tick_unit="seconds",
                    stopping_criterion=lambda m: m.schedule.steps >= T,
                    resource_management_algorithm=algo)
    sim.initialize(input_file=DATASET)
    sim.run_model()
    n = max(st["n"], 1)
    return dict(policy=policy, workload=workload, seed=seed, recs=st["recs"], migrations=st["migs"],
                sustained_gap=st["gap"] / n, load_imbalance=st["imb"] / n, ticks_measured=st["n"])


def spawn(policy, workload, seed, interval=50):
    out = subprocess.run([sys.executable, __file__, "--one", policy, workload, str(seed), str(interval)],
                         capture_output=True, text=True)
    try: return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception: raise RuntimeError(out.stderr[-800:])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one":          # one isolated run (fresh simulator state)
        iv = int(sys.argv[5]) if len(sys.argv) > 5 else 50
        print(json.dumps(run_one(sys.argv[2], sys.argv[3], int(sys.argv[4]), iv)))
        sys.exit(0)
    import pandas as pd
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1))   # each run is its own process
    rows = []
    for w in WORKLOADS:
        sem = list(pool.map(lambda s: spawn("persistence", w, s), range(N_SEEDS))); rows += sem
        Tm = min(range(5, 101), key=lambda k: abs(S * math.ceil(T / k) - np.mean([r["recs"] for r in sem])))
        jobs = [("event", s, 50) for s in range(N_SEEDS)] + [("periodic", s, 50) for s in range(N_SEEDS)] \
             + [("periodic_matched", s, Tm) for s in range(N_SEEDS)]
        def go(j, w=w):
            pol, s, iv = j
            r = spawn("periodic" if pol.startswith("periodic") else pol, w, s, iv); r["policy"] = pol; return r
        rows += list(pool.map(go, jobs))
        print("done", w, "(matched periodic T =", Tm, ")", flush=True)
    df = pd.DataFrame(rows); df.to_csv("results/edgesimpy_results.csv", index=False)
    cols = ["recs", "migrations", "sustained_gap", "load_imbalance"]
    tab = df.groupby(["workload", "policy"])[cols].agg(["mean", "std"]).round(2)
    print(tab.to_string())
    print("Saved results/edgesimpy_results.csv (figures: python src/make_figures.py)")
