"""
Federated Service — PostgreSQL client.
Stores global model weights and federation round history.
"""

import json
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

logger = logging.getLogger("axiom.federated.db")

DB_CONFIG = {
    "host":     "localhost",
    "port":     5439,
    "dbname":   "axiom",
    "user":     "axiom_user",
    "password": "axiom_secret",
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def save_federation_round(
    round_number: int,
    participating_nodes: list,
    accepted_nodes: list,
    rejected_nodes: list,
    global_weights: dict,
    consensus_reached: bool,
    reputation_scores: dict,
) -> str:
    """Save a completed federation round to audit_log."""
    conn = get_conn()
    cursor = conn.cursor()
    import uuid
    round_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    cursor.execute(
        """
        INSERT INTO audit_log (
            audit_id, event_type,
            entity_type, entity_id,
            actor_id, actor_role,
            details_json, occurred_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(uuid.uuid4()),
            "federated.round.completed",
            "federation_round",
            round_id,
            "federated-coordinator",
            "ai_system",
            json.dumps({
                "round_number": round_number,
                "participating_nodes": participating_nodes,
                "accepted_nodes": accepted_nodes,
                "rejected_nodes": rejected_nodes,
                "consensus_reached": consensus_reached,
                "reputation_scores": reputation_scores,
                "weight_keys": list(
                    global_weights.keys()
                ),
            }),
            now,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()
    logger.info(
        "Round %d saved: accepted=%d rejected=%d",
        round_number,
        len(accepted_nodes),
        len(rejected_nodes),
    )
    return round_id


def get_patient_partition(
    node_id: str,
    total_nodes: int = 3,
) -> list:
    """
    Get patient IDs for a specific hospital node.
    Partitions the 50 patients across nodes.
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients ORDER BY created_at"
    )
    all_patients = [str(row[0]) for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    node_index = int(node_id.split("-")[-1]) - 1
    partition = []
    for i, pid in enumerate(all_patients):
        if i % total_nodes == node_index:
            partition.append(pid)
    return partition


def get_patient_observations_flat(
    patient_ids: list,
) -> list:
    """Get observations for a list of patients."""
    if not patient_ids:
        return []
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    placeholders = ",".join(["%s"] * len(patient_ids))
    cursor.execute(
        f"""
        SELECT patient_id, feature_name, value_quantity
        FROM observations
        WHERE patient_id IN ({placeholders})
          AND value_quantity IS NOT NULL
          AND feature_name IS NOT NULL
          AND feature_name != ''
        ORDER BY patient_id, feature_name
        """,
        patient_ids,
    )
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows