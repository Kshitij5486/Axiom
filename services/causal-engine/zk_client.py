"""
ZK Service Client

Called by the causal engine after every graph build
to generate a cryptographic integrity proof.
The proof hash is stored alongside the graph.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("axiom.causal.zk")

ZK_SERVICE_URL = "http://localhost:8084"
TIMEOUT = 10


def generate_graph_proof(
    graph_id: str,
    patient_id: str,
    edges: list,
    effect_sizes: dict,
    built_at: str,
) -> Optional[str]:
    """
    Call ZK service to generate integrity proof
    for a causal graph.
    Returns integrity_proof hash or None on failure.
    """
    try:
        response = requests.post(
            f"{ZK_SERVICE_URL}/zk/proof/graph",
            json={
                "graph_id": graph_id,
                "patient_id": patient_id,
                "edges": edges,
                "effect_sizes": effect_sizes,
                "built_at": built_at,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        proof = response.json()
        integrity_proof = proof.get(
            "integrity_proof"
        )
        logger.info(
            "Graph proof generated: graph=%s "
            "proof=%s",
            graph_id[:8],
            integrity_proof[:12] if integrity_proof
            else "None",
        )
        return integrity_proof
    except Exception as e:
        logger.warning(
            "ZK proof generation failed "
            "(ZK service may be offline): %s", e
        )
        return None


def generate_recommendation_proof(
    patient_id: str,
    recommendation: str,
    causal_effect: float,
    graph_id: str,
    treatment: str,
    outcome: str,
) -> Optional[str]:
    """
    Generate ZK proof for a recommendation.
    Returns proof_hash or None on failure.
    """
    try:
        response = requests.post(
            f"{ZK_SERVICE_URL}/zk/proof/recommendation",
            json={
                "patient_id": patient_id,
                "recommendation": recommendation,
                "causal_effect": causal_effect,
                "graph_id": graph_id,
                "treatment": treatment,
                "outcome": outcome,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        proof = response.json()
        return proof.get("proof_hash")
    except Exception as e:
        logger.warning(
            "Recommendation proof failed: %s", e
        )
        return None