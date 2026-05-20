import psycopg2
import psycopg2.extras
import logging

logger = logging.getLogger("axiom.causal.db")

DB_CONFIG = {
    "host":     "localhost",
    "port":     5439,
    "dbname":   "axiom",
    "user":     "axiom_user",
    "password": "axiom_secret",
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def fetch_patient_observations(
    patient_id: str,
    limit: int = 200,
) -> list:
    """
    Fetch all observations for a patient
    as a list of dicts sorted by time.
    """
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT
            o.feature_name,
            o.value_quantity,
            o.unit,
            o.is_abnormal,
            o.effective_at,
            p.date_of_birth,
            p.gender
        FROM observations o
        JOIN patients p
            ON o.patient_id = p.patient_id
        WHERE o.patient_id = %s
          AND o.value_quantity IS NOT NULL
          AND o.feature_name IS NOT NULL
          AND o.feature_name != ''
        ORDER BY o.effective_at DESC
        LIMIT %s
        """,
        (patient_id, limit),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


def fetch_patient_info(patient_id: str) -> dict:
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT patient_id, fhir_id, first_name,
               last_name, date_of_birth, gender
        FROM patients
        WHERE patient_id = %s
        """,
        (patient_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else {}


def fetch_all_patient_ids() -> list:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients "
        "ORDER BY created_at"
    )
    ids = [str(row[0]) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return ids


def save_causal_graph(
    patient_id: str,
    adjacency_json: list,
    effect_sizes: dict,
    node_list: list,
    samples_used: int,
    build_time_ms: float,
):
    conn = get_conn()
    cursor = conn.cursor()
    import json

    # Mark old graphs as not current
    cursor.execute(
        """
        UPDATE causal_graphs
        SET is_current = FALSE
        WHERE patient_id = %s
        """,
        (patient_id,),
    )

    cursor.execute(
        """
        INSERT INTO causal_graphs (
            patient_id, adjacency_json,
            effect_sizes, node_list,
            samples_used, build_time_ms,
            is_current
        ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """,
        (
            patient_id,
            json.dumps(adjacency_json),
            json.dumps(effect_sizes),
            json.dumps(node_list),
            samples_used,
            build_time_ms,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()


def load_causal_graph(patient_id: str) -> dict:
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT * FROM causal_graphs
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
    return dict(row) if row else {}