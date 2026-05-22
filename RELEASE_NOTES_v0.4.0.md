# Axiom v0.4.0 — Federated Learning + Byzantine Aggregation

**Released:** 2026-05-22
**Sprint:** 4 of 12
**Days:** 22-28

---

## What Was Built

Sprint 4 adds federated learning across simulated hospital
nodes. Multiple hospitals train causal models locally and
share only gradients — no patient data ever transmitted.
Byzantine-fault-tolerant aggregation detects and excludes
compromised nodes automatically.

---

## Architecture
Hospital A (17 patients)    Hospital B (17 patients)    Hospital C (17 patients)
Local OLS causal model      Local OLS causal model      Local OLS causal model
Gaussian DP noise           Gaussian DP noise           Gaussian DP noise
|                           |                           |
└───────────────────────────┴───────────────────────────┘
|
Bulyan Byzantine Aggregator
pairwise L2 distance detection
outlier exclusion
|
FederatedCoordinator
global weight update
PostgreSQL audit log
|
ReputationScorer
per-node score 0.0-1.0
auto-exclusion below 0.3
|
Causal Engine
alpha blending of local + federated

---

## Components

### HospitalNode (Day 23)
Simulates a hospital federated learning client.
Partitions 50 patients across 3 nodes (17 each).
Trains local OLS causal model on 6 causal pairs.
Applies Gaussian DP noise: sigma = 1.1 * clip_norm.
Returns DP-noised gradient vector.

### ByzantineAggregator — Bulyan Algorithm (Day 24)
Pairwise L2 distance between gradient vectors.
Sorts nodes by total distance, selects n-2f closest.
Coordinate-wise trimmed mean on selected nodes.
Detects sign_flip attack: distance 57.02 vs ~30 honest.

### FederatedCoordinator (Day 25)
Orchestrates complete federation rounds.
Collects gradients from all nodes.
Runs Bulyan aggregation.
Updates global model weights (lr=0.1).
Stores round in PostgreSQL audit_log.

### ReputationScorer (Day 26)
Tracks per-node trustworthiness across rounds.
reward=0.1, penalty=0.2, initial=0.7.
Auto-excludes nodes below score 0.3.
hospital-3 excluded after 4 Byzantine rounds:
  score trajectory: 0.70 -> 0.56 -> 0.448 -> 0.3584 -> 0.2867

### Federated-Causal Integration (Day 27)
Global weights fetched by causal engine after each build.
Alpha blending: alpha = min(1.0, n_observations / 20)
  n=20: pure local estimate (alpha=1.0)
  n=10: 50% local + 50% federated (alpha=0.5)
  n=0:  pure federated prior (cold start)
blended=true flag in effect_sizes.

---

## Byzantine Attack Results

  Normal round:
    hospital-3 distance: 9.53 (slightly furthest)
    rejected: hospital-3

  Sign-flip attack (x-10):
    hospital-3 distance: 57.02 vs 30.1/30.8 honest
    rejected: hospital-3  (detected) ✓

  After 4 attack rounds:
    hospital-3 score:  0.2867 (below 0.3 threshold)
    hospital-3 status: EXCLUDED ✓
    active_nodes: [hospital-1, hospital-2]

---

## Differential Privacy

  noise_multiplier: 1.1
  clip_norm:        1.0
  sigma:            1.1

  Each gradient vector clipped to L2 norm <= 1.0
  then Gaussian noise N(0, 1.21) added per dimension.
  Satisfies (epsilon, delta)-DP guarantees.

---

## Validation Results

  Hospital nodes:          3
  Patients per node:       17
  Federation rounds run:   4 (with attack)
  Byzantine detected:      yes (round 1-4)
  Node auto-excluded:      hospital-3
  Unit tests:              66 passed, 0 failed

---

## Test Summary

| Suite            | Tests | Passed | Failed | Time  |
|------------------|-------|--------|--------|-------|
| Causal Engine    | 28    | 28     | 0      | —     |
| ZK Trust Layer   | 15    | 15     | 0      | —     |
| Federated        | 23    | 23     | 0      | —     |
| Total            | 66    | 66     | 0      | 3.03s |

---

## Service Map

| Service        | Port  | Technology       | Sprint |
|----------------|-------|------------------|--------|
| FHIR Adapter   | 8080  | Java Spring Boot | 1      |
| Normalisation  | 8086  | Python FastAPI   | 1      |
| Causal Engine  | 8081  | Python FastAPI   | 2      |
| ZK Service     | 8084  | Python FastAPI   | 3      |
| Federated      | 8085  | Python FastAPI   | 4      |
| PostgreSQL     | 5439  | postgres:15      | 1      |
| MongoDB        | 27018 | mongo:7          | 1      |
| Redis          | 6380  | redis:7          | 1      |
| Kafka          | 9094  | Confluent 7.4    | 1      |
| Prometheus     | 9095  | prom 2.45        | 1      |
| Grafana        | 3001  | grafana 10.1     | 1      |

---

## Next Sprint

Sprint 5 — Survival Model + RL Treatment Optimiser
  Deep Cox proportional hazards (PyTorch)
  PPO treatment policy (Stable Baselines3)
  Patient survival curves per causal graph
  RL agent learns optimal treatment sequences