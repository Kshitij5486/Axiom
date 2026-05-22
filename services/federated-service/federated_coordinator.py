"""
FederatedCoordinator

Orchestrates a complete federation round:
  1. Collect DP-noised gradients from all hospital nodes
  2. Run Bulyan Byzantine aggregation
  3. Apply aggregated gradients to global model
  4. Store round result in PostgreSQL audit_log
  5. Update reputation scores per node
  6. Return round summary

This is the equivalent of the Flower server strategy
but implemented directly to avoid Flower's heavyweight
client-server setup for simulation purposes.
In production, each HospitalNode would be a separate
Flower client running in its own hospital's infrastructure.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from byzantine_aggregator import ByzantineAggregator
from db import save_federation_round

logger = logging.getLogger("axiom.federated.coordinator")

# Global model learning rate for applying aggregated gradients
GLOBAL_LR = 0.1


class FederatedCoordinator:
    """
    Coordinates federation rounds across hospital nodes.

    Owns:
      - Global model weights (shared across all nodes)
      - Round history
      - Aggregation strategy
    """

    def __init__(
        self,
        node_ids: list,
        max_byzantine: int = 1,
        min_consensus: int = 2,
        global_lr: float = GLOBAL_LR,
    ):
        self.node_ids = node_ids
        self.global_lr = global_lr
        self.round_number = 0
        self.round_history = []

        # Initialize global weights to zero
        self.global_weights = {
            "glucose->creatinine":     0.0,
            "systolic_bp->creatinine": 0.0,
            "systolic_bp->heart_rate": 0.0,
            "heart_rate->spo2":        0.0,
            "creatinine->spo2":        0.0,
            "glucose->heart_rate":     0.0,
        }

        self.aggregator = ByzantineAggregator(
            max_byzantine=max_byzantine,
            min_nodes=min_consensus,
        )

        logger.info(
            "FederatedCoordinator initialized: "
            "nodes=%d global_lr=%.2f",
            len(node_ids), global_lr,
        )

    def run_round(
        self,
        hospital_nodes: dict,
        reputation_scores: Optional[dict] = None,
        inject_attack_on: Optional[str] = None,
    ) -> dict:
        """
        Execute one complete federation round.

        Args:
            hospital_nodes: {node_id: HospitalNode}
            reputation_scores: {node_id: float}
            inject_attack_on: node_id to inject attack
                              (for testing Byzantine detection)

        Returns:
            Complete round summary dict
        """
        start = time.perf_counter()
        self.round_number += 1
        round_id = self.round_number

        logger.info(
            "Federation round %d starting: %d nodes",
            round_id, len(hospital_nodes),
        )

        # Step 1: Collect gradients from all nodes
        node_gradients = {}
        node_losses = {}

        for node_id, node in hospital_nodes.items():
            grads = node.get_gradients(
                global_weights=self.global_weights
            )
            if grads:
                # Inject attack for testing
                if inject_attack_on == node_id:
                    grads = (
                        self.aggregator
                        .simulate_byzantine_attack(
                            grads,
                            attack_type="sign_flip",
                        )
                    )
                    logger.warning(
                        "Attack injected on %s", node_id
                    )

                node_gradients[node_id] = grads
                node_losses[node_id] = node.last_loss

        logger.info(
            "Round %d: collected gradients from %d nodes",
            round_id, len(node_gradients),
        )

        # Step 2: Byzantine aggregation
        agg_result = self.aggregator.aggregate(
            node_gradients,
            reputation_scores=reputation_scores,
        )

        accepted_nodes = agg_result["accepted_nodes"]
        rejected_nodes = agg_result["rejected_nodes"]
        consensus_reached = agg_result["consensus_reached"]
        aggregated_grads = agg_result["aggregated_gradients"]

        # Step 3: Update global model if consensus reached
        weights_before = dict(self.global_weights)

        if consensus_reached and aggregated_grads:
            for key, grad in aggregated_grads.items():
                if key in self.global_weights:
                    self.global_weights[key] += (
                        self.global_lr * grad
                    )

            logger.info(
                "Round %d: global weights updated",
                round_id,
            )
        else:
            logger.warning(
                "Round %d: consensus NOT reached, "
                "global weights unchanged",
                round_id,
            )

        # Step 4: Compute weight deltas
        weight_deltas = {
            k: round(
                self.global_weights[k] - weights_before[k],
                6,
            )
            for k in self.global_weights
        }

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Step 5: Store round in PostgreSQL
        try:
            save_federation_round(
                round_number=round_id,
                participating_nodes=list(
                    hospital_nodes.keys()
                ),
                accepted_nodes=accepted_nodes,
                rejected_nodes=rejected_nodes,
                global_weights=self.global_weights,
                consensus_reached=consensus_reached,
                reputation_scores=reputation_scores or {},
            )
        except Exception as e:
            logger.error(
                "Failed to save round %d: %s",
                round_id, e,
            )

        # Step 6: Build round summary
        round_summary = {
            "round_number": round_id,
            "consensus_reached": consensus_reached,
            "participating_nodes": list(
                hospital_nodes.keys()
            ),
            "accepted_nodes": accepted_nodes,
            "rejected_nodes": rejected_nodes,
            "n_accepted": len(accepted_nodes),
            "n_rejected": len(rejected_nodes),
            "aggregation_method": "bulyan",
            "global_weights": {
                k: round(v, 6)
                for k, v in self.global_weights.items()
            },
            "weight_deltas": weight_deltas,
            "node_losses": {
                k: round(v, 4) if v else None
                for k, v in node_losses.items()
            },
            "distance_sums": agg_result.get(
                "distance_sums", {}
            ),
            "elapsed_ms": round(elapsed_ms, 1),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        self.round_history.append({
            "round_number": round_id,
            "accepted": len(accepted_nodes),
            "rejected": len(rejected_nodes),
            "consensus": consensus_reached,
        })

        logger.info(
            "Round %d complete: accepted=%d rejected=%d "
            "consensus=%s elapsed=%.0fms",
            round_id,
            len(accepted_nodes),
            len(rejected_nodes),
            consensus_reached,
            elapsed_ms,
        )

        return round_summary

    def get_global_weights(self) -> dict:
        return dict(self.global_weights)

    def status(self) -> dict:
        return {
            "round_number": self.round_number,
            "global_weights": {
                k: round(v, 6)
                for k, v in self.global_weights.items()
            },
            "round_history": self.round_history,
            "aggregator": self.aggregator.status(),
        }