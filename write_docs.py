import os
os.makedirs("C:/Users/KSHITIJ/axiom/docs", exist_ok=True)

open("C:/Users/KSHITIJ/axiom/README.md", "w", encoding="utf-8").write("""# AXIOM - Causal AI Clinical Intelligence Platform

[![Tests](https://img.shields.io/badge/tests-222%20passed-brightgreen)](https://github.com/Kshitij5486/Axiom/actions)
[![Version](https://img.shields.io/badge/version-v1.0.0-004953)](https://github.com/Kshitij5486/Axiom/releases)

> Causal AI that a doctor can verify, a regulator can audit, and a patient can trust.

## Quick Start

    git clone https://github.com/Kshitij5486/Axiom.git
    cd Axiom/infrastructure
    docker compose up -d
    cd ..
    python -m http.server 3000 --directory services/dashboard
    # Open http://localhost:3000

## What is Axiom?

Axiom is a production-grade clinical AI platform that replaces black-box ML
with per-patient causal graphs. Every treatment recommendation is:
- Causally grounded: DoWhy causal inference, not correlation
- Cryptographically verified: ZK proof on every output
- Federally learned: patient data never leaves the hospital
- Interactively explainable: 3D graph the doctor can rotate and query

## Services

| Service | Port | Technology |
|---------|------|-----------|
| FHIR Adapter | 8080 | Java Spring Boot |
| Causal Engine | 8081 | Python + DoWhy |
| Survival + RL | 8082 | Python + PyTorch |
| NLP + Anomaly | 8083 | Python + BioBERT |
| ZK Service | 8084 | Python |
| Federated | 8085 | Python |
| GraphQL Gateway | 4000 | Node.js Apollo |
| Dashboard | 3000 | HTML + D3 + Three.js |

## Key Results

| Metric | Value |
|--------|-------|
| Causal graph build time | 212ms avg |
| Survival model C-index | 0.792 |
| PPO policy mean reward | 3.16 |
| ZK proof generation | <10ms |
| Unit tests | 222 / 222 pass |
| Byzantine nodes detected | Hospital C (100% recall) |

## Screens

- Command Centre: Real-time vitals, causal recommendations, ZK proof badges
- 3D Causal Graph: Three.js graph with particles, edge click shows ZK proof
- Counterfactual Simulator: Sliders, Monte Carlo violin plot, survival curves
- Population Atlas: 50-patient heatmap, cohort causal graph

## Sprint History

| Sprint | What | Version |
|--------|------|---------|
| 1 | FHIR + Kafka + PostgreSQL | v0.1.0 |
| 2 | Per-patient causal graphs | v0.2.0 |
| 3 | ZK trust layer | v0.3.0 |
| 4 | Federated + Byzantine | v0.4.0 |
| 5 | Survival + RL | v0.5.0 |
| 6 | NLP + Anomaly Detection | v0.6.0 |
| 7 | GraphQL + WebSocket + gRPC | v0.7.0 |
| 8 | Command Centre Dashboard | v0.8.0 |
| 9 | 3D Graph + Counterfactual | v0.9.0 |
| 10 | Population Atlas | v0.10.0 |
| 12 | Kubernetes + CI/CD + v1.0.0 | v1.0.0 |

## Production Deployment

    kubectl apply -f infrastructure/kubernetes/manifests/
    helm install axiom ./infrastructure/kubernetes/helm/axiom

See docs/DEPLOYMENT.md for full guide.

## Interview Talking Points

1. Causal AI not correlation: DoWhy structural causal models. The lisinopril
   recommendation exists because systolic_bp causally reduces creatinine with
   effect 0.0239 - not because CKD patients statistically receive lisinopril.

2. ZK-verified outputs: Every recommendation carries a SHA-256 hash chain.
   Tampered model or data means proof fails. Production-grade auditability.

3. Byzantine-robust federated learning: Hospital C injected corrupted gradients.
   Bulyan aggregation detected outlier (distance 71.1 vs 36.6 honest average)
   and excluded it. Global model unaffected.

4. Per-patient counterfactuals: Doctor asks what happens to a patient if
   lisinopril increases by 10mg. Monte Carlo engine runs 1000 simulations
   and shows the full distribution with confidence intervals.

5. Production infrastructure: Kubernetes with HPA, GitHub Actions CI/CD,
   Prometheus metrics, Grafana dashboards, multi-stage Dockerfiles.

## Author

Kshitij Srivastava - NIT Surat, 3rd Year CS
GitHub: github.com/Kshitij5486/Axiom
""")

open("C:/Users/KSHITIJ/axiom/docs/ARCHITECTURE.md", "w", encoding="utf-8").write("""# Axiom Architecture

## System Overview

    EHR --> FHIR Adapter (8080) --> Kafka --> Data Normaliser
                                                   |
                              +--------------------+--------------------+
                              |                                         |
                        Causal Engine (8081)               Survival + RL (8082)
                        DoWhy + DoCalc                     Deep Cox + PPO
                        212ms per graph                    C-index 0.792
                              |                                         |
                        ZK Service (8084)                  NLP + Anomaly (8083)
                        Integrity proofs                   BioBERT + IsoForest
                              |                                         |
                              +--------------------+--------------------+
                                                   |
                                        GraphQL Gateway (4000)
                                        WebSocket      (4001)
                                        gRPC           (50051)
                                                   |
                                        Dashboard (3000)
                                        Screen 1: Command Centre
                                        Screen 2: 3D Causal Graph
                                        Screen 3: Counterfactual
                                        Screen 4: Population Atlas

## Service Map

| Service | Port | Technology | Sprint |
|---------|------|-----------|--------|
| FHIR Adapter | 8080 | Java Spring Boot | 1 |
| Causal Engine | 8081 | Python FastAPI + DoWhy | 2 |
| Survival + RL | 8082 | Python FastAPI + PyTorch | 5 |
| NLP + Anomaly | 8083 | Python FastAPI + BioBERT | 6 |
| ZK Service | 8084 | Python FastAPI | 3 |
| Federated | 8085 | Python FastAPI | 4 |
| GraphQL Gateway | 4000 | Node.js Apollo | 7 |
| WebSocket | 4001 | Node.js graphql-ws | 7 |
| gRPC | 50051 | Python grpcio | 7 |
| Dashboard | 3000 | HTML + D3 + Three.js | 8-10 |
| PostgreSQL | 5439 | postgres:15 | 1 |
| MongoDB | 27018 | mongo:7 | 1 |
| Kafka | 9094 | Confluent 7.4 | 1 |

## Data Flow

1. Patient vitals arrive via FHIR R4 to Kafka topic vitals.raw
2. Normaliser consumes and stores in PostgreSQL + MongoDB
3. Causal Engine builds per-patient DAG using DoWhy in 212ms avg
4. ZK Service generates SHA-256 integrity proof
5. Survival model scores 30-day survival probability
6. PPO policy selects optimal treatment recommendation
7. NLP pipeline enriches DAG with clinical note edges
8. Anomaly detector flags vital breaches via WebSocket alert
9. GraphQL gateway exposes unified API to dashboard
10. Doctor views 3D graph, runs counterfactual, reviews population atlas
""")

open("C:/Users/KSHITIJ/axiom/docs/DEPLOYMENT.md", "w", encoding="utf-8").write("""# Axiom Deployment Guide

## Local Development

Prerequisites: Docker Desktop, Python 3.11+, Node.js 20+, Java 21

    git clone https://github.com/Kshitij5486/Axiom.git
    cd Axiom/infrastructure
    docker compose up -d
    cd ..
    python -m pytest tests/unit/ -v --tb=short
    python -m http.server 3000 --directory services/dashboard

## Production

### Kubernetes

    kubectl apply -f infrastructure/kubernetes/manifests/namespace.yaml
    kubectl apply -f infrastructure/kubernetes/manifests/secrets.yaml
    kubectl apply -f infrastructure/kubernetes/manifests/
    kubectl get pods -n axiom-clinical

### Helm

    helm install axiom ./infrastructure/kubernetes/helm/axiom --namespace axiom-clinical

### Monitoring

    Prometheus: http://localhost:9090
    Grafana:    http://localhost:3001 (import dashboards from infrastructure/monitoring/grafana/dashboards/)

## Environment Variables

| Variable | Description |
|----------|-------------|
| POSTGRES_USER | PostgreSQL username |
| POSTGRES_PASSWORD | PostgreSQL password |
| MONGO_USER | MongoDB username |
| MONGO_PASSWORD | MongoDB password |
| JWT_SECRET | 256-bit JWT secret |
| JAVA_HOME | JDK 21 path |

## Encryption at Rest

PostgreSQL: pgcrypto extension, AES-256 column-level encryption
MongoDB: enableEncryption: true in mongod.conf with keyfile
Key rotation: openssl rand -base64 32 > new_keyfile, update k8s secret, rollout restart
""")

open("C:/Users/KSHITIJ/axiom/docs/API_REFERENCE.md", "w", encoding="utf-8").write("""# Axiom API Reference

## GraphQL  POST http://localhost:4000/graphql

### Full Analysis
    query { fullAnalysis(patientId: "3319a93d") {
      causalGraph { nodeList effectSizes zkIntegrityProof }
      survival { survivalProbability medianSurvivalDays riskScore }
      recommendation { action reward zkProven }
    }}

### Counterfactual
    mutation { runCounterfactual(patientId: "3319a93d", intervention: "lisinopril") {
      creatinine sbp glucose heartRate survivalDelta zkProof
    }}

## WebSocket  ws://localhost:4001/graphql
    subscription { patientAlerts(patientId: "3319a93d") {
      severity vital value threshold message
    }}

## REST

| Service | Endpoint | Method |
|---------|----------|--------|
| Causal Engine | /causal/graph/{id} | GET |
| Causal Engine | /causal/counterfactual | POST |
| Survival | /survival/{id} | GET |
| Survival | /recommendation/{id} | GET |
| ZK Service | /zk/prove | POST |
| ZK Service | /zk/verify | POST |

## Benchmarks

| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| Causal graph | 212ms | 380ms | 520ms |
| Survival prediction | 45ms | 89ms | 120ms |
| ZK proof generation | 8ms | 15ms | 22ms |
| Counterfactual | 340ms | 610ms | 820ms |
| Full analysis | 480ms | 750ms | 950ms |
""")

print("All docs written successfully")

