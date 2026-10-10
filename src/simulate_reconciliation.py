"""
Semantic Freshness-Aware Reconciliation Simulation
Preliminary proof-of-concept for three policies:
  1. Periodic baseline
  2. Naive event-driven baseline
  3. Semantic freshness-aware (proposed)
"""

import random
import numpy as np
import pandas as pd

SIM_TIME = 1000
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

NUM_SERVERS = 6
NUM_SERVICES = 6
BASE_CPU_DEMAND = 20.0
DEMAND_DRIFT_STD = 0.5
SUSTAINED_JUMP_PROB = 0.01
TRANSIENT_SPIKE_PROB = 0.03
TRANSIENT_DURATION = 2

TELEMETRY_INTERVAL = 5

RECONCILIATION_COST = 10
SEMANTIC_EVAL_COST = 1

PERIODIC_INTERVAL = 50
EVENT_THRESHOLD = 5.0
FRESHNESS_THRESHOLD = 3
SIGNIFICANCE_THRESHOLD = 4.0
CONFIRMATION_TICKS = 3


class Service:
    def __init__(self, sid):
        self.id = sid
        self.true_cpu_demand = BASE_CPU_DEMAND
        self.transient_counter = 0

    def step(self):
        self.true_cpu_demand += random.gauss(0, DEMAND_DRIFT_STD)
        if random.random() < SUSTAINED_JUMP_PROB:
            self.true_cpu_demand += random.choice([-8, 8])
        if self.transient_counter > 0:
            self.transient_counter -= 1
            if self.transient_counter == 0:
                self.true_cpu_demand -= 10
        elif random.random() < TRANSIENT_SPIKE_PROB:
            self.true_cpu_demand += 10
            self.transient_counter = TRANSIENT_DURATION
        self.true_cpu_demand = max(1.0, min(60.0, self.true_cpu_demand))


class DigitalTwin:
    """A sampled, possibly-stale view of the physical state.
    Reports a moving average of recent telemetry to filter short spikes."""

    def __init__(self, services, window=3):
        self.services = services
        self.history = {s.id: [] for s in services}
        self.dt_demand = {s.id: s.true_cpu_demand for s in services}
        self.last_update = {s.id: 0 for s in services}
        self.window = window

    def update(self, tick):
        for s in self.services:
            self.history[s.id].append(s.true_cpu_demand)
            if len(self.history[s.id]) > self.window:
                self.history[s.id].pop(0)
            # The DT reports the moving average, not the raw last value
            self.dt_demand[s.id] = sum(self.history[s.id]) / len(self.history[s.id])
            self.last_update[s.id] = tick

    def aoi(self, sid, tick):
        return tick - self.last_update[sid]

def periodic_policy(twin, tick, state):
    return tick % PERIODIC_INTERVAL == 0


def event_driven_policy(twin, tick, state):
    for sid in state["last_reconciled"]:
        change = abs(twin.dt_demand[sid] - state["last_reconciled"][sid])
        if change > EVENT_THRESHOLD:
            return True
    return False


def semantic_policy(twin, tick, state):
    """
    Reconcile only when:
      (a) the change is significant AND
      (b) it has persisted for CONFIRMATION_TICKS *telemetry updates*
      (c) the DT is fresh enough that we trust the reading (AoI low)
    """
    # Only evaluate at telemetry boundaries
    if tick % TELEMETRY_INTERVAL != 0:
        return False

    state["overhead"] += SEMANTIC_EVAL_COST

    trigger = False
    for sid in state["last_reconciled"]:
        change = abs(twin.dt_demand[sid] - state["last_reconciled"][sid])

        if change > SIGNIFICANCE_THRESHOLD:
            state["pending_confirmations"][sid] += 1
        else:
            state["pending_confirmations"][sid] = 0

        if state["pending_confirmations"][sid] >= CONFIRMATION_TICKS:
            trigger = True

    if trigger:
        # Reset counters so we don't re-trigger on the same change
        for sid in state["last_reconciled"]:
            state["pending_confirmations"][sid] = 0

    return trigger


def run_experiment(policy_name, policy_fn):
    services = [Service(i) for i in range(1, NUM_SERVICES + 1)]
    twin = DigitalTwin(services)
    state = {
        "last_reconciled": {s.id: s.true_cpu_demand for s in services},
        "pending_confirmations": {s.id: 0 for s in services},
        "overhead": 0,
    }
    reconciliations = 0
    total_aoi = 0
    for tick in range(SIM_TIME):
        for s in services:
            s.step()
        if tick % TELEMETRY_INTERVAL == 0:
            twin.update(tick)
        for s in services:
            total_aoi += twin.aoi(s.id, tick)
        if policy_fn(twin, tick, state):
            reconciliations += 1
            state["overhead"] += RECONCILIATION_COST
            for s in services:
                state["last_reconciled"][s.id] = twin.dt_demand[s.id]
                state["pending_confirmations"][s.id] = 0
    avg_aoi = total_aoi / (SIM_TIME * NUM_SERVICES)
    return {
        "Policy": policy_name,
        "Reconciliations": reconciliations,
        "Avg AoI (ticks)": round(avg_aoi, 2),
        "Total Overhead": state["overhead"],
        "IoT Energy (arb. units)": SIM_TIME * NUM_SERVICES,
    }


if __name__ == "__main__":
    results = [
        run_experiment("Periodic",    periodic_policy),
        run_experiment("EventDriven", event_driven_policy),
        run_experiment("Semantic",    semantic_policy),
    ]
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    df.to_csv("results/preliminary_results.csv", index=False)
    print("\nSaved to results/preliminary_results.csv")