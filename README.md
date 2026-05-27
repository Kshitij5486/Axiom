# Axiom v2.0.0 — Clinical AI Platform + Sentinel Network Security

[![Tests](https://img.shields.io/badge/tests-212%20passed-brightgreen)](tests/)
[![Version](https://img.shields.io/badge/version-v2.0.0-blue)](RELEASE_NOTES_v2.0.0.md)

> The only clinical AI system combining causal inference, federated learning,
> zero-knowledge proofs, and bare-metal network security.

## Live Demo

- **Platform:** https://axiom-dashboard-pi.vercel.app
- **Sentinel SOC:** https://axiom-dashboard-pi.vercel.app/sentinel/
- **GitHub:** https://github.com/Kshitij5486/Axiom

## Architecture — 17 Services, 8 Layers

```text
AXIOM v2.0.0 | 17 Services | 8 Layers | 212 Tests

LAYER 1 - PRESENTATION
  index.html           Landing page          port 3000
  dashboard.html       Command Centre        port 3000
  causal_graph.html    3D Causal Graph       port 3000
  counterfactual.html  Counterfactual        port 3000
  population.html      Population Atlas      port 3000
  sentinel-soc         React + TS + Three.js port 5173

LAYER 2 - API GATEWAY
  api-gateway          FastAPI + JWT         port 8080

LAYER 3 - CLINICAL AI
  causal-engine        DoWhy DAG             port 8081
  federated-service    Flower + Byzantine    port 8084
  survival-service     Cox PH + RL           port 8082
  nlp-service          Bio-BERT              port 8083

LAYER 4 - TRUST + PRIVACY
  zk-service           SHA-256 Merkle        port 8085
  Proofs: ClinicalRecommendation, CausalGraphIntegrity,
          NetworkIntegrity[v2], FederatedTraffic[v2],
          DeviceTrust[v2]

LAYER 5 - SENTINEL NETWORK SECURITY
  sentinel-sensor          C++ libpcap BPF   DaemonSet
  sentinel-control-plane   Go 5 pools        port 8090
  sentinel-graph-service   Python NetworkX   port 8091
  sentinel-correlator      Python Kafka      port 8092

LAYER 6 - DATA INGESTION
  fhir-adapter         FHIR R4 + HL7         port 8086
  websocket-server     Real-time vitals       port 8087

LAYER 7 - MESSAGE BUS + CACHE
  Kafka                12 topics             port 9094
  Redis                Trust scores          port 6380
  MinIO                Model store           port 9002

LAYER 8 - STORAGE + OBSERVABILITY
  PostgreSQL           Clinical + ZK proofs  port 5439
  MongoDB              Unstructured data     port 27018
  Prometheus           Metrics               port 9095
  Grafana              5 dashboards          port 3001

DATA FLOW
  Hospital Network
  -> sentinel-sensor (C++ BPF tcp:443)
  -> sentinel-control-plane (5 goroutine pools)
  -> sentinel-correlator (5-min sliding window)
  -> causal-engine (PATCH flag-source)
  -> Patient recommendations auto-attenuated

  Patient FHIR Data
  -> fhir-adapter -> Kafka -> causal-engine
  -> zk-service (proof) -> Dashboard
```

## Quick Start

```bash
git clone https://github.com/Kshitij5486/Axiom.git
cd Axiom/infrastructure
docker compose up -d
cd ..
python3 -m http.server 3000 --directory services/dashboard
```

Open http://localhost:3000

## Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Backend Sprints 1-7 | 150 | 150 |
| Dashboard Sprints 8-10 | 72 | 72 |
| Sentinel unit | 45 | 45 |
| Sentinel integration | 17 | 17 |
| **Total** | **284** | **284** |

## Stack

| Layer | Technologies |
|-------|-------------|
| Languages | Python, Go, C++17, TypeScript, React |
| AI/ML | DoWhy, PyTorch, Flower, Bio-BERT, Cox PH |
| Security | libpcap BPF, ZK Proofs, iptables |
| Infra | Kubernetes, Helm, Docker, Prometheus, Grafana |
| Viz | Three.js, D3.js, Framer Motion, Zustand |

## Key Innovation

> When a patient monitor shows anomalous network traffic while
> simultaneously producing impossible vital signs, Axiom automatically
> reduces the causal weight of that device's readings in the patient's
> treatment recommendations. The system heals its own data trust in
> real time. All decisions are backed by ZK proofs.

---
*Built by Kshitij Srivastava — NIT Surat, 3rd Year CS*
