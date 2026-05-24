# Axiom v1.0.0 - Production Release

**Released:** 2026-05-24
**Tag:** v1.0.0
**Sprints:** 1-12 complete

---

## What is Axiom?

Axiom is a production-grade Clinical AI platform that delivers
per-patient causal treatment recommendations, ZK-verified outputs,
federated learning across hospital nodes, and a full clinical dashboard.

---

## Complete Feature List

### Backend Services (Sprints 1-7)

Sprint 1 - Data Ingestion
  50 synthetic patients, 5000 observations
  FHIR R4 adapter (Java Spring Boot, port 8080)
  Kafka streaming (7 topics, port 9094)
  PostgreSQL (port 5439) + MongoDB (port 27018)
  28 unit tests

Sprint 2 - Per-Patient Causal Engine
  DoWhy structural causal models
  Per-patient DAG: 11 edges for Amit Singh (CKD)
  Counterfactual simulation (Monte Carlo)
  ZK integrity proof per graph
  Build time: 212ms average
  Strongest edge: systolic_bp -> creatinine (0.0239)

Sprint 3 - ZK Trust Layer
  SHA-256 hash chain on every recommendation
  Tamper detection: corrupted hash instantly rejected
  Audit log in PostgreSQL
  15 unit tests

Sprint 4 - Federated Learning + Byzantine Detection
  Bulyan aggregation across 3 hospital nodes
  Hospital C detected and excluded
  Byzantine distance: 71.1 vs 36.6 honest average
  23 unit tests

Sprint 5 - Survival Model + RL
  Deep Cox proportional hazards, C-index 0.792
  PPO treatment policy, mean reward 3.16
  Amit Singh: 82% 30-day survival, 72-day median
  Recommendation: increase_lisinopril, zkProven=true
  25 unit tests

Sprint 6 - NLP + Anomaly Detection
  BioBERT clinical note extraction
  IsolationForest anomaly detector
  NLP edge added: furosemide -> creatinine (0.0375)
  31 unit tests

Sprint 7 - GraphQL + WebSocket + gRPC
  Apollo GraphQL gateway (port 4000)
  WebSocket subscriptions (port 4001)
  gRPC CausalService (port 50051)
  n8n workflows + Claude judgment service
  28 unit tests

Total backend: 150 unit tests, 0 failures

### Dashboard Screens (Sprints 8-10)

Sprint 8 - Command Centre Dashboard
  Landing page (HEAL.ELITE design system, Axiom brand)
  Login modal with spring animation
  Left panel: 8 patients, risk rings, pulsing deteriorating
  Centre panel: 4 D3 vital charts, 3s live updates, 60-point rolling
  Right panel: 3 causal recommendations, ZK badges, CI bars
  Alert banner: dismiss + view patient
  Bell notification panel
  17 dashboard tests

Sprint 9 - 3D Causal Graph + Counterfactual
  Three.js 3D graph: 7 nodes, 9 edges, particles
  Node glow, labels on hover, double-click fly-to
  Edge thickness = effect size, NLP edges orange
  Click edge: ZK proof + CI in left panel
  Counterfactual simulator: sliders, D3 violin plot
  1000 Monte Carlo samples, before/after survival curves
  37 UI tests

Sprint 10 - Population Atlas
  50-patient risk heatmap (D3 grid, 5 variables)
  Colour coding: critical/warning/normal/borderline
  Hover tooltips with sparklines
  Cohort causal graph: 15 nodes, 22 edges
  D3 force simulation, prevalence slider
  Edge hover tooltips, node click panel
  18 UI tests

Total UI tests: 72

### Infrastructure (Sprint 12)

  Production Dockerfiles: multi-stage, non-root, healthchecks
  docker-compose.prod.yml: resource limits, logging, healthchecks
  Kubernetes manifests: namespace, deployments, HPA, StatefulSets
  Ingress with TLS, NetworkPolicy
  Helm chart with values.yaml
  GitHub Actions: pr.yml + merge.yml + release.yml
  Prometheus: scrapes all 6 services
  Grafana: 3 dashboards (clinical-ops, ml-performance, infrastructure)
  Custom metrics: 7 histograms + 4 counters + 5 gauges
  Complete documentation: README, ARCHITECTURE, DEPLOYMENT, API_REFERENCE

---

## Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Causal Engine | 28 | 28 |
| ZK Trust Layer | 15 | 15 |
| Federated | 23 | 23 |
| Survival + RL | 25 | 25 |
| NLP + Anomaly | 31 | 31 |
| API Gateway | 28 | 28 |
| Dashboard | 17 | 17 |
| Sprint 9 UI | 37 | 37 |
| Sprint 10 UI | 18 | 18 |
| Total | 222 | 222 |

---

## Performance Benchmarks

| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| Causal graph build | 212ms | 380ms | 520ms |
| Survival prediction | 45ms | 89ms | 120ms |
| ZK proof generation | 8ms | 15ms | 22ms |
| Counterfactual | 340ms | 610ms | 820ms |
| Full analysis | 480ms | 750ms | 950ms |

---

## Key Clinical Results

Patient: Amit Singh, 58yr M, CKD
  Risk score: 0.9919 (HIGH)
  30-day survival: 82%
  Median survival: 72 days
  Recommendation: Increase Lisinopril
  Causal effect: -0.024 on creatinine
  ZK proof: a7a292cb...verified
  Causal drift: systolic_bp -> creatinine +29.7%
  Anomaly: creatinine predicted 4.41 mg/dL in 2h

Federated Network:
  Hospital A: reputation 0.80, Active
  Hospital B: reputation 0.80, Active
  Hospital C: reputation 0.29, Excluded (Byzantine)

---

## Sprint History

| Sprint | Feature | Version |
|--------|---------|---------|
| 1 | Data Ingestion | v0.1.0 |
| 2 | Causal Engine | v0.2.0 |
| 3 | ZK Trust Layer | v0.3.0 |
| 4 | Federated + Byzantine | v0.4.0 |
| 5 | Survival + RL | v0.5.0 |
| 6 | NLP + Anomaly | v0.6.0 |
| 7 | GraphQL + WebSocket + gRPC | v0.7.0 |
| 8 | Command Centre Dashboard | v0.8.0 |
| 9 | 3D Causal Graph + Counterfactual | v0.9.0 |
| 10 | Population Atlas | v0.10.0 |
| 12 | Kubernetes + CI/CD + Production | v1.0.0 |

---

## Author

Kshitij Srivastava
NIT Surat, 3rd Year Computer Science
CGPA: 6.14
Placement: August-September 2026
GitHub: github.com/Kshitij5486/Axiom
