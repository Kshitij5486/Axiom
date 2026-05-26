# Axiom v2.0.0 — Production Release

**Date:** 2026-05-26
**Sprint:** 17 (Days 91-97)
**Tests:** 284 passed, 0 failed

---

## What's New in v2.0.0

### Sprint 17 — Production Hardening + ZK Extension

#### Day 91 — Sentinel Kubernetes Helm Charts
- DaemonSet for sentinel-sensor (privileged, hostNetwork, NET_ADMIN/NET_RAW)
- Deployments for sentinel-control-plane, sentinel-graph-service, sentinel-correlator
- NetworkPolicies restricting all service-to-service communication
- Istio AuthorizationPolicy (admin + security_analyst RBAC only)
- PodDisruptionBudget (minAvailable: 1)
- Chart.yaml v2.0.0, values.yaml with full configuration

#### Day 92 — ZK Proof Extension (3 new types)
- NetworkIntegrityProof: Merkle root of FlowEvent Kafka batch
- FederatedTrafficProof: gradient hashes + volume profile + timing
- DeviceTrustProof: evidence-based trust score reconstruction
- All 3 verified correct (generate → verify roundtrip)
- 6 new API endpoints on zk-service
- PostgreSQL zk_audit_trail table extended

#### Day 93 — Prometheus + Grafana
- Scrape configs for sentinel-control-plane(:9182), graph-service(:8091),
  correlator(:8092), zk-service(:8085)
- 5th Grafana dashboard: Sentinel Security Operations
  - Threats/hr by type (stacked bar)
  - Blocked IPs over time (area chart)
  - Device trust score distribution (histogram)
  - Federated anomaly rate per round (line chart)
  - Correlation events/hr by type (bar chart)
  - Top 10 most-threatened devices (table)
  - Geo-IP threat origin world map (geomap)
  - ZK proof generation rate (line chart)

#### Day 94 — Integration Tests
- 17 new integration tests across 5 scenarios
- Scenario 1: SYN flood → HIGH threat within 3s + iptables block
- Scenario 2: Malicious SNI → CRITICAL + immediate block
- Scenario 3: Medical device 10x spike → COMPROMISED_SUSPECTED
- Scenario 4: Unregistered federated node → FEDERATED_ATTACK + Byzantine flag
- Scenario 5: Patient anomaly + LOW_TRUST device → correlation within 10s
- 17/17 passing

#### Day 95 — README + Documentation
- Complete README.md with ASCII architecture diagram (17 services, 8 layers)
- Local dev setup (docker compose up)
- Production deployment (helm install)
- Sentinel sensor deployment guide
- ZK proof verification guide
- Interview talking points

---

## Cumulative Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Backend Sprints 1-7 | 150 | 150 |
| Dashboard Sprints 8-10 | 72 | 72 |
| Sentinel unit v1 | 10 | 10 |
| Sentinel unit v2 | 20 | 20 |
| Sentinel unit v3 | 15 | 15 |
| Sentinel integration | 17 | 17 |
| Total | 284 | 284 |

---

## Complete Sprint History

| Sprint | Feature | Version | Days |
|--------|---------|---------|------|
| 1 | FHIR + Kafka + PostgreSQL | v0.1.0 | 1-7 |
| 2 | Causal Engine (DoWhy) | v0.2.0 | 8-14 |
| 3 | ZK Trust Layer | v0.3.0 | 15-21 |
| 4 | Federated + Byzantine | v0.4.0 | 22-28 |
| 5 | Survival + RL | v0.5.0 | 29-35 |
| 6 | NLP + Anomaly Detection | v0.6.0 | 36-42 |
| 7 | GraphQL + WebSocket + gRPC | v0.7.0 | 43-49 |
| 8 | Command Centre Dashboard | v0.8.0 | 50-56 |
| 9 | 3D Causal Graph | v0.9.0 | 57-63 |
| 10 | Population Atlas | v0.10.0 | 64-69 |
| 12 | Kubernetes + CI/CD | v1.0.0 | 64-69 |
| 13 | Sentinel C++ + Go | v1.2.0 | 70-80 |
| 15 | IoT Graph + Correlator | v1.3.0 | 81-83 |
| 16 | Sentinel SOC Dashboard | v1.4.0 | 84-90 |
| 17 | Production + ZK + v2.0.0 | v2.0.0 | 91-97 |
