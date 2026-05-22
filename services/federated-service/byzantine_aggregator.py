"""
Byzantine Aggregator — Bulyan Algorithm

Bulyan is a Byzantine-fault-tolerant gradient aggregation
algorithm. Given n gradient vectors from n hospital nodes,
it detects and excludes corrupted nodes.

Algorithm:
  1. Compute pairwise L2 distances between all gradient vectors
  2. For each node, sum its distances to all other nodes
  3. Sort nodes by total distance (ascending)
  4. Select the n - 2f closest nodes (f = max Byzantine nodes)
  5. From selected nodes, trim the highest and lowest values
     per dimension, average the rest
  6. Return: clean aggregated gradient + rejected node list

With n=3 hospitals and f=1 Byzantine node:
  n - 2f = 3 - 2 = 1 minimum nodes needed
  We require at least 2 nodes to agree (2/3 consensus)

Reference: El Mhamdi et al. 2018
  "The Hidden Vulnerability of Distributed Learning in Byzantium"
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("axiom.federated.byzantine")

# With 3 nodes, tolerate 1 Byzantine node
MAX_BYZANTINE = 1
MIN_NODES = 2  # 2/3 consensus


class ByzantineAggregator:
    """
    Bulyan Byzantine-fault-tolerant aggregator.

    Detects corrupted hospital nodes by analyzing
    gradient vectors and excludes outliers before
    aggregating the global model update.
    """

    def __init__(
        self,
        max_byzantine: int = MAX_BYZANTINE,
        min_nodes: int = MIN_NODES,
    ):
        self.max_byzantine = max_byzantine
        self.min_nodes = min_nodes
        self.rounds_completed = 0
        self.total_rejected = 0

    def aggregate(
        self,
        node_gradients: dict,
        reputation_scores: Optional[dict] = None,
    ) -> dict:
        """
        Main aggregation entry point.

        Args:
            node_gradients: {node_id: {key: gradient_value}}
            reputation_scores: {node_id: float 0.0-1.0}

        Returns:
            {
                "aggregated_gradients": {key: value},
                "accepted_nodes": [node_id, ...],
                "rejected_nodes": [node_id, ...],
                "consensus_reached": bool,
                "method": "bulyan",
                "n_nodes": int,
            }
        """
        node_ids = list(node_gradients.keys())
        n = len(node_ids)

        if n < self.min_nodes:
            logger.warning(
                "Insufficient nodes for aggregation: "
                "%d < %d", n, self.min_nodes
            )
            return {
                "aggregated_gradients": {},
                "accepted_nodes": [],
                "rejected_nodes": node_ids,
                "consensus_reached": False,
                "method": "bulyan",
                "n_nodes": n,
                "error": "insufficient_nodes",
            }

        # Get gradient keys from first node
        grad_keys = list(
            next(iter(node_gradients.values())).keys()
        )

        # Build gradient matrix: rows=nodes, cols=features
        grad_matrix = np.zeros((n, len(grad_keys)))
        for i, node_id in enumerate(node_ids):
            for j, key in enumerate(grad_keys):
                grad_matrix[i, j] = node_gradients[
                    node_id
                ].get(key, 0.0)

        # Step 1: Pairwise L2 distances
        distances = self._pairwise_l2(grad_matrix)

        # Step 2: Sum of distances per node
        distance_sums = distances.sum(axis=1)

        # Step 3: Sort by distance sum (ascending)
        sorted_indices = np.argsort(distance_sums)

        # Step 4: Select n - 2f closest nodes
        # With reputation, down-weight suspicious nodes
        n_select = max(
            self.min_nodes,
            n - 2 * self.max_byzantine,
        )
        n_select = min(n_select, n)

        if reputation_scores:
            # Re-rank by distance + (1 - reputation)
            combined_scores = []
            for i, node_id in enumerate(node_ids):
                rep = reputation_scores.get(node_id, 1.0)
                score = distance_sums[i] + (1.0 - rep) * 10
                combined_scores.append(score)
            sorted_indices = np.argsort(combined_scores)

        selected_indices = sorted_indices[:n_select]
        rejected_indices = sorted_indices[n_select:]

        accepted_nodes = [
            node_ids[i] for i in selected_indices
        ]
        rejected_nodes = [
            node_ids[i] for i in rejected_indices
        ]

        if len(accepted_nodes) < self.min_nodes:
            logger.warning(
                "Byzantine detection rejected too many "
                "nodes: accepted=%d min=%d",
                len(accepted_nodes), self.min_nodes,
            )
            # Fall back to accepting all
            accepted_nodes = node_ids
            rejected_nodes = []

        # Step 5: Bulyan trimmed mean on selected nodes
        selected_matrix = grad_matrix[selected_indices]
        aggregated = self._bulyan_trim(selected_matrix)

        aggregated_gradients = {
            grad_keys[j]: float(aggregated[j])
            for j in range(len(grad_keys))
        }

        consensus_reached = (
            len(accepted_nodes) >= self.min_nodes
        )

        self.rounds_completed += 1
        self.total_rejected += len(rejected_nodes)

        # Log distance analysis
        for i, node_id in enumerate(node_ids):
            status = (
                "ACCEPTED" if node_id in accepted_nodes
                else "REJECTED"
            )
            logger.info(
                "Node %s: distance_sum=%.4f status=%s",
                node_id,
                float(distance_sums[i]),
                status,
            )

        if rejected_nodes:
            logger.warning(
                "Byzantine nodes detected: %s",
                rejected_nodes,
            )

        logger.info(
            "Aggregation complete: accepted=%d "
            "rejected=%d consensus=%s",
            len(accepted_nodes),
            len(rejected_nodes),
            consensus_reached,
        )

        return {
            "aggregated_gradients": aggregated_gradients,
            "accepted_nodes": accepted_nodes,
            "rejected_nodes": rejected_nodes,
            "consensus_reached": consensus_reached,
            "method": "bulyan",
            "n_nodes": n,
            "n_selected": len(accepted_nodes),
            "distance_sums": {
                node_ids[i]: round(
                    float(distance_sums[i]), 4
                )
                for i in range(n)
            },
        }

    def _pairwise_l2(
        self, matrix: np.ndarray
    ) -> np.ndarray:
        """
        Compute pairwise L2 distances between rows.
        Returns n x n distance matrix.
        """
        n = matrix.shape[0]
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i, j] = np.linalg.norm(
                        matrix[i] - matrix[j]
                    )
        return distances

    def _bulyan_trim(
        self, matrix: np.ndarray
    ) -> np.ndarray:
        """
        Bulyan coordinate-wise trimmed mean.

        For each gradient dimension:
          - Sort values across selected nodes
          - Remove max_byzantine highest + lowest values
          - Average the remaining values

        This prevents a single Byzantine node from
        pulling the aggregated gradient in any direction.
        """
        n, d = matrix.shape
        trim = min(self.max_byzantine, n // 2 - 1)
        trim = max(0, trim)

        result = np.zeros(d)
        for j in range(d):
            col = np.sort(matrix[:, j])
            if trim > 0 and n > 2 * trim:
                trimmed = col[trim:-trim]
            else:
                trimmed = col
            result[j] = trimmed.mean()

        return result

    def simulate_byzantine_attack(
        self,
        honest_gradients: dict,
        attack_type: str = "sign_flip",
    ) -> dict:
        """
        Simulate a Byzantine attack on honest gradients.
        Used for testing that Bulyan detects the attack.

        attack_type:
          sign_flip: multiply all gradients by -10
          random:    replace with random large values
          zero:      send all zeros
        """
        if attack_type == "sign_flip":
            return {
                k: v * -10.0
                for k, v in honest_gradients.items()
            }
        elif attack_type == "random":
            return {
                k: float(np.random.uniform(-100, 100))
                for k in honest_gradients.keys()
            }
        elif attack_type == "zero":
            return {k: 0.0 for k in honest_gradients}
        else:
            return honest_gradients

    def status(self) -> dict:
        return {
            "max_byzantine": self.max_byzantine,
            "min_nodes": self.min_nodes,
            "rounds_completed": self.rounds_completed,
            "total_rejected": self.total_rejected,
            "algorithm": "bulyan",
        }