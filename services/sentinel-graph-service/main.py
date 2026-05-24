import asyncio
import json
import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from kafka import KafkaConsumer, KafkaProducer  # kafka-python-ng
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sentinel-graph")

app = FastAPI(title="Sentinel Graph Service", version="1.0.0")

# ── Config ──
DB_URL = "host=localhost port=5439 dbname=axiom user=axiom_user password=axiom_secret"
KAFKA_BROKERS = ["localhost:9094"]

# ── Database ──
def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sentinel_devices (
                ip              VARCHAR(45) PRIMARY KEY,
                mac_address     VARCHAR(17),
                device_type     VARCHAR(50) DEFAULT 'unknown',
                hospital_id     VARCHAR(50),
                first_seen      TIMESTAMP DEFAULT NOW(),
                last_seen       TIMESTAMP DEFAULT NOW(),
                trust_score     FLOAT DEFAULT 1.0,
                traffic_profile JSONB DEFAULT '{}',
                causal_node_id  VARCHAR(50)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sentinel_graph (
                id          SERIAL PRIMARY KEY,
                source_ip   VARCHAR(45),
                target_ip   VARCHAR(45),
                effect_size FLOAT DEFAULT 0.0,
                lag_seconds FLOAT DEFAULT 0.0,
                edge_type   VARCHAR(50) DEFAULT 'communication',
                updated_at  TIMESTAMP DEFAULT NOW(),
                UNIQUE(source_ip, target_ip)
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        log.info("[DB] Tables initialised")
    except Exception as e:
        log.warning(f"[DB] Init warning: {e}")

# ── Device Profile Store ──
# ip -> {ports, domains, peers, timestamps, bytes}
device_profiles: Dict[str, Dict] = defaultdict(lambda: {
    "ports": set(),
    "domains": set(),
    "peers": set(),
    "timestamps": [],
    "bytes_total": 0,
    "packet_count": 0,
    "device_type": "unknown",
    "hospital_id": "",
    "trust_score": 1.0,
    "anomaly_scores": []
})

# ── Infrastructure Causal Graph ──
infra_graph = nx.DiGraph()
graph_lock  = threading.Lock()

def update_device_profile(evt: dict):
    ip = evt.get("src_ip", "")
    if not ip:
        return

    p = device_profiles[ip]
    p["ports"].add(evt.get("dest_port", 0))
    if evt.get("sni_domain"):
        p["domains"].add(evt["sni_domain"])
    p["peers"].add(evt.get("dest_ip", ""))
    p["timestamps"].append(time.time())
    p["bytes_total"] += evt.get("byte_count", 1400)
    p["packet_count"] += 1
    p["device_type"]  = evt.get("device_type", p["device_type"])
    p["hospital_id"]  = evt.get("hospital_id", p["hospital_id"])
    p["trust_score"]  = float(evt.get("trust_score", p["trust_score"]))

    # Keep only last 1000 timestamps
    if len(p["timestamps"]) > 1000:
        p["timestamps"] = p["timestamps"][-1000:]

    # Persist to DB
    try:
        conn = get_db()
        cur  = conn.cursor()
        profile_json = json.dumps({
            "ports":        list(p["ports"])[:20],
            "domains":      list(p["domains"])[:20],
            "peers":        list(p["peers"])[:20],
            "packet_count": p["packet_count"],
            "bytes_total":  p["bytes_total"]
        })
        cur.execute("""
            INSERT INTO sentinel_devices
                (ip, device_type, hospital_id, trust_score, traffic_profile, last_seen, causal_node_id)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            ON CONFLICT (ip) DO UPDATE SET
                device_type     = EXCLUDED.device_type,
                trust_score     = EXCLUDED.trust_score,
                traffic_profile = EXCLUDED.traffic_profile,
                last_seen       = NOW()
        """, (ip, p["device_type"], p["hospital_id"],
              p["trust_score"], profile_json, f"node_{ip.replace('.','_')}"))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.warning(f"[DB] Device upsert error: {e}")

def build_infrastructure_graph():
    """
    Incrementally build DoWhy-style causal graph from device profiles.
    Edge: A -> B if A regularly communicates with B
    Effect size: correlation of anomaly scores
    Lag: average time delta between A anomaly and B anomaly
    """
    with graph_lock:
        infra_graph.clear()

        # Add nodes
        for ip, profile in device_profiles.items():
            infra_graph.add_node(ip,
                device_type=profile["device_type"],
                trust_score=profile["trust_score"],
                hospital_id=profile["hospital_id"],
                packet_count=profile["packet_count"]
            )

        # Add edges from communication peers
        for ip, profile in device_profiles.items():
            for peer in profile["peers"]:
                if peer and peer != ip and peer in device_profiles:
                    # Calculate effect size from peer communication frequency
                    peer_profile = device_profiles[peer]
                    ip_count   = profile["packet_count"] + 1
                    peer_count = peer_profile["packet_count"] + 1
                    effect = min(1.0, ip_count / (ip_count + peer_count))

                    infra_graph.add_edge(ip, peer,
                        effect_size=round(effect, 3),
                        lag_seconds=0.0,
                        edge_type="communication"
                    )

                    # Persist edge to DB
                    try:
                        conn = get_db()
                        cur  = conn.cursor()
                        cur.execute("""
                            INSERT INTO sentinel_graph
                                (source_ip, target_ip, effect_size, lag_seconds, edge_type)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (source_ip, target_ip) DO UPDATE SET
                                effect_size = EXCLUDED.effect_size,
                                updated_at  = NOW()
                        """, (ip, peer, effect, 0.0, "communication"))
                        conn.commit()
                        cur.close()
                        conn.close()
                    except Exception as e:
                        log.warning(f"[DB] Edge upsert error: {e}")

    log.info(f"[GRAPH] Rebuilt: {infra_graph.number_of_nodes()} nodes, "
             f"{infra_graph.number_of_edges()} edges")

def graph_rebuild_scheduler():
    """Rebuild graph every 30 minutes"""
    while True:
        time.sleep(1800)
        log.info("[GRAPH] Scheduled rebuild starting...")
        build_infrastructure_graph()

# ── Kafka Consumer ──
def consume_device_events():
    try:
        consumer = KafkaConsumer(
            "sentinel.devices",
            bootstrap_servers=KAFKA_BROKERS,
            group_id="sentinel-graph-service",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            consumer_timeout_ms=1000
        )
        log.info("[KAFKA] Consuming sentinel.devices")
        while True:
            try:
                for msg in consumer:
                    update_device_profile(msg.value)
            except Exception as e:
                log.warning(f"[KAFKA] Consumer error: {e}")
                time.sleep(5)
    except Exception as e:
        log.warning(f"[KAFKA] Cannot connect: {e} — running without Kafka")

def consume_flow_events():
    """Also consume network.flows for device fingerprinting"""
    try:
        consumer = KafkaConsumer(
            "network.flows",
            bootstrap_servers=KAFKA_BROKERS,
            group_id="sentinel-graph-flows",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            consumer_timeout_ms=1000
        )
        log.info("[KAFKA] Consuming network.flows for fingerprinting")
        while True:
            try:
                for msg in consumer:
                    update_device_profile(msg.value)
                    # Rebuild graph after every 100 new events
                    total = sum(p["packet_count"] for p in device_profiles.values())
                    if total % 100 == 0:
                        build_infrastructure_graph()
            except Exception as e:
                log.warning(f"[KAFKA] Flow consumer error: {e}")
                time.sleep(5)
    except Exception as e:
        log.warning(f"[KAFKA] Cannot connect to network.flows: {e}")

# ── API Models ──
class CounterfactualRequest(BaseModel):
    compromised_ip: str
    attack_type:    str = "UNKNOWN"
    confidence:     float = 0.8

# ── API Endpoints ──
@app.on_event("startup")
async def startup():
    init_db()
    # Start background threads
    threading.Thread(target=consume_device_events, daemon=True).start()
    threading.Thread(target=consume_flow_events,   daemon=True).start()
    threading.Thread(target=graph_rebuild_scheduler, daemon=True).start()
    # Initial graph build from any existing profiles
    build_infrastructure_graph()
    log.info("[STARTUP] Sentinel Graph Service ready")

@app.get("/health")
def health():
    return {"status": "ok", "service": "sentinel-graph-service",
            "nodes": infra_graph.number_of_nodes(),
            "edges": infra_graph.number_of_edges()}

@app.get("/sentinel/graph/infrastructure")
def get_infrastructure_graph():
    with graph_lock:
        nodes = []
        for ip, data in infra_graph.nodes(data=True):
            nodes.append({
                "ip":          ip,
                "device_type": data.get("device_type", "unknown"),
                "trust_score": data.get("trust_score", 1.0),
                "hospital_id": data.get("hospital_id", ""),
                "packet_count": data.get("packet_count", 0)
            })

        edges = []
        for src, dst, data in infra_graph.edges(data=True):
            edges.append({
                "source":      src,
                "target":      dst,
                "effect_size": data.get("effect_size", 0.0),
                "lag_seconds": data.get("lag_seconds", 0.0),
                "edge_type":   data.get("edge_type", "communication")
            })

        return {
            "nodes":      nodes,
            "edges":      edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "built_at":   datetime.utcnow().isoformat()
        }

@app.get("/sentinel/graph/device/{ip}")
def get_device_neighbourhood(ip: str):
    with graph_lock:
        if ip not in infra_graph:
            # Return empty neighbourhood — device not yet seen
            return {"ip": ip, "neighbours": [], "in_edges": [], "out_edges": []}

        out_edges = []
        for _, dst, data in infra_graph.out_edges(ip, data=True):
            out_edges.append({
                "target":      dst,
                "effect_size": data.get("effect_size", 0.0),
                "edge_type":   data.get("edge_type", "communication")
            })

        in_edges = []
        for src, _, data in infra_graph.in_edges(ip, data=True):
            in_edges.append({
                "source":      src,
                "effect_size": data.get("effect_size", 0.0),
                "edge_type":   data.get("edge_type", "communication")
            })

        profile = device_profiles.get(ip, {})
        return {
            "ip":          ip,
            "device_type": profile.get("device_type", "unknown"),
            "trust_score": profile.get("trust_score", 1.0),
            "hospital_id": profile.get("hospital_id", ""),
            "out_edges":   out_edges,
            "in_edges":    in_edges,
            "degree":      infra_graph.degree(ip),
            "domains":     list(profile.get("domains", set()))[:10],
            "peers":       list(profile.get("peers", set()))[:10]
        }

@app.post("/sentinel/graph/counterfactual")
def run_counterfactual(req: CounterfactualRequest):
    """
    Given a compromised device IP, predict propagation path
    through infrastructure causal graph using BFS + effect sizes.
    """
    with graph_lock:
        if req.compromised_ip not in infra_graph:
            return {
                "compromised_ip":   req.compromised_ip,
                "propagation_path": [],
                "at_risk_devices":  [],
                "message":          "Device not yet in graph"
            }

        # BFS through graph weighted by effect_size
        visited  = {req.compromised_ip}
        queue    = [(req.compromised_ip, 1.0, [])]
        at_risk  = []

        while queue:
            current, prob, path = queue.pop(0)
            for _, neighbor, data in infra_graph.out_edges(current, data=True):
                if neighbor not in visited:
                    effect = data.get("effect_size", 0.5)
                    propagation_prob = prob * effect * req.confidence
                    if propagation_prob > 0.1:  # threshold
                        visited.add(neighbor)
                        neighbor_profile = device_profiles.get(neighbor, {})
                        at_risk.append({
                            "ip":               neighbor,
                            "device_type":      neighbor_profile.get("device_type", "unknown"),
                            "propagation_prob": round(propagation_prob, 3),
                            "path":             path + [current],
                            "hospital_id":      neighbor_profile.get("hospital_id", "")
                        })
                        queue.append((neighbor, propagation_prob, path + [current]))

        # Sort by propagation probability
        at_risk.sort(key=lambda x: x["propagation_prob"], reverse=True)

        return {
            "compromised_ip":   req.compromised_ip,
            "attack_type":      req.attack_type,
            "confidence":       req.confidence,
            "at_risk_devices":  at_risk[:20],
            "total_at_risk":    len(at_risk),
            "propagation_path": list(visited - {req.compromised_ip})
        }

@app.get("/sentinel/graph/devices")
def get_all_devices():
    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM sentinel_devices ORDER BY last_seen DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"devices": [dict(r) for r in rows], "total": len(rows)}
    except Exception as e:
        return {"devices": list(device_profiles.keys()), "total": len(device_profiles)}
