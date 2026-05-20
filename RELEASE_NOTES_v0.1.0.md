# Axiom v0.1.0 — Data Ingestion Layer

**Released:** 2026-05-20
**Sprint:** 1 of 12
**Days:** 7

---

## What Was Built

Sprint 1 establishes the complete data ingestion foundation
for Axiom. Every subsequent sprint builds on this layer.

---

## Components

### FHIR Adapter (Java Spring Boot) — port 8080
Ingests HL7 FHIR R4 patient records from any EHR system.
Supports Patient and Observation resources. Publishes every
ingested event to Kafka for downstream processing.

Endpoints:
  GET  /fhir/health
  POST /fhir/patient
  POST /fhir/observation
  GET  /fhir/patients
  GET  /actuator/prometheus

### Normalisation Service (Python FastAPI) — port 8086
Consumes raw clinical events from Kafka and normalises them:
  - LOINC code → clinical feature name (30 mappings)
  - Unit conversion (15 conversion rules)
  - Reference range abnormality detection
  - Publishes normalised events to patient.vitals.normalised

Endpoints:
  GET  /health
  GET  /stats
  GET  /metrics
  POST /normalise

### PostgreSQL — port 5439
7 tables: patients, observations, medications, conditions,
causal_graphs, recommendations, audit_log
7 indexes for query performance

### MongoDB — port 27018
4 collections: clinical_notes, imaging_metadata,
nlp_extractions, alert_history
Full-text index on clinical notes content

### Kafka — port 9094
7 topics:
  patient.events          (6 partitions)
  patient.vitals          (6 partitions)
  patient.labs            (6 partitions)
  patient.medications     (6 partitions)
  causal.updates          (6 partitions)
  alerts.clinical         (3 partitions)
  patient.vitals.normalised (auto-created)

### Prometheus — port 9095
Scrapes FHIR adapter and normalisation service metrics.
15-day retention.

### Grafana — port 3001
Prometheus datasource auto-provisioned.
Login: admin / axiom123

---

## Validation Results

  Patients ingested:          50
  Observations ingested:      5000
  Messages normalised:        5000
  Normalisation failures:     0
  Clinical notes (MongoDB):   53
  Kafka topics:               7
  Docker containers:          8

---

## Data Pipeline
EHR System (FHIR R4 JSON)
→ FHIR Adapter (Java Spring Boot)
→ PostgreSQL (patients + observations)
→ Kafka: patient.vitals
→ Normalisation Service (Python)
→ LOINC mapping + unit conversion
→ Abnormality detection
→ Kafka: patient.vitals.normalised
→ PostgreSQL (feature_name + is_abnormal)
→ MongoDB (clinical notes)

---

## Service Map

| Service              | Port  | Technology          |
|----------------------|-------|---------------------|
| FHIR Adapter         | 8080  | Java Spring Boot    |
| Normalisation        | 8086  | Python FastAPI      |
| PostgreSQL           | 5439  | postgres:15-alpine  |
| MongoDB              | 27018 | mongo:7             |
| Redis                | 6380  | redis:7-alpine      |
| Zookeeper            | 2182  | cp-zookeeper:7.4.0  |
| Kafka                | 9094  | cp-kafka:7.4.0      |
| MinIO                | 9010  | minio:latest        |
| Prometheus           | 9095  | prom/prometheus     |
| Grafana              | 3001  | grafana:10.1.0      |

---

## Next Sprint

Sprint 2 — Per-Patient Causal Graph (Days 8-14)
  Build individual causal DAG per patient using DoWhy.
  The same causal inference engine from CognitiveMesh,
  applied to patients instead of database nodes.