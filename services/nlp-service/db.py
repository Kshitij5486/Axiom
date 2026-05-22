"""
NLP Service — Database clients.
PostgreSQL for patient/observation data.
MongoDB for clinical notes and alert history.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from pymongo import MongoClient

logger = logging.getLogger("axiom.nlp.db")

PG_CONFIG = {
    "host":     "localhost",
    "port":     5439,
    "dbname":   "axiom",
    "user":     "axiom_user",
    "password": "axiom_secret",
}

MONGO_URI = (
    "mongodb://axiom_user:axiom_secret"
    "@localhost:27018/axiom_clinical"
    "?authSource=admin"
)


def get_pg_conn():
    return psycopg2.connect(**PG_CONFIG)


def get_mongo_db():
    client = MongoClient(MONGO_URI)
    return client.axiom_clinical


def get_clinical_notes(
    patient_id: str = None,
    limit: int = 10,
) -> list:
    """Fetch clinical notes from MongoDB."""
    db = get_mongo_db()
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    notes = list(
        db.clinical_notes
        .find(query, {"_id": 0})
        .sort("recorded_at", -1)
        .limit(limit)
    )
    return notes


def save_nlp_extraction(
    patient_id: str,
    note_id: str,
    entities: list,
    relations: list,
    model_used: str,
) -> str:
    """Save NLP extraction results to MongoDB."""
    db = get_mongo_db()
    extraction_id = str(uuid.uuid4())
    doc = {
        "extraction_id": extraction_id,
        "patient_id": patient_id,
        "note_id": note_id,
        "entities": entities,
        "relations": relations,
        "model_used": model_used,
        "processed_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }
    db.nlp_extractions.insert_one(doc)

    # Mark note as processed
    db.clinical_notes.update_one(
        {"patient_id": patient_id},
        {"$set": {"nlp_processed": True}},
    )
    return extraction_id


def save_alert(
    patient_id: str,
    alert_type: str,
    feature: str,
    current_value: float,
    threshold: float,
    severity: str,
    message: str,
    zk_proof_hash: str = None,
) -> str:
    """Save anomaly alert to MongoDB."""
    db = get_mongo_db()
    alert_id = str(uuid.uuid4())
    doc = {
        "alert_id": alert_id,
        "patient_id": patient_id,
        "alert_type": alert_type,
        "feature": feature,
        "current_value": current_value,
        "threshold": threshold,
        "severity": severity,
        "message": message,
        "zk_proof_hash": zk_proof_hash,
        "acknowledged": False,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }
    db.alert_history.insert_one(doc)
    return alert_id


def get_patient_alerts(
    patient_id: str, limit: int = 20
) -> list:
    """Get alerts for a patient."""
    db = get_mongo_db()
    alerts = list(
        db.alert_history
        .find(
            {"patient_id": patient_id},
            {"_id": 0},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    return alerts


def get_patient_vitals_series(
    patient_id: str,
    feature: str,
    limit: int = 20,
) -> list:
    """Get time series of a vital for a patient."""
    conn = get_pg_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT value_quantity, effective_at
        FROM observations
        WHERE patient_id = %s
          AND feature_name = %s
          AND value_quantity IS NOT NULL
        ORDER BY effective_at DESC
        LIMIT %s
        """,
        (patient_id, feature, limit),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


def get_all_patient_ids() -> list:
    conn = get_pg_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients "
        "ORDER BY created_at"
    )
    ids = [str(r[0]) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return ids


def update_causal_graph_effects(
    patient_id: str,
    updated_effects: dict,
    source: str = "nlp",
) -> bool:
    """
    Update effect_sizes in causal_graphs table.
    Used by incremental DAG updater.
    """
    conn = get_pg_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE causal_graphs
            SET effect_sizes = %s
            WHERE patient_id = %s
              AND is_current = TRUE
            """,
            (
                json.dumps(updated_effects),
                patient_id,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(
            "Failed to update graph effects: %s", e
        )
        conn.rollback()
        cursor.close()
        conn.close()
        return False


def get_current_causal_effects(
    patient_id: str,
) -> dict:
    """Get current effect_sizes for a patient."""
    conn = get_pg_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT effect_sizes
        FROM causal_graphs
        WHERE patient_id = %s
          AND is_current = TRUE
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return {}
    effects = row["effect_sizes"]
    if isinstance(effects, str):
        effects = json.loads(effects)
    return effects