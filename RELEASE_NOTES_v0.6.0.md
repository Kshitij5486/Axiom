# Axiom v0.6.0 — BioBERT NLP + Anomaly Detection

**Released:** 2026-05-22
**Sprint:** 6 of 12
**Days:** 36-42

---

## What Was Built

Sprint 6 adds two intelligence layers:
  1. Clinical NLP — reads doctor notes, extracts entities
     and causal relations, enriches the causal DAG
  2. Anomaly Detection — watches vital sign streams,
     predicts threshold breaches 2 hours in advance

---

## Component 1: NLP Pipeline (port 8083)

### Entity Extractor
  Dictionary NER (fast, <3ms):
    50 condition terms (SNOMED-CT subset)
    25 drug names (RxNorm subset)
    10 vital sign patterns (regex)
    15 symptom terms
  BioBERT (d4data/biomedical-ner-all) with fallback

  Tested on Amit Singh note:
    CONDITION: diabetes_mellitus (confidence 0.90)
    VITAL:     blood_pressure 123/72 mmHg (0.95)
    VITAL:     creatinine 1.0 mg/dL (0.95)

### Relation Extractor
  Causal pattern extraction from free text:
    "X rose after Y"         → Y causes X
    "Y reduced X"            → Y improves X
    "poorly compliant with Y" → non_compliant
  
  Tested: "creatinine rose after furosemide"
    → furosemide->creatinine causes confidence=0.75

### Incremental DAG Updater
  EWMA update: new = 0.3*nlp + 0.7*old
  No full DoWhy rebuild (saves 20 seconds)
  New NLP edges flagged: nlp_source=true
  
  Result: furosemide->creatinine added to Amit Singh
  graph (effect=0.0375) — 11 edges total (10 DoWhy + 1 NLP)

---

## Component 2: Anomaly Detector

### Isolation Forest
  Per-patient model trained on own vital history
  20 readings, 5 features, contamination=0.1
  Score = -1 means anomaly detected

### 2-Hour Predictive Alert
  Linear regression on last 5 readings
  Extrapolates to t+120 minutes
  Fires if extrapolated value crosses threshold
  
  Tested for Amit Singh:
    creatinine current: 4.0 mg/dL
    creatinine predicted (2h): 4.41 mg/dL
    slope: +0.42 mg/dL/hour
    threshold: 3.5 mg/dL → PREDICTIVE alert

### Alert Pipeline
  MongoDB: alert_history stored
  Kafka: alerts.clinical published
  ZK proof per alert (Sprint 3)
  WebSocket: ws://localhost:8083/ws/alerts

---

## API Endpoints (port 8083)

  POST /nlp/extract/{patient_id}    entity extraction
  POST /nlp/relations/{patient_id}  causal relations
  POST /nlp/enrich/{patient_id}     DAG update
  POST /anomaly/train/{patient_id}  train IF model
  POST /anomaly/score/{patient_id}  score vitals
  POST /anomaly/scan/{patient_id}   full pipeline
  GET  /anomaly/alerts/{patient_id} get alerts
  WS   /ws/alerts                   WebSocket stream

---

## Test Summary

| Suite            | Tests | Passed | Failed | Time   |
|------------------|-------|--------|--------|--------|
| Causal Engine    | 28    | 28     | 0      | —      |
| ZK Trust Layer   | 15    | 15     | 0      | —      |
| Federated        | 23    | 23     | 0      | —      |
| Survival + RL    | 25    | 25     | 0      | —      |
| NLP + Anomaly    | 31    | 31     | 0      | —      |
| Total            | 122   | 122    | 0      | 20.05s |

---

## Service Map

| Service        | Port  | Technology        | Sprint |
|----------------|-------|-------------------|--------|
| FHIR Adapter   | 8080  | Java Spring Boot  | 1      |
| Normalisation  | 8086  | Python FastAPI    | 1      |
| Causal Engine  | 8081  | Python FastAPI    | 2      |
| ZK Service     | 8084  | Python FastAPI    | 3      |
| Federated      | 8085  | Python FastAPI    | 4      |
| Survival       | 8082  | Python FastAPI    | 5      |
| NLP            | 8083  | Python FastAPI    | 6      |
| PostgreSQL     | 5439  | postgres:15       | 1      |
| MongoDB        | 27018 | mongo:7           | 1      |
| Redis          | 6380  | redis:7           | 1      |
| Kafka          | 9094  | Confluent 7.4     | 1      |
| Prometheus     | 9095  | prom 2.45         | 1      |
| Grafana        | 3001  | grafana 10.1      | 1      |

---

## Next Sprint

Sprint 7 — GraphQL + WebSocket + gRPC APIs
  Unified GraphQL API over all services
  Real-time WebSocket subscriptions
  gRPC for inter-service communication
  API gateway pattern