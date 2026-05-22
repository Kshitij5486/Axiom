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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)