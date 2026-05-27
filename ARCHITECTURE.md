# Axiom v2.0.0 — Architecture

## 17 Services · 8 Layers · 212 Tests
=================================================================
AXIOM v2.0.0 ARCHITECTURE
17 Services | 8 Layers | 212 Tests
LAYER 1: PRESENTATION
index.html          Landing page           port 3000
dashboard.html      Command Centre         port 3000
causal_graph.html   3D Causal Graph        port 3000
counterfactual.html Counterfactual         port 3000
population.html     Population Atlas       port 3000
sentinel-soc        React + TS + Three.js  port 5173
=================================================================
LAYER 2: API GATEWAY
api-gateway         FastAPI + JWT          port 8080
=================================================================
LAYER 3: CLINICAL AI  (4 services)
causal-engine       DoWhy DAG              port 8081
federated-service   Flower + Byzantine     port 8084
survival-service    Cox PH + RL            port 8082
nlp-service         Bio-BERT               port 8083
=================================================================
LAYER 4: TRUST + PRIVACY  (1 service)
zk-service          SHA-256 Merkle         port 8085
Proof types:
ClinicalRecommendationProof
CausalGraphIntegrityProof
NetworkIntegrityProof      [NEW v2.0.0]
FederatedTrafficProof      [NEW v2.0.0]
DeviceTrustProof           [NEW v2.0.0]
=================================================================
LAYER 5: SENTINEL NETWORK SECURITY  (4 services)
sentinel-sensor
Type:    Kubernetes DaemonSet (1 pod per hospital node)
Stack:   C++ libpcap + BPF filter tcp:443
Feature: SNI extraction from TLS ClientHello
IPC:     Unix socket to control plane
sentinel-control-plane                     port 8090
Stack:   Go goroutines
Pool 1:  GeoIP enforcement (MaxMind)
Pool 2:  SYN flood + port scan detection
Pool 3:  Ransomware heuristics (4 rules)
Pool 4:  Federated learning monitor
Pool 5:  SNI domain intelligence
sentinel-graph-service                     port 8091
Stack:   Python FastAPI + NetworkX
Feature: Infrastructure causal DAG
Device fingerprinting
BFS counterfactual propagation
sentinel-correlator                        port 8092
Stack:   Python FastAPI
Feature: 3-topic Kafka consumer
5-minute sliding window
4 correlation rules
=================================================================
LAYER 6: DATA INGESTION  (2 services)
fhir-adapter        FHIR R4 + HL7          port 8086
websocket-server    Real-time vitals        port 8087
=================================================================
LAYER 7: MESSAGE BUS + CACHE
Kafka               12 topics              port 9094
patient.alerts        sentinel.threats
sentinel.devices      network.flows
sentinel.correlations federated.gradients
patient.vitals        causal.updates
zk.proofs             audit.trail
anomaly.scores        model.updates
Redis               Trust scores           port 6380
MinIO               Model store            port 9002
=================================================================
LAYER 8: STORAGE + OBSERVABILITY
PostgreSQL          Clinical + ZK proofs   port 5439
MongoDB             Unstructured data      port 27018
Prometheus          Metrics                port 9095
Grafana             5 dashboards           port 3001
- clinical-operations
- ml-performance
- infrastructure
- sentinel-soc     [NEW v2.0.0]
- zk-audit-trail
=================================================================
DATA FLOW
Hospital Network
-> sentinel-sensor (C++ BPF tcp:443)
-> Unix socket IPC
-> sentinel-control-plane (5 goroutine pools)
-> Kafka: sentinel.threats + sentinel.devices
-> sentinel-graph-service (NetworkX causal DAG)
-> sentinel-correlator (5-min sliding window)
-> Kafka: sentinel.correlations
-> zk-service (DeviceTrustProof)
-> causal-engine PATCH /causal/graph/{id}/flag-source
-> Patient recommendations auto-attenuated
Patient FHIR Data
-> fhir-adapter
-> Kafka: patient.vitals
-> causal-engine (DoWhy DAG inference)
-> zk-service (ClinicalRecommendationProof)
-> websocket-server
-> Dashboard screens
=================================================================
KUBERNETES
Namespace:    axiom-clinical
DaemonSet:    sentinel-sensor
(1 pod per hospital node)
Deployments:  api-gateway
causal-engine
federated-service
survival-service
nlp-service
zk-service
sentinel-control-plane
sentinel-graph-service
sentinel-correlator
fhir-adapter
websocket-server
StatefulSets: postgres  mongodb  kafka  redis  minio
Security:     NetworkPolicies (all Sentinel services)
Istio AuthorizationPolicy
(admin + security_analyst roles only)
=================================================================
