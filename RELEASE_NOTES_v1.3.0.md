# Axiom v1.3.0 — Medical IoT Device Graph + AI Cross-Correlation Engine

**Date:** 2026-05-24
**Sprint:** 15
**Days:** 81-83
**Tests:** 267 passed, 0 failed

---

## What Was Built

Sprint 15 adds the most technically unique components of Axiom Sentinel:
the Medical IoT Device Graph and AI Cross-Correlation Engine.

---

## sentinel-graph-service (Port 8091)

Python FastAPI microservice using NetworkX + DoWhy-style causal inference
to build an infrastructure causal graph of hospital network devices.

### Device Fingerprinting
- Consumes network.flows and sentinel.devices Kafka topics
- Builds per-device profile: ports, SNI domains, peers, bytes, packet count
- PostgreSQL table sentinel_devices with traffic_profile JSONB
- Persists device profiles with ON CONFLICT upsert

### Infrastructure Causal Graph
- NetworkX DiGraph: nodes=devices, edges=communication relationships
- Edge effect_size = communication frequency ratio
- Incremental rebuild every 30 minutes
- PostgreSQL table sentinel_graph with adjacency matrix

### REST API
- GET /health
- GET /sentinel/graph/infrastructure — full DAG
- GET /sentinel/graph/device/{ip} — causal neighbourhood
- POST /sentinel/graph/counterfactual — BFS propagation prediction
- GET /sentinel/graph/devices — all known devices

---

## sentinel-correlator (Port 8092)

Python FastAPI microservice consuming 3 Kafka topics simultaneously
with a 5-minute sliding window correlation engine.

### 4 Correlation Rules

Rule 1 — DEVICE_COMPROMISE_CLINICAL_IMPACT
  Medical device trust score < 0.5 AND same patient anomaly
  in 5-minute window. Jaccard similarity confidence score.
  Calls PATCH /causal/graph/{patient_id}/flag-source to
  attenuate compromised device edge weights in causal graph.

Rule 2 — RANSOMWARE_PATIENT_RISK
  CRITICAL ransomware threat in hospital segment AND devices
  linked to active patients. Lists all at-risk patient IDs.

Rule 3 — FEDERATED_POISONING_CLINICAL_IMPACT
  FEDERATED_ATTACK event AND widened confidence intervals
  in patient recommendations. Queries causal engine for CI changes.

Rule 4 — DEVICE_COMPROMISE_PROPAGATION
  Device trust < 0.3 → calls graph counterfactual → predicts
  which patient-facing devices are next to be compromised.
  Pre-emptive alerts for affected patients.

### Clinical Pipeline Feedback
- PATCH /causal/graph/{patient_id}/flag-source
- Confidence penalty = 1.0 - trust_score
- Causal graph edge weights attenuated for compromised devices
- System heals its own data trust automatically

### REST API
- GET /sentinel/correlations
- GET /sentinel/correlations/patient/{patient_id}
- GET /sentinel/risk/patients (sorted by risk score)

---

## Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Backend Sprints 1-7 | 150 | 150 |
| Dashboard Sprints 8-10 | 72 | 72 |
| Sentinel v1 | 10 | 10 |
| Sentinel v2 | 20 | 20 |
| Sentinel v3 | 15 | 15 |
| Total | 267 | 267 |
