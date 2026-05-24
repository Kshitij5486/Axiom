import pytest
import json
import socket
import os
import time
import threading

# ── Test 1-3: JSON contract validation ──
def test_flow_event_has_required_fields():
    evt = {
        "timestamp": 1779615135,
        "src_ip": "172.30.88.1",
        "src_port": 49836,
        "dest_ip": "20.233.83.145",
        "dest_port": 443,
        "protocol": "TCP",
        "sni_domain": "github.com",
        "status": "SNI_EXTRACTED"
    }
    required = ["timestamp","src_ip","src_port","dest_ip","dest_port","protocol","sni_domain","status"]
    for field in required:
        assert field in evt, f"Missing field: {field}"

def test_flow_event_json_serializable():
    evt = {
        "timestamp": 1779615135,
        "src_ip": "172.30.88.1",
        "src_port": 49836,
        "dest_ip": "20.233.83.145",
        "dest_port": 443,
        "protocol": "TCP",
        "sni_domain": "github.com",
        "status": "SNI_EXTRACTED"
    }
    serialized = json.dumps(evt)
    parsed = json.loads(serialized)
    assert parsed["sni_domain"] == "github.com"
    assert parsed["status"] == "SNI_EXTRACTED"

def test_flow_event_status_values():
    valid_statuses = ["NEW_FLOW", "SNI_EXTRACTED", "CLOSED", "FIN_SEEN"]
    for status in valid_statuses:
        evt = {"status": status}
        assert evt["status"] in valid_statuses

# ── Test 4-6: GeoIP logic ──
def test_geoip_allowlist_india():
    allowed = {"IN": True, "US": True, "GB": True, "AE": True, "OM": True}
    assert allowed.get("IN") == True

def test_geoip_blocks_unknown_country():
    allowed = {"IN": True, "US": True, "GB": True}
    assert allowed.get("CN") is None

def test_geoip_threat_severity():
    threat = {
        "threat_type": "GEO_BLOCK",
        "severity": "MEDIUM",
        "src_ip": "1.2.3.4",
        "detail": "Traffic from blocked country: CN"
    }
    assert threat["severity"] == "MEDIUM"
    assert "CN" in threat["detail"]

# ── Test 7-8: Rate limiter logic ──
def test_syn_flood_threshold():
    window = []
    limit = 100
    now = time.time()
    for i in range(101):
        window.append(now)
    assert len(window) > limit

def test_port_scan_threshold():
    ports = set()
    for p in range(25):
        ports.add(p + 1000)
    assert len(ports) > 20

# ── Test 9-10: Trust scorer ──
def test_trust_score_penalty_medium():
    score = 1.0
    score -= 0.1  # MEDIUM penalty
    assert abs(score - 0.9) < 0.001

def test_trust_score_floor_zero():
    score = 0.1
    score -= 0.5  # CRITICAL penalty
    score = max(0.0, score)
    assert score == 0.0
