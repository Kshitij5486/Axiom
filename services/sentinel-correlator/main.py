import json
import logging
import threading
import time
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sentinel-correlator")

app = FastAPI(title="Sentinel Correlator", version="1.0.0")

KAFKA_BROKERS       = ["localhost:9094"]
CAUSAL_ENGINE_URL   = "http://localhost:8081"
GRAPH_SERVICE_URL   = "http://localhost:8091"
WINDOW_SECONDS      = 300  # 5-minute sliding window

# ── In-memory event windows ──
# Each window: list of {timestamp, event}
patient_alerts   = []   # from patient.alerts
sentinel_threats = []   # from sentinel.threats
sentinel_devices = []   # from sentinel.devices
correlations     = []   # published correlations

windows_lock = threading.Lock()

# ── Kafka Producer ──
producer = None
def get_producer():
    global producer
    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
        except Exception as e:
            log.warning(f"[KAFKA] Producer error: {e}")
    return producer

def publish_correlation(event: dict):
    p = get_producer()
    if p:
        try:
            p.send("sentinel.correlations", event)
            p.flush()
        except Exception as e:
            log.warning(f"[KAFKA] Publish error: {e}")
    with windows_lock:
        correlations.append(event)
        if len(correlations) > 10000:
            correlations.pop(0)
    log.info(f"[CORRELATOR] {event['correlation_type']} patient={event.get('patient_id','?')} severity={event.get('severity','?')}")

def clean_window(lst: list) -> list:
    cutoff = time.time() - WINDOW_SECONDS
    return [e for e in lst if e["ts"] > cutoff]

# ── Rule 1: Device-Patient Correlation ──
def check_device_patient_correlation():
    with windows_lock:
        devices_window  = clean_window(sentinel_devices)
        patients_window = clean_window(patient_alerts)

    low_trust_devices = [
        e for e in devices_window
        if float(e["event"].get("trust_score", 1.0)) < 0.5
        and e["event"].get("axiom_patient_id")
    ]

    for dev_evt in low_trust_devices:
        patient_id = dev_evt["event"].get("axiom_patient_id")
        device_ip  = dev_evt["event"].get("ip", dev_evt["event"].get("src_ip",""))

        # Find matching patient alert in same window
        matching = [
            p for p in patients_window
            if p["event"].get("patient_id") == patient_id
        ]

        if matching:
            # Jaccard similarity of time windows
            dev_times     = {int(dev_evt["ts"])}
            patient_times = {int(p["ts"]) for p in matching}
            intersection  = len(dev_times & patient_times)
            union         = len(dev_times | patient_times)
            confidence    = intersection / union if union > 0 else 0.5

            event = {
                "correlation_type":      "DEVICE_COMPROMISE_CLINICAL_IMPACT",
                "severity":              "HIGH",
                "patient_id":            patient_id,
                "device_ip":             device_ip,
                "device_trust_score":    dev_evt["event"].get("trust_score", 0),
                "patient_anomaly":       matching[0]["event"],
                "correlation_confidence": round(confidence, 3),
                "timestamp":             datetime.utcnow().isoformat()
            }
            publish_correlation(event)

            # Call causal engine to flag compromised device
            try:
                requests.patch(
                    f"{CAUSAL_ENGINE_URL}/causal/graph/{patient_id}/flag-source",
                    json={
                        "device_ip":        device_ip,
                        "confidence_penalty": 1.0 - float(dev_evt["event"].get("trust_score", 0))
                    },
                    timeout=3
                )
                log.info(f"[CORRELATOR] Flagged causal source for patient={patient_id} device={device_ip}")
            except Exception as e:
                log.warning(f"[CORRELATOR] Causal engine flag failed: {e}")

# ── Rule 2: Ransomware-Clinical Correlation ──
def check_ransomware_clinical():
    with windows_lock:
        threats_window  = clean_window(sentinel_threats)
        devices_window  = clean_window(sentinel_devices)

    critical_threats = [
        e for e in threats_window
        if e["event"].get("severity") == "CRITICAL"
        and e["event"].get("threat_type") in ["DATA_EXFILTRATION", "LATERAL_MOVEMENT", "DEVICE_TRAFFIC_SPIKE"]
    ]

    for threat in critical_threats:
        hospital_id = threat["event"].get("hospital_id", "")
        at_risk_patients = list({
            d["event"].get("axiom_patient_id")
            for d in devices_window
            if d["event"].get("hospital_id") == hospital_id
            and d["event"].get("axiom_patient_id")
        })

        if at_risk_patients:
            event = {
                "correlation_type": "RANSOMWARE_PATIENT_RISK",
                "severity":         "CRITICAL",
                "hospital_id":      hospital_id,
                "threat_type":      threat["event"].get("threat_type"),
                "at_risk_patients": at_risk_patients,
                "threat_detail":    threat["event"].get("detail", ""),
                "timestamp":        datetime.utcnow().isoformat()
            }
            publish_correlation(event)

# ── Rule 3: Federated Poisoning + Clinical Impact ──
def check_federated_clinical():
    with windows_lock:
        threats_window = clean_window(sentinel_threats)

    federated_attacks = [
        e for e in threats_window
        if e["event"].get("threat_type") == "FEDERATED_ATTACK"
    ]

    if not federated_attacks:
        return

    # Query causal engine for recent CI widening
    try:
        resp = requests.get(
            f"{CAUSAL_ENGINE_URL}/causal/ci-changes",
            timeout=3
        )
        if resp.status_code == 200:
            ci_data = resp.json()
            affected_patients = ci_data.get("widened_patients", [])
            if affected_patients:
                event = {
                    "correlation_type":   "FEDERATED_POISONING_CLINICAL_IMPACT",
                    "severity":           "HIGH",
                    "federated_attacks":  len(federated_attacks),
                    "affected_patients":  affected_patients,
                    "detail":             "Federated attack may have degraded recommendation quality",
                    "timestamp":          datetime.utcnow().isoformat()
                }
                publish_correlation(event)
    except Exception as e:
        log.warning(f"[CORRELATOR] CI check failed (causal engine unavailable): {e}")

# ── Rule 4: Device Compromise Propagation ──
def check_propagation():
    with windows_lock:
        devices_window = clean_window(sentinel_devices)

    untrusted = [
        e for e in devices_window
        if float(e["event"].get("trust_score", 1.0)) < 0.3
    ]

    for dev in untrusted:
        device_ip = dev["event"].get("ip", dev["event"].get("src_ip",""))
        if not device_ip:
            continue

        try:
            resp = requests.post(
                f"{GRAPH_SERVICE_URL}/sentinel/graph/counterfactual",
                json={"compromised_ip": device_ip, "attack_type": "TRUST_DEGRADED"},
                timeout=3
            )
            if resp.status_code == 200:
                result = resp.json()
                at_risk = result.get("at_risk_devices", [])
                patient_facing = [
                    d for d in at_risk
                    if d.get("device_type") in ["ecg_monitor", "ventilator",
                                                 "infusion_pump", "medical_device"]
                ]
                if patient_facing:
                    event = {
                        "correlation_type":       "DEVICE_COMPROMISE_PROPAGATION",
                        "severity":               "HIGH",
                        "source_device":          device_ip,
                        "at_risk_devices":        at_risk[:5],
                        "patient_facing_at_risk": patient_facing,
                        "timestamp":              datetime.utcnow().isoformat()
                    }
                    publish_correlation(event)
        except Exception as e:
            log.warning(f"[CORRELATOR] Propagation check failed: {e}")

# ── Correlation Engine Loop ──
def correlation_loop():
    log.info("[CORRELATOR] Correlation engine started")
    while True:
        time.sleep(30)  # Run every 30 seconds
        try:
            check_device_patient_correlation()
            check_ransomware_clinical()
            check_federated_clinical()
            check_propagation()
        except Exception as e:
            log.warning(f"[CORRELATOR] Loop error: {e}")

# ── Kafka Consumers ──
def consume_topic(topic: str, window: list, group: str):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BROKERS,
            group_id=group,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            consumer_timeout_ms=1000
        )
        log.info(f"[KAFKA] Consuming {topic}")
        while True:
            try:
                for msg in consumer:
                    with windows_lock:
                        window.append({"ts": time.time(), "event": msg.value})
                        # Keep only last 5 min
                        cutoff = time.time() - WINDOW_SECONDS
                        window[:] = [e for e in window if e["ts"] > cutoff]
            except Exception as e:
                log.warning(f"[KAFKA] {topic} error: {e}")
                time.sleep(5)
    except Exception as e:
        log.warning(f"[KAFKA] Cannot connect to {topic}: {e}")

# ── API Endpoints ──
@app.on_event("startup")
async def startup():
    threading.Thread(
        target=consume_topic,
        args=("patient.alerts", patient_alerts, "correlator-patients"),
        daemon=True
    ).start()
    threading.Thread(
        target=consume_topic,
        args=("sentinel.threats", sentinel_threats, "correlator-threats"),
        daemon=True
    ).start()
    threading.Thread(
        target=consume_topic,
        args=("sentinel.devices", sentinel_devices, "correlator-devices"),
        daemon=True
    ).start()
    threading.Thread(target=correlation_loop, daemon=True).start()
    log.info("[STARTUP] Sentinel Correlator ready")

@app.get("/health")
def health():
    return {
        "status":          "ok",
        "service":         "sentinel-correlator",
        "correlations":    len(correlations),
        "patient_alerts":  len(patient_alerts),
        "threats":         len(sentinel_threats),
        "device_events":   len(sentinel_devices)
    }

@app.get("/sentinel/correlations")
def get_correlations(limit: int = 100):
    with windows_lock:
        return {
            "correlations": correlations[-limit:],
            "total":        len(correlations)
        }

@app.get("/sentinel/correlations/patient/{patient_id}")
def get_patient_correlations(patient_id: str):
    with windows_lock:
        patient_corrs = [
            c for c in correlations
            if c.get("patient_id") == patient_id
            or patient_id in c.get("at_risk_patients", [])
            or patient_id in c.get("affected_patients", [])
        ]
    return {
        "patient_id":   patient_id,
        "correlations": patient_corrs,
        "total":        len(patient_corrs)
    }

@app.get("/sentinel/risk/patients")
def get_at_risk_patients():
    with windows_lock:
        risk_map = {}
        for c in correlations:
            pid = c.get("patient_id")
            if pid:
                if pid not in risk_map:
                    risk_map[pid] = {"patient_id": pid, "risk_score": 0.0, "events": []}
                sev = c.get("severity", "MEDIUM")
                risk_map[pid]["risk_score"] += {"LOW": 0.1, "MEDIUM": 0.3, "HIGH": 0.5, "CRITICAL": 1.0}.get(sev, 0.3)
                risk_map[pid]["events"].append(c.get("correlation_type"))

            for pid in c.get("at_risk_patients", []) + c.get("affected_patients", []):
                if pid not in risk_map:
                    risk_map[pid] = {"patient_id": pid, "risk_score": 0.0, "events": []}
                risk_map[pid]["risk_score"] += 0.5
                risk_map[pid]["events"].append(c.get("correlation_type"))

    at_risk = sorted(risk_map.values(), key=lambda x: x["risk_score"], reverse=True)
    return {"at_risk_patients": at_risk, "total": len(at_risk)}
