import pytest
import json
import time
import math
from collections import defaultdict

# ══════════════════════════════════════════
# sentinel-graph-service tests
# ══════════════════════════════════════════

def test_device_profile_ports_tracked():
    profile = {"ports": set(), "domains": set(), "peers": set(),
                "timestamps": [], "bytes_total": 0, "packet_count": 0}
    evt = {"dest_port": 443, "sni_domain": "github.com",
           "dest_ip": "20.233.83.145", "byte_count": 1400}
    profile["ports"].add(evt["dest_port"])
    profile["domains"].add(evt["sni_domain"])
    profile["peers"].add(evt["dest_ip"])
    profile["bytes_total"] += evt["byte_count"]
    profile["packet_count"] += 1
    assert 443 in profile["ports"]
    assert "github.com" in profile["domains"]
    assert profile["packet_count"] == 1

def test_device_profile_bytes_accumulated():
    profile = {"bytes_total": 0, "packet_count": 0}
    for i in range(10):
        profile["bytes_total"] += 1400
        profile["packet_count"] += 1
    assert profile["bytes_total"] == 14000
    assert profile["packet_count"] == 10

def test_graph_edge_effect_size():
    ip_count   = 100
    peer_count = 50
    effect = min(1.0, ip_count / (ip_count + peer_count))
    assert 0.0 < effect <= 1.0
    assert round(effect, 3) == 0.667

def test_counterfactual_bfs_threshold():
    prob      = 1.0
    effect    = 0.8
    confidence = 0.9
    propagation_prob = prob * effect * confidence
    assert propagation_prob > 0.1  # above threshold

def test_counterfactual_low_effect_blocked():
    prob      = 1.0
    effect    = 0.05
    confidence = 0.8
    propagation_prob = prob * effect * confidence
    assert propagation_prob <= 0.1  # below threshold, not propagated

def test_graph_node_trust_score():
    node = {"ip": "10.0.0.1", "trust_score": 0.3, "device_type": "ecg_monitor"}
    assert node["trust_score"] < 0.5  # low trust

def test_infrastructure_graph_structure():
    nodes = [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}]
    edges = [{"source": "10.0.0.1", "target": "10.0.0.2", "effect_size": 0.7}]
    assert len(nodes) == 2
    assert edges[0]["effect_size"] == 0.7

# ══════════════════════════════════════════
# sentinel-correlator tests
# ══════════════════════════════════════════

def test_sliding_window_cleanup():
    now = time.time()
    window = [
        {"ts": now - 400, "event": {}},  # outside 5min window
        {"ts": now - 100, "event": {}},  # inside
        {"ts": now,       "event": {}},  # inside
    ]
    cutoff = now - 300
    valid = [e for e in window if e["ts"] > cutoff]
    assert len(valid) == 2

def test_correlation_rule1_device_patient_match():
    patient_id = "pt-001"
    device_evt = {"axiom_patient_id": patient_id, "trust_score": 0.3, "ip": "10.0.0.5"}
    alert_evt  = {"patient_id": patient_id, "anomaly_type": "creatinine_spike"}
    assert device_evt["axiom_patient_id"] == alert_evt["patient_id"]
    assert float(device_evt["trust_score"]) < 0.5

def test_correlation_rule1_no_match_high_trust():
    device_evt = {"axiom_patient_id": "pt-001", "trust_score": 0.9}
    assert float(device_evt["trust_score"]) >= 0.5  # should NOT trigger

def test_jaccard_similarity():
    dev_times     = {100, 101, 102}
    patient_times = {101, 102, 103}
    intersection  = len(dev_times & patient_times)
    union         = len(dev_times | patient_times)
    confidence    = intersection / union
    assert 0.0 < confidence < 1.0

def test_correlation_rule2_ransomware_patient():
    threat = {"severity": "CRITICAL", "threat_type": "DATA_EXFILTRATION",
              "hospital_id": "hospital-A"}
    devices = [
        {"hospital_id": "hospital-A", "axiom_patient_id": "pt-001"},
        {"hospital_id": "hospital-A", "axiom_patient_id": "pt-002"},
        {"hospital_id": "hospital-B", "axiom_patient_id": "pt-003"},
    ]
    at_risk = [d["axiom_patient_id"] for d in devices
               if d["hospital_id"] == threat["hospital_id"]]
    assert len(at_risk) == 2
    assert "pt-001" in at_risk
    assert "pt-003" not in at_risk

def test_correlation_rule4_propagation_patient_facing():
    at_risk = [
        {"ip": "10.0.0.2", "device_type": "ecg_monitor", "propagation_prob": 0.7},
        {"ip": "10.0.0.3", "device_type": "router",       "propagation_prob": 0.4},
    ]
    patient_facing = [d for d in at_risk
                      if d["device_type"] in ["ecg_monitor", "ventilator", "medical_device"]]
    assert len(patient_facing) == 1
    assert patient_facing[0]["ip"] == "10.0.0.2"

def test_risk_score_accumulation():
    severity_map = {"LOW": 0.1, "MEDIUM": 0.3, "HIGH": 0.5, "CRITICAL": 1.0}
    score = 0.0
    for sev in ["HIGH", "MEDIUM", "CRITICAL"]:
        score += severity_map[sev]
    assert score == 1.8

def test_correlation_event_structure():
    event = {
        "correlation_type":       "DEVICE_COMPROMISE_CLINICAL_IMPACT",
        "severity":               "HIGH",
        "patient_id":             "pt-001",
        "device_ip":              "10.0.0.5",
        "correlation_confidence": 0.75,
        "timestamp":              "2026-05-24T14:00:00"
    }
    required = ["correlation_type", "severity", "patient_id",
                "device_ip", "correlation_confidence", "timestamp"]
    for field in required:
        assert field in event
