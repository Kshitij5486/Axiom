# Axiom — Causal-AI Clinical Intelligence Platform

**The world's first per-patient causal graph clinical decision support system.**

A full-stack, federated, real-time clinical operating system that combines
causal inference, reinforcement learning, zero-knowledge proofs, and
Byzantine-fault-tolerant federated learning — deployable across hospital
networks with no patient data ever leaving the institution.

> Every feature must serve a real clinical need.
> Every technology must be justified by the problem.
> The UI must be so good that non-technical people are impressed
> before technical people look at the code.

---

## What It Does

Most clinical decision support tools are correlation-based.
They say "patients with these symptoms often get this drug."

Axiom asks a different question: **for this specific patient,
given their individual causal graph, what is the causal effect
of intervention X on outcome Y?**

That is a fundamentally different — and more defensible —
type of clinical recommendation.

---

## Architecture
Layer 0  FHIR R4 Ingestion + Kafka Pipeline      ← v0.1.0
Layer 1  Per-Patient Causal Graph (DoWhy)         ← Sprint 2
Layer 2  Survival Model + RL + BioBERT + Anomaly  ← Sprint 3-6
Layer 3  Federated Learning + ZK Proofs           ← Sprint 7-8
Layer 4  GraphQL + WebSocket + gRPC APIs          ← Sprint 9
Layer 5  React 18 + Three.js 3D UI + Mobile       ← Sprint 10-11
Layer 6  Prometheus + Grafana + Loki + Jaeger      ← Sprint 12
Layer 7  Kubernetes + CI/CD + v1.0.0              ← Sprint 12

---

## Current Status — v0.4.0

Sprints 1-4 complete. Data ingestion, causal engine, and ZK trust layer fully operational.
Services running:    12
Patients ingested:   50
Observations:        5000
Causal graphs:       50 (avg 10 effects, 212ms)
ZK proofs:           auto-generated per graph build
Federated nodes:     3 (hospital-1,2,3)
Byzantine detected:  hospital-3 auto-excluded
Unit tests:          66 passed, 0 failed
Kafka topics:        7

---

## Quick Start

```bash
# Start all infrastructure
cd infrastructure
docker compose up -d

# Start FHIR Adapter
cd services/fhir-adapter
mvn spring-boot:run

# Start Normalisation Service
cd services/normalisation-service
python -m venv venv && venv/Scripts/activate
pip install -r requirements.txt
python main.py

# Generate synthetic patients
cd infrastructure/data_generator
python generate_patients.py
```

**Health checks:**
http://localhost:8080/fhir/health
http://localhost:8086/health
http://localhost:9095/-/healthy
http://localhost:3001/api/health

**Grafana:** http://localhost:3001 — admin / axiom123

---

## Service Map

| Service        | Port  | Technology       |
|----------------|-------|------------------|
| FHIR Adapter   | 8080  | Java Spring Boot |
| Normalisation  | 8086  | Python FastAPI   |
| PostgreSQL     | 5439  | postgres:15      |
| MongoDB        | 27018 | mongo:7          |
| Redis          | 6380  | redis:7          |
| Kafka          | 9094  | Confluent 7.4    |
| MinIO          | 9010  | minio:latest     |
| Prometheus     | 9095  | prom 2.45        |
| Grafana        | 3001  | grafana 10.1     |

---

## Tech Stack
Backend:     Java 21, Python 3.13, Node.js 20, Rust
AI/ML:       DoWhy, PyTorch, Stable Baselines3, BioBERT
Data:        PostgreSQL 15, MongoDB 7, Redis 7, Kafka
Frontend:    React 18, TypeScript, Three.js, D3.js
Mobile:      React Native
Infra:       Docker, Kubernetes, GitHub Actions
Observability: Prometheus, Grafana, Loki, Jaeger

---

## Author

**Kshitij Srivastava**
NIT Surat — 3rd year Computer Science
github.com/Kshitij5486/Axiom

*12 sprints. 84 days. 1 developer.*