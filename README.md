# Axiom v2.0.0 — Clinical AI Platform + Sentinel Network Security

[![Tests](https://img.shields.io/badge/tests-284%20passed-brightgreen)](tests/)
[![Version](https://img.shields.io/badge/version-v2.0.0-blue)](RELEASE_NOTES_v2.0.0.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> The only clinical AI system that combines causal inference, federated learning,
> zero-knowledge proofs, and bare-metal network security in a single platform.

---

## Architecture — 17 Services, 8 Layers
python3 - << 'PYEOF'
arch = """
╔══════════════════════════════════════════════════════════════════╗
║              AXIOM v2.0.0 — ARCHITECTURE                        ║
║              17 Services · 8 Layers · 284 Tests                 ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 1 · PRESENTATION                                         ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  ║
║  │ dashboard  │ │causal_graph│ │population  │ │sentinel-soc │  ║
║  │ :3000      │ │ :3000      │ │ :3000      │ │ :5173       │  ║
║  │ HTML+D3    │ │ HTML+Three │ │ HTML+D3    │ │ React+TS    │  ║
║  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 2 · API GATEWAY                                          ║
║  ┌────────────────────────────────────────────────────────────┐ ║
║  │  api-gateway :8080  FastAPI · JWT · Rate Limiting          │ ║
║  └────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 3 · CLINICAL AI                                          ║
║  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────┐  ║
║  │causal-engine │ │ federated-svc│ │survival-svc│ │nlp-svc  │  ║
║  │ :8081 DoWhy  │ │:8084 Flower  │ │:8082 Cox   │ │:8083    │  ║
║  │ Causal DAG   │ │ Byzantine    │ │ RL agent   │ │BioBERT  │  ║
║  └──────────────┘ └──────────────┘ └────────────┘ └─────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 4 · TRUST + PRIVACY                                      ║
║  ┌────────────────────────────────────────────────────────────┐ ║
║  │  zk-service :8085  SHA-256 Merkle Proofs                  │ ║
║  │  ClinicalRecommendation  CausalGraphIntegrity              │ ║
║  │  NetworkIntegrity[NEW]   FederatedTraffic[NEW]             │ ║
║  │  DeviceTrust[NEW]                                          │ ║
║  └────────────────────────────────────────────────────────────┘ ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 5 · SENTINEL NETWORK SECURITY                            ║
║  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────┐  ║
║  │sentinel-     │ │sentinel-     │ │sentinel-   │ │sentinel │  ║
║  │sensor        │ │control-plane │ │graph-svc   │ │correlat │  ║
║  │C++ libpcap   │ │Go :8090      │ │Py :8091    │ │Py :8092 │  ║
║  │DaemonSet     │ │5 goroutine   │ │NetworkX    │ │3-topic  │  ║
║  │BPF tcp:443   │ │worker pools  │ │DoWhy DAG   │ │Kafka    │  ║
║  │SNI extractor │ │GeoIP+Ransom  │ │BFS countf  │ │5-min win│  ║
║  └──────────────┘ └──────────────┘ └────────────┘ └─────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 6 · DATA INGESTION                                       ║
║  ┌──────────────────────────┐ ┌──────────────────────────────┐  ║
║  │ fhir-adapter :8086       │ │ websocket-server :8087       │  ║
║  │ FHIR R4 · HL7 · Kafka    │ │ Real-time vitals · alerts    │  ║
║  └──────────────────────────┘ └──────────────────────────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 7 · MESSAGE BUS + CACHE                                  ║
║  ┌─────────────────────┐ ┌──────────────┐ ┌─────────────────┐  ║
║  │ Kafka :9094         │ │ Redis :6380  │ │ MinIO :9002     │  ║
║  │ 12 topics:          │ │ Trust scores │ │ Model store     │  ║
║  │ patient.alerts      │ │ Blocked IPs  │ │ Gradient store  │  ║
║  │ sentinel.threats    │ │ Sessions     │ └─────────────────┘  ║
║  │ network.flows       │ └──────────────┘                      ║
║  │ sentinel.correlations│                                       ║
║  └─────────────────────┘                                        ║
╠══════════════════════════════════════════════════════════════════╣
║  LAYER 8 · STORAGE + OBSERVABILITY                              ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  ║
║  │ PostgreSQL │ │ MongoDB    │ │ Prometheus │ │ Grafana     │  ║
║  │ :5439      │ │ :27018     │ │ :9095      │ │ :3001       │  ║
║  │ Clinical   │ │ Unstructd  │ │ Metrics    │ │ 5 dashbds   │  ║
║  │ ZK proofs  │ │ NLP docs   │ │ 15s scrape │ │ SOC+Clinical│  ║
║  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  DATA FLOW                                                      ║
║                                                                  ║
║  Hospital Network                                               ║
║  → sentinel-sensor (C++ BPF)                                    ║
║  → Unix socket                                                  ║
║  → sentinel-control-plane (5 pools)                             ║
║  → Kafka: sentinel.threats + sentinel.devices                   ║
║  → sentinel-correlator (5-min window)                           ║
║  → causal-engine (PATCH flag-source)                            ║
║  → Patient recommendations auto-attenuated                      ║
║                                                                  ║
║  Patient FHIR Data                                              ║
║  → fhir-adapter → Kafka → causal-engine                         ║
║  → zk-service (proof) → Dashboard                               ║
╠══════════════════════════════════════════════════════════════════╣
║  KUBERNETES                                                     ║
║  Namespace: axiom-clinical                                      ║
║  DaemonSet:   sentinel-sensor (1 per node)                      ║
║  Deployments: 11 services (replicated)                          ║
║  StatefulSets: postgres mongodb kafka redis minio               ║
╚══════════════════════════════════════════════════════════════════╝
"""

with open('/mnt/c/Users/KSHITIJ/axiom/ARCHITECTURE.md', 'w') as f:
    f.write('# Axiom v2.0.0 Architecture\n\n```\n' + arch + '\n```\n')

# Verify no line too long
lines = arch.split('\n')
max_len = max(len(l) for l in lines)
print(f"Max line length: {max_len}")
print(f"Total lines: {len(lines)}")
print("Written to ARCHITECTURE.md")
PYEOF
---

## Quick Start

### Local Development (Docker Compose)

```bash
# Clone
git clone https://github.com/Kshitij5486/Axiom.git
cd Axiom

# Start all 17 services
cd infrastructure
docker compose up -d

# Verify all running
docker compose ps

# Run all tests
cd ..
python3 -m pytest tests/ -v

# Start dashboard
python3 -m http.server 3000 --directory services/dashboard

# Start Sentinel SOC
cd services/sentinel-soc
npm install && npm run dev
```

Open:
- Dashboard:     http://localhost:3000/dashboard.html
- Sentinel SOC:  http://localhost:5173
- Grafana:       http://localhost:3001
- Prometheus:    http://localhost:9095

---

### Production Deployment (Kubernetes + Helm)

```bash
# Create namespace
kubectl create namespace axiom-clinical

# Label hospital nodes for Sentinel sensor
kubectl label node <hospital-node> hospital-network-enabled=true

# Create secrets
kubectl create secret generic axiom-postgres-secret \
  --from-literal=password=<your-password> \
  -n axiom-clinical

# Install Axiom
helm install axiom infrastructure/kubernetes/helm/axiom \
  --namespace axiom-clinical \
  --values infrastructure/kubernetes/helm/axiom/values.yaml

# Verify Sentinel DaemonSet
kubectl get daemonset sentinel-sensor -n axiom-clinical

# Verify all pods
kubectl get pods -n axiom-clinical
```

---

### Sentinel Sensor Deployment (New Hospital Node)

```bash
# 1. Label the node
kubectl label node <new-hospital-node> hospital-network-enabled=true

# 2. DaemonSet automatically schedules sentinel-sensor pod
# Verify:
kubectl get pods -n axiom-clinical -l app=sentinel-sensor

# 3. Check sensor is capturing
kubectl logs -n axiom-clinical \
  $(kubectl get pods -n axiom-clinical -l app=sentinel-sensor \
    --field-selector spec.nodeName=<new-hospital-node> \
    -o jsonpath='{.items[0].metadata.name}')

# Expected output:
# [SENTINEL] IPC Bridge Service v1.0
# [IPC] Connected to /tmp/axiom_sentinel.sock
# [SENTINEL] Capturing on eth0
```

---

## ZK Proof Types (5 total)

### Clinical Proofs (Sprint 3)
| Proof | Purpose | Verify |
|-------|---------|--------|
| ClinicalRecommendationProof | Treatment recommendation is authentic | POST /zk/verify |
| CausalGraphIntegrityProof | Causal graph not tampered | POST /zk/graph/verify |

### Sentinel Proofs (Sprint 17)
| Proof | Purpose | Verify |
|-------|---------|--------|
| NetworkIntegrityProof | Network flow batch not fabricated (Merkle root) | POST /zk/network-integrity/verify |
| FederatedTrafficProof | Only registered hospitals submitted gradients | POST /zk/federated-traffic/verify |
| DeviceTrustProof | Trust score derived from real threat evidence | POST /zk/device-trust/verify |

### Verify a Device Trust Proof

```bash
curl -X POST http://localhost:8085/zk/device-trust/verify \
  -H "Content-Type: application/json" \
  -d '{
    "proof_hash": "<hash-from-audit-trail>",
    "device_ip": "10.0.0.5",
    "trust_score": 0.4,
    "evidence_events": [
      {"severity": "HIGH", "threat_type": "SYN_FLOOD"},
      {"severity": "MEDIUM", "threat_type": "PORT_SCAN"}
    ],
    "hospital_id": "hospital-A"
  }'
```

---

## Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Backend Sprints 1-7 | 150 | 150 |
| Dashboard Sprints 8-10 | 72 | 72 |
| Sentinel unit v1 | 10 | 10 |
| Sentinel unit v2 | 20 | 20 |
| Sentinel unit v3 | 15 | 15 |
| Sentinel integration | 17 | 17 |
| **Total** | **284** | **284** |

---

## Interview Talking Points

> "Axiom v2.0.0 adds a clinical network security layer called Sentinel.
> It runs a bare-metal C++ libpcap engine on every hospital node via
> a Kubernetes DaemonSet — capturing network flows at the kernel level
> using BPF filters and extracting SNI domains from TLS without
> decrypting traffic.
>
> A Go control plane runs five parallel goroutine worker pools doing
> geo-IP enforcement, SYN flood detection, ransomware heuristics,
> federated learning traffic monitoring, and SNI domain intelligence.
>
> The most technically novel component is the AI Cross-Correlation Engine:
> it correlates patient clinical anomalies, network threat events, and
> device trust scores in a 5-minute sliding window. When a patient monitor
> starts showing anomalous network traffic while simultaneously producing
> impossible vital signs, Axiom automatically reduces the causal weight of
> that device's readings in the patient's treatment recommendations —
> the system heals its own data trust in real time.
>
> All network integrity decisions are backed by ZK proofs, so clinicians
> can cryptographically verify that a device's data was discounted based
> on real evidence, not a model error.
>
> No clinical AI system, no hospital SIEM, and no network security tool
> combines all of this. I built it as the v2.0.0 extension of my
> undergraduate Axiom project."

---

## Stack
Languages:   Python  Go  C++17  TypeScript  React
Frameworks:  FastAPI  Gin  libpcap  Vite  Tailwind
AI/ML:       DoWhy  PyTorch  Flower  Bio-BERT  Cox PH
Storage:     PostgreSQL  MongoDB  Redis  MinIO  Kafka
Security:    ZK Proofs (SHA-256 Merkle)  BPF  iptables
Infra:       Kubernetes  Helm  Docker  Prometheus  Grafana
Viz:         Three.js  D3.js  Framer Motion  Zustand
---

*Built by Kshitij Srivastava — NIT Surat, 3rd Year CS*
*github.com/Kshitij5486/Axiom*
