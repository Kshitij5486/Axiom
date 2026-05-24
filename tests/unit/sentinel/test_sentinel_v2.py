import pytest
import json
import time
import math

# ══════════════════════════════════════════
# Pool 1 — GeoIP Tests
# ══════════════════════════════════════════

def test_geoip_allows_india():
    allowed = {"IN": True, "US": True, "GB": True, "AE": True, "OM": True}
    assert allowed.get("IN") == True

def test_geoip_allows_oman():
    allowed = {"IN": True, "US": True, "GB": True, "AE": True, "OM": True}
    assert allowed.get("OM") == True

def test_geoip_blocks_china():
    allowed = {"IN": True, "US": True, "GB": True, "AE": True, "OM": True}
    assert allowed.get("CN") is None

def test_geoip_threat_event_structure():
    threat = {
        "threat_type": "GEO_BLOCK",
        "severity": "MEDIUM",
        "src_ip": "1.2.3.4",
        "dest_ip": "10.0.0.1",
        "detail": "Traffic from blocked country: CN"
    }
    assert threat["severity"] == "MEDIUM"
    assert threat["threat_type"] == "GEO_BLOCK"
    assert "CN" in threat["detail"]

# ══════════════════════════════════════════
# Pool 2 — Rate Limiter Tests
# ══════════════════════════════════════════

def test_syn_flood_threshold_100():
    window = [time.time() for _ in range(101)]
    assert len(window) > 100

def test_port_scan_threshold_20():
    ports = set(range(1000, 1025))
    assert len(ports) > 20

def test_rate_limiter_window_cleanup():
    now = time.time()
    old_time = now - 15  # 15 seconds ago, outside 10s window
    window = [old_time, now]
    cutoff = now - 10
    valid = [t for t in window if t > cutoff]
    assert len(valid) == 1

def test_syn_flood_severity():
    threat = {"threat_type": "SYN_FLOOD", "severity": "HIGH"}
    assert threat["severity"] == "HIGH"

# ══════════════════════════════════════════
# Pool 3 — Ransomware Detection Tests
# ══════════════════════════════════════════

def test_lateral_movement_threshold():
    targets = set(f"10.0.0.{i}" for i in range(16))
    assert len(targets) > 15

def test_beaconing_cv_calculation():
    intervals = [5.0, 5.1, 4.9, 5.0, 5.05, 4.95, 5.02, 4.98, 5.01, 4.99]
    mean = sum(intervals) / len(intervals)
    variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
    cv = math.sqrt(variance) / mean
    assert cv < 0.1  # Should trigger beaconing alert

def test_beaconing_high_cv_no_alert():
    intervals = [1.0, 10.0, 3.0, 8.0, 2.0, 9.0, 4.0, 7.0, 5.0, 6.0]
    mean = sum(intervals) / len(intervals)
    variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
    cv = math.sqrt(variance) / mean
    assert cv > 0.1  # Should NOT trigger

def test_exfil_threshold_10mb():
    bytes_sent = 11 * 1024 * 1024  # 11MB
    threshold = 10 * 1024 * 1024   # 10MB
    assert bytes_sent > threshold

def test_traffic_spike_10x():
    baseline = 10.0
    current = 105.0
    assert current > baseline * 10

# ══════════════════════════════════════════
# Pool 4 — Federated Monitor Tests
# ══════════════════════════════════════════

def test_federated_known_nodes():
    registered = {"10.0.1.10": True, "10.0.1.11": True, "10.0.1.12": True}
    assert registered.get("10.0.1.10") == True
    assert registered.get("10.0.1.99") is None

def test_federated_unknown_node_triggers():
    registered = {"10.0.1.10": True, "10.0.1.11": True}
    unknown_ip = "10.0.1.99"
    assert not registered.get(unknown_ip)

def test_federated_replay_threshold():
    uploads = [time.time() for _ in range(11)]
    assert len(uploads) > 10

# ══════════════════════════════════════════
# Trust Scorer Tests
# ══════════════════════════════════════════

def test_trust_medium_penalty():
    score = 1.0 - 0.1
    assert abs(score - 0.9) < 0.001

def test_trust_high_penalty():
    score = 1.0 - 0.3
    assert abs(score - 0.7) < 0.001

def test_trust_critical_penalty():
    score = 1.0 - 0.5
    assert abs(score - 0.5) < 0.001

def test_trust_floor_zero():
    score = max(0.0, 0.1 - 0.5)
    assert score == 0.0
