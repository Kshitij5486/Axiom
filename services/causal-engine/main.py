import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.causal")

app = FastAPI(
    title="Axiom Causal Engine",
    version="0.2.0",
)

_start_time = time.time()


class CounterfactualRequest(BaseModel):
    treatment: str
    outcome: str
    intervention_value: Optional[float] = None
    use_stored_graph: bool = True


class CompareRequest(BaseModel):
    treatments: list
    outcome: str


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
    from db import load_causal_graph
    import json
    graph = load_causal_graph(patient_id)
    if not graph:
        raise HTTPException(
            status_code=404,
            detail=f"No causal graph found for "
                   f"patient {patient_id}.",
        )
    # Parse JSON fields
    for field in [
        "adjacency_json", "effect_sizes", "node_list"
    ]:
        if field in graph and isinstance(
            graph[field], str
        ):
            graph[field] = json.loads(graph[field])
    return graph


@app.post("/causal/build/{patient_id}")
def build_causal_graph(patient_id: str):
    from causal_graph_builder import (
        PatientCausalGraphBuilder,
    )
    builder = PatientCausalGraphBuilder()
    return builder.build_causal_graph(patient_id)


@app.post("/causal/build-all")
def build_all_graphs():
    from db import fetch_all_patient_ids
    from causal_graph_builder import (
        PatientCausalGraphBuilder,
    )
    patient_ids = fetch_all_patient_ids()
    builder = PatientCausalGraphBuilder()
    built = failed = empty = 0
    for pid in patient_ids:
        try:
            r = builder.build_causal_graph(pid)
            if r.get("empty"):
                empty += 1
            else:
                built += 1
        except Exception as e:
            failed += 1
            logger.error("Build failed %s: %s", pid, e)
    return {
        "total_patients": len(patient_ids),
        "graphs_built": built,
        "empty_graphs": empty,
        "failed": failed,
    }


@app.post("/causal/counterfactual/{patient_id}")
def counterfactual(
    patient_id: str,
    request: CounterfactualRequest,
):
    """
    Answer: what happens to outcome if treatment changes?

    Example:
      POST /causal/counterfactual/{patient_id}
      {
        "treatment": "glucose",
        "outcome": "creatinine",
        "intervention_value": -20.0
      }
    """
    from counterfactual_engine import (
        CounterfactualEngine,
    )
    engine = CounterfactualEngine()

    if request.use_stored_graph:
        return engine.query_from_graph(
            patient_id=patient_id,
            treatment=request.treatment,
            outcome=request.outcome,
            intervention_value=(
                request.intervention_value
            ),
        )
    else:
        return engine.query_from_data(
            patient_id=patient_id,
            treatment=request.treatment,
            outcome=request.outcome,
            intervention_value=(
                request.intervention_value
            ),
        )


@app.post("/causal/compare/{patient_id}")
def compare_interventions(
    patient_id: str,
    request: CompareRequest,
):
    """
    Compare multiple treatments for the same outcome.
    Returns ranked list by causal effect magnitude.
    """
    from counterfactual_engine import (
        CounterfactualEngine,
    )
    engine = CounterfactualEngine()
    return engine.compare_interventions(
        patient_id=patient_id,
        treatments=request.treatments,
        outcome=request.outcome,
    )


@app.get("/causal/patients")
def list_patients_with_graphs():
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
            cg.samples_used,
            cg.build_time_ms,
            cg.created_at as graph_built_at
        FROM patients p
        JOIN causal_graphs cg
            ON p.patient_id = cg.patient_id
        WHERE cg.is_current = TRUE
        ORDER BY p.created_at
        LIMIT 50
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return {"patients": rows, "total": len(rows)}



    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)

class SimulationRequest(BaseModel):
    treatment: str
    outcome: str
    intervention_value: float
    n_simulations: int = 1000


class MultiOutcomeRequest(BaseModel):
    treatment: str
    intervention_value: float
    outcomes: list = None
    n_simulations: int = 1000


@app.post("/causal/simulate/{patient_id}")
def simulate_intervention(
    patient_id: str,
    request: SimulationRequest,
):
    """
    Monte Carlo simulation of an intervention.
    Returns distribution of outcomes (1000 samples).

    Example:
      POST /causal/simulate/{patient_id}
      {
        "treatment": "glucose",
        "outcome": "creatinine",
        "intervention_value": -20.0
      }
    """
    from intervention_simulator import (
        InterventionSimulator,
    )
    simulator = InterventionSimulator()
    return simulator.simulate(
        patient_id=patient_id,
        treatment=request.treatment,
        outcome=request.outcome,
        intervention_value=request.intervention_value,
        n_simulations=request.n_simulations,
    )


@app.post("/causal/simulate-all-outcomes/{patient_id}")
def simulate_all_outcomes(
    patient_id: str,
    request: MultiOutcomeRequest,
):
    """
    Simulate one intervention across all
    causally connected outcomes.
    """
    from intervention_simulator import (
        InterventionSimulator,
    )
    simulator = InterventionSimulator()
    return simulator.simulate_multiple_outcomes(
        patient_id=patient_id,
        treatment=request.treatment,
        intervention_value=request.intervention_value,
        outcomes=request.outcomes,
        n_simulations=request.n_simulations,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)