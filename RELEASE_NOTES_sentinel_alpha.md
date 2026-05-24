# Axiom Sentinel Alpha Release

**Tag:** v1.1.1
**Sprint:** 13
**Days:** 70-76
**Date:** 2026-05-24

---

## What Was Built

Axiom Sentinel is a bare-metal network security engine
integrated into the Axiom Clinical AI Platform.

It intercepts raw network frames, reconstructs TCP flows,
extracts plaintext SNI domains from encrypted TLS traffic,
and streams threat intelligence to a Go control plane
with GeoIP enforcement, rate limiting, and device trust scoring.

---

## C++ Engine (sentinel-engine) — 4 services

### Day 70 — IngressHandler
- pcap_open_live on eth0, BPF filter tcp port 443
- Ethernet + IPv4 + TCP header parsing
- FlowEvent struct: timestamp, IPs, ports, protocol
- Verified: live capture 172.30.88.1 -> 142.250.202.206:443

### Day 71 — FlowTracker
- unordered_map with FlowKeyHash (bidirectional dedup)
- TCP state machine: SYN_SEEN, ESTABLISHED, FIN_SEEN, CLOSED
- GC thread removes inactive flows every 30s
- Verified: NEW flow github.com google.com

### Day 72 — SNI Extractor
- Safe pointer arithmetic through TLS ClientHello
- session_id, cipher_suites, compression, extensions
- Extension type 0x0000 = SNI hostname
- Verified: github.com google.com stackoverflow.com

### Day 73 — IPC Bridge
- Manual JSON serializer (no external library)
- AF_UNIX SOCK_STREAM client to Go control plane
- Thread-safe queue + sender_thread + reconnect on failure
- Newline-delimited JSON contract

---

## Go Control Plane (sentinel-control-plane)

### Day 74 — Worker Pool v1
- 8 goroutine workers, buffered channel 10000
- Unix socket server reads from C++ engine
- Prometheus metrics: flows, SNI, connections, events
- Verified: 427 events processed

### Day 75 — Threat Intelligence v2
- GeoIP enforcement (MaxMind GeoLite2-Country)
  - Allowlist: IN, US, GB, AE, OM
  - Verified: AE traffic blocked, trust degraded to 0.00
- SYN flood detection: 100 packets/10s sliding window
- Port scan detection: 20 distinct ports/window
- SNI intelligence: blocklist + clinical domain allowlist
- Device trust scorer: Redis 0.0-1.0, MEDIUM -0.1, HIGH -0.3, CRITICAL -0.5
- REST API: /sentinel/threats, /sentinel/stats, /health
- Prometheus: sentinel_flows_total, sentinel_threats_detected_total,
              sentinel_blocked_ips_active, sentinel_sni_domains_total

### Day 76 — Tests + Release
- 10 unit tests: JSON contract, GeoIP, rate limiter, trust scorer
- 10/10 passing

---

## IPC JSON Contract

{
  "timestamp": 1779615135,
  "src_ip": "172.30.88.1",
  "src_port": 49836,
  "dest_ip": "20.233.83.145",
  "dest_port": 443,
  "protocol": "TCP",
  "sni_domain": "github.com",
  "status": "SNI_EXTRACTED"
}

---

## Test Summary

| Suite | Tests | Pass |
|-------|-------|------|
| Backend Sprints 1-7 | 150 | 150 |
| Dashboard Sprints 8-10 | 72 | 72 |
| Sentinel Sprint 13 | 10 | 10 |
| Total | 232 | 232 |

---

## Stack Added

- C++17 with libpcap 1.10.4
- BPF kernel filters (zero idle CPU)
- Go 1.22 goroutines and channels
- MaxMind GeoLite2-Country MMDB (8.9MB)
- Redis (trust scores, blocked IPs, 1hr TTL)
- Unix Domain Sockets IPC
- Manual JSON serializer
- Prometheus custom metrics

---

## Sprint History

| Sprint | Feature | Version |
|--------|---------|---------|
| 1 | FHIR + Kafka + PostgreSQL | v0.1.0 |
| 2 | Causal Engine | v0.2.0 |
| 3 | ZK Trust Layer | v0.3.0 |
| 4 | Federated + Byzantine | v0.4.0 |
| 5 | Survival + RL | v0.5.0 |
| 6 | NLP + Anomaly Detection | v0.6.0 |
| 7 | GraphQL + WebSocket + gRPC | v0.7.0 |
| 8 | Command Centre Dashboard | v0.8.0 |
| 9 | 3D Causal Graph + Counterfactual | v0.9.0 |
| 10 | Population Atlas | v0.10.0 |
| 12 | Kubernetes + CI/CD + v1.0.0 | v1.0.0 |
| 13 | Sentinel Network Security Engine | v1.1.1 |
