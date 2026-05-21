# Axiom v0.3.0 — ZK Trust Layer

**Released:** 2026-05-21
**Sprint:** 3 of 12
**Days:** 15-21

---

## What Was Built

Sprint 3 adds cryptographic trust to every AI recommendation
Axiom makes. A doctor can verify any recommendation is
authentic without seeing patient data or model weights.

---

## Components

### ZK Service (Python FastAPI) — port 8084

ClinicalRecommendationProof: proves a recommendation came
from real patient data. Algorithm: sha256-composite-v1.
Components: patient_id_hash, recommendation_hash,
causal_effect_hash, graph_version_hash, composite_hash.

CausalGraphIntegrityProof: proves the causal graph was
not tampered with since it was built. Components:
edges_hash, effects_hash, graph_hash, integrity_proof.

Endpoints:
  POST /zk/proof/recommendation
  POST /zk/verify/recommendation
  POST /zk/proof/graph
  POST /zk/verify/graph
  POST /zk/doctor-verify
  GET  /zk/stats
  GET  /health

### Audit Trail — PostgreSQL

Every recommendation logged with full lineage:
  patient -> causal graph -> ZK proof ->
  recommendation -> doctor action -> audit log

Tables used: recommendations, audit_log
Endpoints:
  POST /audit/recommendation
  POST /audit/action
  GET  /audit/patient/{id}
  GET  /audit/recent

### ZK-Causal Engine Integration (Day 18)

Every causal graph build automatically:
  1. Generates ZK integrity proof via ZK service
  2. Stores proof in causal_graphs.zk_integrity_proof
  3. Returns proof hash in build API response

### PostgreSQL Schema Update (Day 19)

  ALTER TABLE causal_graphs
  ADD COLUMN zk_integrity_proof VARCHAR(256);

---

## Tamper Detection Proven (Day 17)

  Original hash:        98c56997...a7a0b27
  Tampered (00c56997):  valid=false  match=false
  Wrong effect (0.999): valid=false  match=false
  Valid proof:          valid=true   match=true

---

## Validation Results

  Proof generation:        valid=true
  Tampered hash:           valid=false
  Wrong causal effect:     valid=false
  ZK proof stored in DB:   graph 83ace297 proven
  Unit tests:              43 passed, 0 failed

---

## Test Summary

| Suite            | Tests | Passed | Failed | Time  |
|------------------|-------|--------|--------|-------|
| Causal Engine    | 28    | 28     | 0      | 1.80s |
| ZK Trust Layer   | 15    | 15     | 0      | 0.24s |
| Total            | 43    | 43     | 0      | 4.63s |

---

## Service Map

| Service       | Port  | Technology       | Sprint |
|---------------|-------|------------------|--------|
| FHIR Adapter  | 8080  | Java Spring Boot | 1      |
| Normalisation | 8086  | Python FastAPI   | 1      |
| Causal Engine | 8081  | Python FastAPI   | 2      |
| ZK Service    | 8084  | Python FastAPI   | 3      |
| PostgreSQL    | 5439  | postgres:15      | 1      |
| MongoDB       | 27018 | mongo:7          | 1      |
| Redis         | 6380  | redis:7          | 1      |
| Kafka         | 9094  | Confluent 7.4    | 1      |
| MinIO         | 9010  | minio:latest     | 1      |
| Prometheus    | 9095  | prom 2.45        | 1      |
| Grafana       | 3001  | grafana 10.1     | 1      |

---

## Next Sprint

Sprint 4 — Federated Learning + Byzantine Aggregation
  3 simulated hospital nodes train locally
  Bulyan Byzantine-fault-tolerant aggregation
  No patient data leaves any hospital
  Only gradients shared across nodes
  Reputation scoring per hospital node