# Axiom v0.7.0 — GraphQL + WebSocket + gRPC API Layer

**Released:** 2026-05-22
**Sprint:** 7 of 12
**Days:** 43-49

---

## What Was Built

Sprint 7 adds the complete API layer connecting all
services built in Sprints 1-6. One unified GraphQL
endpoint replaces 7 separate REST APIs for the frontend.

---

## Component 1: Apollo GraphQL Gateway (port 4000)

Technology: Node.js + Apollo Server 5

Queries implemented:
  health()              service status
  fullAnalysis()        parallel fetch all services
  causalGraph()         causal engine
  survival()            Cox model
  recommendation()      PPO policy
  alerts()              anomaly detector
  nlpEntities()         BioBERT extraction
  nlpRelations()        causal relations
  federatedStatus()     Byzantine reputation

Mutations:
  buildCausalGraph()    trigger rebuild
  enrichFromNotes()     NLP DAG update
  runAnomalyScan()      anomaly pipeline
  runFederatedRound()   federation

Tested query result for Amit Singh:
  nodeCount=7  edgeCount=10
  riskScore=0.9919  medianSurvival=72d
  action=increase_lisinopril  zkProven=true

---

## Component 2: WebSocket Subscriptions (port 4001)

Technology: graphql-ws + ws

Subscriptions:
  patientAlerts(patientId)     live alerts
  vitalUpdates(patientId)      live vitals
  causalDrift(patientId)       graph changes
  collaborativeSession(id)     multi-doctor

PubSub: in-memory EventEmitter
Kafka consumer: routes alerts.clinical to PubSub
Test alert publish: POST /test/alert/:patientId

---

## Component 3: gRPC Inter-Service (port 50051)

Technology: Python grpcio 1.80.0

Services defined in axiom.proto:
  CausalService    port 50051 (Python)
  ZKBridgeService  port 50052 (Rust)
  SurvivalService  port 50053 (Python)
  FederatedService port 50054 (Rust)
  AlertService     embedded in NLP

CausalService tested:
  GetGraph: success=True nodeCount=7 edgeCount=11
  ZK proof: a7a292cb... verified via gRPC

---

## Component 4: n8n Orchestration

4 workflows defined in services/n8n/workflows.json:

  Workflow 1: New Vital Received
    Kafka trigger → anomaly scan →
    Claude triage → WebSocket broadcast

  Workflow 2: Causal Drift Detection
    drift event → Claude judgment →
    if significant → alert doctor

  Workflow 3: New Clinical Note NLP
    MongoDB trigger → NLP extract →
    DAG update → ZK proof → audit

  Workflow 4: Federated Round
    schedule (6h) → collect gradients →
    Byzantine check → global model update

---

## Component 5: Claude Judgment Service (port 8090)

4 clinical reasoning endpoints:
  POST /judge/causal-drift
  POST /judge/conflicting-recommendations
  POST /judge/alert-triage
  POST /judge/treatment-coherence

n8n OWNS: routing, scheduling, HTTP calls,
          Kafka, MongoDB, audit triggers
Claude OWNS: clinical significance judgment,
             conflict resolution, alert triage,
             treatment coherence

Graceful fallback when ANTHROPIC_API_KEY not set.

---

## Test Summary

| Suite            | Tests | Passed | Failed | Time  |
|------------------|-------|--------|--------|-------|
| Causal Engine    | 28    | 28     | 0      | —     |
| ZK Trust Layer   | 15    | 15     | 0      | —     |
| Federated        | 23    | 23     | 0      | —     |
| Survival + RL    | 25    | 25     | 0      | —     |
| NLP + Anomaly    | 31    | 31     | 0      | —     |
| API Gateway      | 28    | 28     | 0      | —     |
| Total            | 150   | 150    | 0      | 7.57s |

---

## Service Map

| Service          | Port  | Technology        | Sprint |
|------------------|-------|-------------------|--------|
| FHIR Adapter     | 8080  | Java Spring Boot  | 1      |
| Normalisation    | 8086  | Python FastAPI    | 1      |
| Causal Engine    | 8081  | Python FastAPI    | 2      |
| ZK Service       | 8084  | Python FastAPI    | 3      |
| Federated        | 8085  | Python FastAPI    | 4      |
| Survival         | 8082  | Python FastAPI    | 5      |
| NLP              | 8083  | Python FastAPI    | 6      |
| API Gateway GQL  | 4000  | Node.js Apollo    | 7      |
| API Gateway WS   | 4001  | Node.js graphql-ws| 7      |
| CausalService    | 50051 | Python gRPC       | 7      |
| Claude Judgment  | 8090  | Python FastAPI    | 7      |
| PostgreSQL       | 5439  | postgres:15       | 1      |
| MongoDB          | 27018 | mongo:7           | 1      |
| Kafka            | 9094  | Confluent 7.4     | 1      |

---

## Next Sprint

Sprint 8 — React Dashboard + D3 Visualizations
  Patient overview dashboard
  Causal graph D3 force-directed visualization
  Survival curve charts
  Real-time alert feed via WebSocket
  Multi-doctor collaborative view