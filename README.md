# AXIOM - Causal AI Clinical Intelligence Platform

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
