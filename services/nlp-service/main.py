"""
Axiom NLP Service
Port 8083

BioBERT clinical NER + relation extraction
+ Isolation Forest anomaly detection
+ WebSocket alert broadcasting
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.nlp")

app = FastAPI(
    title="Axiom NLP Service",
    description=(
        "BioBERT clinical NER, relation extraction, "
        "anomaly detection, WebSocket alerts."
    ),
    version="0.6.0",
)

_start_time = time.time()
_biobert_loaded = False
_connected_clients: List[WebSocket] = []


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-nlp",
        "version": "0.6.0",
        "biobert_loaded": _biobert_loaded,
        "connected_clients": len(_connected_clients),
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time clinical alerts.
    React dashboard connects here in Sprint 8.
    """
    await websocket.accept()
    _connected_clients.append(websocket)
    logger.info(
        "WebSocket client connected. "
        "Total: %d", len(_connected_clients)
    )
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong keepalive
            await websocket.send_text(
                f"connected:{len(_connected_clients)}"
            )
    except WebSocketDisconnect:
        _connected_clients.remove(websocket)
        logger.info(
            "WebSocket client disconnected. "
            "Total: %d", len(_connected_clients)
        )


async def broadcast_alert(alert: dict):
    """Broadcast alert to all connected WebSocket clients."""
    import json
    disconnected = []
    for client in _connected_clients:
        try:
            await client.send_text(json.dumps(alert))
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        _connected_clients.remove(client)


@app.get("/nlp/notes/{patient_id}")
def get_patient_notes(patient_id: str):
    """Get clinical notes for a patient."""
    from db import get_clinical_notes
    notes = get_clinical_notes(patient_id, limit=10)
    return {
        "patient_id": patient_id,
        "notes": notes,
        "total": len(notes),
    }


@app.get("/anomaly/alerts/{patient_id}")
def get_patient_alerts(patient_id: str):
    """Get anomaly alerts for a patient."""
    from db import get_patient_alerts
    alerts = get_patient_alerts(patient_id)
    return {
        "patient_id": patient_id,
        "alerts": alerts,
        "total": len(alerts),
    }



    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)

@app.post("/nlp/extract/{patient_id}")
def extract_patient_entities(patient_id: str):
    """
    Extract clinical entities from all notes
    for a patient using dictionary NER.
    Returns conditions, drugs, vitals, symptoms.
    """
    from db import get_clinical_notes, save_nlp_extraction
    from entity_extractor import extract_from_note

    notes = get_clinical_notes(patient_id, limit=5)
    if not notes:
        return {
            "patient_id": patient_id,
            "error": "No clinical notes found.",
        }

    all_results = []
    for note in notes:
        result = extract_from_note(note)
        extraction_id = save_nlp_extraction(
            patient_id=patient_id,
            note_id=note.get(
                "patient_name", "unknown"
            ),
            entities=result["entities"],
            relations=[],
            model_used=result["model"],
        )
        result["extraction_id"] = extraction_id
        all_results.append(result)

    # Aggregate all entities
    all_entities = []
    for r in all_results:
        all_entities.extend(r["entities"])

    # Group by label
    by_label = {}
    for ent in all_entities:
        label = ent["label"]
        if label not in by_label:
            by_label[label] = []
        by_label[label].append(ent["canonical"])

    return {
        "patient_id": patient_id,
        "notes_processed": len(notes),
        "total_entities": len(all_entities),
        "entities_by_label": by_label,
        "model": all_results[0]["model"] if all_results else "none",
        "extractions": all_results,
    }


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)

@app.post("/nlp/relations/{patient_id}")
def extract_patient_relations(patient_id: str):
    """
    Extract causal relations from clinical notes.
    Relations feed into causal DAG via EWMA update.

    Example output:
      "furosemide caused creatinine rise"
      -> {cause: furosemide, effect: creatinine,
          direction: causes, nlp_effect: +0.038}
    """
    from db import get_clinical_notes
    from entity_extractor import extract_from_note
    from relation_extractor import (
        extract_relations_from_note,
    )

    notes = get_clinical_notes(patient_id, limit=5)
    if not notes:
        return {
            "patient_id": patient_id,
            "error": "No clinical notes found.",
        }

    all_relations = []
    for note in notes:
        entity_result = extract_from_note(note)
        rel_result = extract_relations_from_note(
            note,
            entities=entity_result["entities"],
        )
        all_relations.extend(rel_result["relations"])

    return {
        "patient_id": patient_id,
        "notes_processed": len(notes),
        "total_relations": len(all_relations),
        "relations": all_relations,
    }


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)

@app.post("/nlp/enrich/{patient_id}")
def enrich_causal_graph(patient_id: str):
    """
    Full NLP enrichment pipeline:
      1. Extract entities from clinical notes
      2. Extract causal relations
      3. Update causal graph via EWMA
      4. Publish to causal.updates Kafka topic

    This runs in <100ms vs 20s for full rebuild.
    """
    from db import get_clinical_notes
    from entity_extractor import extract_from_note
    from relation_extractor import (
        extract_relations_from_note,
    )
    from dag_updater import update_causal_graph

    notes = get_clinical_notes(patient_id, limit=5)
    if not notes:
        return {
            "patient_id": patient_id,
            "error": "No clinical notes found.",
        }

    all_relations = []
    all_entities = []

    for note in notes:
        entity_result = extract_from_note(note)
        all_entities.extend(
            entity_result["entities"]
        )
        rel_result = extract_relations_from_note(
            note,
            entities=entity_result["entities"],
        )
        all_relations.extend(rel_result["relations"])

    # Update causal DAG
    update_result = update_causal_graph(
        patient_id=patient_id,
        relations=all_relations,
    )

    return {
        "patient_id": patient_id,
        "notes_processed": len(notes),
        "entities_extracted": len(all_entities),
        "relations_extracted": len(all_relations),
        "dag_update": update_result,
    }


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)

@app.post("/anomaly/train/{patient_id}")
def train_anomaly_detector(patient_id: str):
    """
    Train Isolation Forest on patient vital history.
    Uses last 20 readings of each vital from PostgreSQL.
    """
    from db import get_patient_vitals_series
    from anomaly_detector import get_registry
    import numpy as np

    registry = get_registry()

    # Build vitals matrix
    features = [
        "glucose", "creatinine", "heart_rate",
        "systolic_bp", "spo2",
    ]
    feature_series = {}
    for feature in features:
        series = get_patient_vitals_series(
            patient_id, feature, limit=20
        )
        feature_series[feature] = [
            r["value_quantity"] for r in series
        ]

    min_len = min(
        len(v) for v in feature_series.values()
    )
    if min_len < 5:
        return {
            "patient_id": patient_id,
            "error": f"Insufficient data: {min_len} readings",
        }

    matrix = np.array([
        [feature_series[f][i] for f in features]
        for i in range(min_len)
    ], dtype=np.float32)

    success = registry.train_patient(
        patient_id, matrix
    )

    return {
        "patient_id": patient_id,
        "trained": success,
        "samples": min_len,
        "features": features,
    }


@app.post("/anomaly/score/{patient_id}")
def score_patient_vitals(patient_id: str):
    """
    Score current patient vitals for anomalies.
    Returns Isolation Forest score + threshold alerts
    + 2-hour predictive alerts.
    """
    from db import get_patient_vitals_series
    from anomaly_detector import get_registry
    import numpy as np

    registry = get_registry()
    detector = registry.get_or_create(patient_id)

    if not detector.is_trained:
        return {
            "patient_id": patient_id,
            "error": "Train detector first: "
                     "POST /anomaly/train/{patient_id}",
        }

    # Get latest reading
    features = [
        "glucose", "creatinine", "heart_rate",
        "systolic_bp", "spo2",
    ]
    latest = {}
    for feature in features:
        series = get_patient_vitals_series(
            patient_id, feature, limit=1
        )
        if series:
            latest[feature] = series[0]["value_quantity"]

    # Score current reading
    score_result = detector.score(latest)

    # Predictive 2-hour alerts
    predictive_alerts = []
    for feature in features:
        series = get_patient_vitals_series(
            patient_id, feature, limit=5
        )
        if len(series) >= 3:
            values = [
                r["value_quantity"] for r in series
            ]
            pred = detector.predict_2h(values, feature)
            if pred and pred.get(
                "will_breach_threshold"
            ):
                predictive_alerts.append(pred)

    score_result["predictive_alerts"] = predictive_alerts
    score_result["current_vitals"] = latest

    # Convert numpy types to Python native for JSON
    import json, numpy as np
    def convert(obj):
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list): return [convert(i) for i in obj]
        return obj

    return convert(score_result)


@app.post("/anomaly/train-all")
def train_all_detectors():
    """Train anomaly detectors for all patients."""
    from db import get_all_patient_ids
    trained = 0
    failed = 0
    for patient_id in get_all_patient_ids():
        try:
            from fastapi.testclient import TestClient
            result = train_anomaly_detector(patient_id)
            if result.get("trained"):
                trained += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return {
        "trained": trained,
        "failed": failed,
        "total": trained + failed,
    }


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)

@app.post("/anomaly/scan/{patient_id}")
def full_anomaly_scan(patient_id: str):
    """
    Full anomaly scan with alert pipeline:
      1. Score vitals (Isolation Forest)
      2. Compute 2h predictive alerts
      3. Save alerts to MongoDB
      4. Publish to Kafka alerts.clinical
      5. Generate ZK proof per alert
      6. Broadcast via WebSocket

    This is the production endpoint called
    every time new vitals arrive.
    """
    from db import get_patient_vitals_series
    from anomaly_detector import get_registry
    from alert_pipeline import get_pipeline
    import numpy as np

    registry = get_registry()
    pipeline = get_pipeline()

    # Auto-train if not trained
    detector = registry.get_or_create(patient_id)
    if not detector.is_trained:
        features = [
            "glucose", "creatinine", "heart_rate",
            "systolic_bp", "spo2",
        ]
        feature_series = {}
        for feature in features:
            series = get_patient_vitals_series(
                patient_id, feature, limit=20
            )
            feature_series[feature] = [
                r["value_quantity"] for r in series
            ]
        min_len = min(
            len(v) for v in feature_series.values()
        )
        if min_len >= 5:
            matrix = np.array([
                [feature_series[f][i] for f in features]
                for i in range(min_len)
            ], dtype=np.float32)
            registry.train_patient(patient_id, matrix)

    if not detector.is_trained:
        return {
            "patient_id": patient_id,
            "error": "Insufficient data to train",
        }

    # Get latest vitals
    features = [
        "glucose", "creatinine", "heart_rate",
        "systolic_bp", "spo2",
    ]
    latest = {}
    for feature in features:
        series = get_patient_vitals_series(
            patient_id, feature, limit=1
        )
        if series:
            latest[feature] = series[0]["value_quantity"]

    # Score
    score_result = detector.score(latest)

    # Predictive alerts
    predictive_alerts = []
    for feature in features:
        series = get_patient_vitals_series(
            patient_id, feature, limit=5
        )
        if len(series) >= 3:
            values = [
                r["value_quantity"] for r in series
            ]
            pred = detector.predict_2h(values, feature)
            if pred and pred.get(
                "will_breach_threshold"
            ):
                predictive_alerts.append(pred)

    # Process through alert pipeline
    processed_alerts = pipeline.process_alerts(
        patient_id=patient_id,
        alerts=score_result.get("alerts", []),
        predictive_alerts=predictive_alerts,
        websocket_clients=_connected_clients,
    )

    import numpy as np
    def convert(obj):
        if isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        if hasattr(obj, 'item'):
            return obj.item()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(i) for i in obj]
        return obj

    return convert({
        "patient_id": patient_id,
        "anomaly_detected": score_result.get("anomaly"),
        "isolation_forest_score": score_result.get(
            "isolation_forest_score"
        ),
        "alerts_fired": len(processed_alerts),
        "alerts": processed_alerts,
        "predictive_alerts": predictive_alerts,
        "current_vitals": latest,
        "pipeline_status": pipeline.status(),
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)