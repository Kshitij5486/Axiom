# Axiom v1.2.0 — Sentinel Control Plane Complete

**Date:** 2026-05-24
**Sprint:** 13 (Days 77-80)
**Tests:** 252 passed, 0 failed

---

## What Was Built

Complete Sentinel Go control plane with 5 parallel threat
detection pools, Kafka consumer, n8n integration, SSE streaming,
quarantine API, and device trust scoring.

---

## Day 77 — Pool 3 + Pool 4

### Pool 3 — Ransomware Detection (4 rules)
- Rule 1: Lateral movement — src_ip contacts >15 internal IPs/60s (HIGH)
- Rule 2: Beaconing — CV of inter-request times <0.1 for 10+ requests (MEDIUM)
- Rule 3: Medical device traffic spike — 10x baseline HTTPS volume (HIGH)
- Rule 4: Data exfiltration — EHR outbound >10MB/5min to non-whitelisted IP (CRITICAL)

### Pool 4 — Federated Learning Monitor
- Unknown node connecting to Flower server (HIGH)
- Gradient size anomaly >50MB upload (HIGH, gradient inversion suspected)
- Replay attack — >10 uploads in 5 minutes from same node (MEDIUM)

---

## Day 78 — REST API + n8n + SSE

### REST API (8 endpoints on port 8090)
- GET  /health
- GET  /sentinel/threats
- GET  /sentinel/stats (threats_total, active_quarantines)
- GET  /sentinel/devices (trust scores from Redis)
- POST /sentinel/quarantine/{ip}
- DELETE /sentinel/quarantine/{ip}
- GET  /sentinel/stream (SSE live threat events)
- GET  /metrics (Prometheus)

### n8n Webhook Integration
- HIGH/CRITICAL threats POST to n8n at :5678/webhook/sentinel
- Payload: full ThreatEvent JSON
- Non-blocking goroutine

### SSE Stream
- /sentinel/stream broadcasts all threats in real time
- text/event-stream format
- Used by Sentinel SOC frontend (Sprint 14)

---

## Day 79 — Kafka Consumer

- Consumes from network.flows topic
- Consumer group: sentinel-control-plane
- Brokers: localhost:9094
- Auto-retry every 5s on failure
- Runs as background goroutine alongside Unix socket server
- Both inputs feed same processEvent pipeline (5 pools)

---

## Day 80 — Tests + Release

- 20 new unit tests covering all 5 pools
- 20/20 passing

---

## Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Backend Sprints 1-7 | 150 | 150 |
| Dashboard Sprints 8-10 | 72 | 72 |
| Sentinel Day 76 | 10 | 10 |
| Sentinel Day 80 | 20 | 20 |
| Total | 252 | 252 |

---

## Complete Control Plane Architecture
C++ Engine (4 services)
IngressHandler  → libpcap BPF tcp:443
FlowTracker     → TCP state machine
SNI Extractor   → TLS ClientHello parser
IPC Bridge      → Unix socket JSON stream
↓
/tmp/axiom_sentinel.sock
↓
Go Control Plane
Input 1: Unix socket (C++ engine direct)
Input 2: Kafka topic network.flows
↓
processEvent() — 5 parallel pools
↓
Pool 1: GeoIP (MaxMind GeoLite2)
Pool 2: SYN flood + port scan
Pool 3: Ransomware (lateral/beacon/spike/exfil)
Pool 4: Federated learning monitor
Pool 5: SNI intelligence
↓
threatsChan
↓
threatCollector
→ Redis trust scores
→ SSE broadcast
→ n8n webhook (HIGH/CRITICAL)
↓
REST API :8090
Prometheus :9182
