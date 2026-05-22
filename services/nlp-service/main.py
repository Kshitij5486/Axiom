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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)