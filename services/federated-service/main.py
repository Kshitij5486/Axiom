"""
Axiom Federated Learning Service
Port 8085

Orchestrates federated learning across simulated
hospital nodes with Byzantine fault tolerance.
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.federated")

app = FastAPI(
    title="Axiom Federated Learning Service",
    description=(
        "Federated learning across hospital nodes "
        "with Byzantine fault tolerance and "
        "differential privacy."
    ),
    version="0.4.0",
)

_start_time = time.time()
_rounds_completed = 0
_total_nodes = 3
_node_ids = ["hospital-1", "hospital-2", "hospital-3"]


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-federated",
        "version": "0.4.0",
        "rounds_completed": _rounds_completed,
        "registered_nodes": _node_ids,
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/federated/nodes")
def list_nodes():
    """List all registered hospital nodes."""
    return {
        "nodes": _node_ids,
        "total": len(_node_ids),
        "min_consensus": 2,
        "consensus_threshold": "2/3",
    }


@app.get("/federated/status")
def federation_status():
    """Current federation status."""
    return {
        "rounds_completed": _rounds_completed,
        "nodes_registered": len(_node_ids),
        "consensus_threshold": "2/3",
        "differential_privacy": True,
        "byzantine_protection": True,
        "aggregation_algorithm": "Bulyan",
        "dp_noise": "Gaussian",
    }



    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)

# Global hospital nodes
_hospital_nodes = {}


@app.on_event("startup")
async def startup():
    from hospital_node import HospitalNode
    global _hospital_nodes
    for node_id in _node_ids:
        node = HospitalNode(
            node_id=node_id,
            total_nodes=_total_nodes,
        )
        node.load_patients()
        _hospital_nodes[node_id] = node
    logger.info(
        "All hospital nodes initialized: %d nodes",
        len(_hospital_nodes),
    )


@app.get("/federated/nodes/{node_id}")
def get_node_status(node_id: str):
    """Get status of a specific hospital node."""
    if node_id not in _hospital_nodes:
        return {"error": f"Node {node_id} not found"}
    return _hospital_nodes[node_id].status()


@app.post("/federated/nodes/{node_id}/train")
def train_node(node_id: str):
    """
    Trigger local training on a hospital node.
    Returns DP-noised gradients.
    """
    if node_id not in _hospital_nodes:
        return {"error": f"Node {node_id} not found"}
    node = _hospital_nodes[node_id]
    gradients = node.get_gradients()
    return {
        "node_id": node_id,
        "gradients": gradients,
        "n_patients": node.n_patients,
        "training_round": node.training_rounds,
        "loss": node.last_loss,
        "dp_applied": True,
        "noise_multiplier": node.noise_multiplier,
    }


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)

# Global Byzantine aggregator
_aggregator = None


@app.on_event("startup")
async def init_aggregator():
    from byzantine_aggregator import ByzantineAggregator
    global _aggregator
    _aggregator = ByzantineAggregator(
        max_byzantine=1,
        min_nodes=2,
    )
    logger.info("Byzantine aggregator initialized")


@app.post("/federated/aggregate")
def aggregate_gradients():
    """
    Collect gradients from all nodes and run
    Byzantine-fault-tolerant aggregation.
    Returns aggregated global gradient + rejected nodes.
    """
    if _aggregator is None:
        return {"error": "Aggregator not initialized"}

    # Collect gradients from all nodes
    node_gradients = {}
    for node_id, node in _hospital_nodes.items():
        grads = node.get_gradients()
        if grads:
            node_gradients[node_id] = grads

    if not node_gradients:
        return {"error": "No gradients collected"}

    result = _aggregator.aggregate(node_gradients)
    return result


@app.post("/federated/aggregate/with-attack")
def aggregate_with_byzantine_attack():
    """
    Test Byzantine detection by injecting an attack
    from hospital-3 (sign-flip attack).
    Bulyan should detect and reject hospital-3.
    """
    if _aggregator is None:
        return {"error": "Aggregator not initialized"}

    from byzantine_aggregator import ByzantineAggregator

    node_gradients = {}
    for node_id, node in _hospital_nodes.items():
        grads = node.get_gradients()
        if grads:
            if node_id == "hospital-3":
                # Inject Byzantine attack
                grads = _aggregator.simulate_byzantine_attack(
                    grads, attack_type="sign_flip"
                )
                logger.warning(
                    "Byzantine attack injected on %s",
                    node_id,
                )
            node_gradients[node_id] = grads

    result = _aggregator.aggregate(node_gradients)
    result["attack_injected_on"] = "hospital-3"
    result["attack_type"] = "sign_flip"
    return result


@app.get("/federated/aggregator/status")
def aggregator_status():
    if _aggregator is None:
        return {"error": "Aggregator not initialized"}
    return _aggregator.status()


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)

# Global coordinator
_coordinator = None


@app.on_event("startup")
async def init_coordinator():
    from federated_coordinator import FederatedCoordinator
    global _coordinator
    _coordinator = FederatedCoordinator(
        node_ids=_node_ids,
        max_byzantine=1,
        min_consensus=2,
        global_lr=0.1,
    )
    logger.info("Federated coordinator initialized")


@app.post("/federated/round")
def run_federation_round():
    """
    Execute one complete federation round.
    Collects gradients, runs Bulyan aggregation,
    updates global model, stores in PostgreSQL.
    """
    if _coordinator is None or not _hospital_nodes:
        return {"error": "Not initialized"}

    result = _coordinator.run_round(
        hospital_nodes=_hospital_nodes,
    )
    return result


@app.post("/federated/round/with-attack")
def run_round_with_attack():
    """
    Run a federation round with Byzantine attack
    injected on hospital-3. Tests that Bulyan
    detects and excludes the compromised node.
    """
    if _coordinator is None or not _hospital_nodes:
        return {"error": "Not initialized"}

    result = _coordinator.run_round(
        hospital_nodes=_hospital_nodes,
        inject_attack_on="hospital-3",
    )
    result["attack_injected_on"] = "hospital-3"
    return result


@app.get("/federated/coordinator/status")
def coordinator_status():
    """Global model weights + round history."""
    if _coordinator is None:
        return {"error": "Not initialized"}
    return _coordinator.status()


@app.get("/federated/weights")
def get_global_weights():
    """Current global model weights."""
    if _coordinator is None:
        return {"error": "Not initialized"}
    return {
        "global_weights": _coordinator.get_global_weights(),
        "round_number": _coordinator.round_number,
    }


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)

# Global reputation scorer
_reputation = None


@app.on_event("startup")
async def init_reputation():
    from reputation_scorer import ReputationScorer
    global _reputation
    _reputation = ReputationScorer(
        node_ids=_node_ids
    )
    logger.info("Reputation scorer initialized")


@app.get("/federated/reputation")
def get_reputation():
    """Current reputation scores for all nodes."""
    if _reputation is None:
        return {"error": "Not initialized"}
    return _reputation.status()


@app.post("/federated/round/reputation")
def run_round_with_reputation():
    """
    Run a full federation round with reputation scoring.
    Reputation scores feed into Byzantine aggregation
    to weight nodes by their historical trustworthiness.
    """
    if _coordinator is None or not _hospital_nodes:
        return {"error": "Not initialized"}
    if _reputation is None:
        return {"error": "Reputation scorer not initialized"}

    # Use current reputation scores in aggregation
    scores = _reputation.get_scores()

    result = _coordinator.run_round(
        hospital_nodes=_hospital_nodes,
        reputation_scores=scores,
    )

    # Update reputation based on round result
    updated_scores = _reputation.update(
        accepted_nodes=result["accepted_nodes"],
        rejected_nodes=result["rejected_nodes"],
        participating_nodes=result["participating_nodes"],
    )

    result["reputation_scores"] = updated_scores
    result["excluded_nodes"] = _reputation.excluded_nodes
    result["active_nodes"] = _reputation.get_active_nodes()
    return result


@app.post("/federated/round/reputation/with-attack")
def run_round_reputation_with_attack():
    """
    Run reputation round with Byzantine attack on hospital-3.
    After enough rounds, hospital-3 should be auto-excluded.
    """
    if _coordinator is None or not _hospital_nodes:
        return {"error": "Not initialized"}

    scores = _reputation.get_scores()

    result = _coordinator.run_round(
        hospital_nodes=_hospital_nodes,
        reputation_scores=scores,
        inject_attack_on="hospital-3",
    )

    updated_scores = _reputation.update(
        accepted_nodes=result["accepted_nodes"],
        rejected_nodes=result["rejected_nodes"],
        participating_nodes=result["participating_nodes"],
    )

    result["reputation_scores"] = updated_scores
    result["excluded_nodes"] = list(
        _reputation.excluded_nodes
    )
    result["active_nodes"] = _reputation.get_active_nodes()
    result["attack_injected_on"] = "hospital-3"
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)