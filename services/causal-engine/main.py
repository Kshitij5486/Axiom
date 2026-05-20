import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.causal")

app = FastAPI(
    title="Axiom Causal Engine",
    description=(
        "Per-patient causal graph inference engine. "
        "Builds individual causal DAGs using DoWhy "
        "and answers counterfactual clinical queries."
    ),
    version="0.2.0",
)

_start_time = time.time()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-causal-engine",
        "version": "0.2.0",
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/causal/graph/{patient_id}")
def get_causal_graph(patient_id: str):
    """
    Get the current causal graph for a patient.
    Returns adjacency list + effect sizes.
    """
    from db import load_causal_graph
    graph = load_causal_graph(patient_id)
    if not graph:
        raise HTTPException(
            status_code=404,
            detail=f"No causal graph found for "
                   f"patient {patient_id}. "
                   f"Run /causal/build/{patient_id} first.",
        )
    return graph


@app.post("/causal/build/{patient_id}")
def build_causal_graph(patient_id: str):
    """
    Build or rebuild the causal graph for a patient.
    Uses their observation history from PostgreSQL.
    """
    from causal_graph_builder import PatientCausalGraphBuilder
    builder = PatientCausalGraphBuilder()
    result = builder.build_causal_graph(patient_id)
    return result


@app.post("/causal/build-all")
def build_all_graphs():
    """
    Build causal graphs for all patients.
    Returns summary of results.
    """
    from db import fetch_all_patient_ids
    from causal_graph_builder import PatientCausalGraphBuilder

    patient_ids = fetch_all_patient_ids()
    builder = PatientCausalGraphBuilder()

    built = 0
    failed = 0
    empty = 0

    for patient_id in patient_ids:
        try:
            result = builder.build_causal_graph(
                patient_id
            )
            if result.get("empty"):
                empty += 1
            else:
                built += 1
        except Exception as e:
            failed += 1
            logger.error(
                "Build failed for %s: %s",
                patient_id, e,
            )

    return {
        "total_patients": len(patient_ids),
        "graphs_built": built,
        "empty_graphs": empty,
        "failed": failed,
    }


@app.get("/causal/patients")
def list_patients_with_graphs():
    """List all patients that have causal graphs."""
    from db import get_conn
    import psycopg2.extras
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT
            p.patient_id,
            p.first_name,
            p.last_name,
            cg.edge_count,
            cg.created_at as graph_built_at
        FROM patients p
        LEFT JOIN (
            SELECT DISTINCT ON (patient_id)
                patient_id,
                jsonb_array_length(adjacency_json)
                    as edge_count,
                created_at
            FROM causal_graphs
            WHERE is_current = TRUE
            ORDER BY patient_id, created_at DESC
        ) cg ON p.patient_id = cg.patient_id
        ORDER BY p.created_at
        LIMIT 50
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return {"patients": rows, "total": len(rows)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)