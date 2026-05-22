"""
Reputation Scorer

Tracks trustworthiness of each hospital node
across federation rounds.

Score 0.0 - 1.0 per node:
  1.0 = fully trusted (consistent honest gradients)
  0.5 = neutral (new node or mixed history)
  0.0 = fully untrusted (consistently Byzantine)

Score update rules:
  Node accepted by Bulyan:  score += REWARD * (1 - score)
  Node rejected by Bulyan:  score -= PENALTY * score
  Node missing from round:  score -= ABSENT_PENALTY * score

2/3 consensus enforcement:
  If a node's score drops below EXCLUSION_THRESHOLD,
  it is excluded from future rounds entirely until
  manually re-admitted by a human administrator.

This creates a self-healing federated network:
  - Honest nodes build reputation over time
  - Byzantine nodes lose reputation quickly
  - Low-reputation nodes excluded automatically
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("axiom.federated.reputation")

# Score hyperparameters
INITIAL_SCORE      = 0.7   # new nodes start trusted
REWARD             = 0.1   # accepted: score moves up
PENALTY            = 0.2   # rejected: score moves down
ABSENT_PENALTY     = 0.05  # missing from round
EXCLUSION_THRESHOLD = 0.3  # below this = excluded
MIN_ROUNDS_BEFORE_EXCLUSION = 3  # grace period


class ReputationScorer:
    """
    Tracks and updates reputation scores for
    hospital nodes across federation rounds.
    """

    def __init__(self, node_ids: list):
        self.scores = {
            node_id: INITIAL_SCORE
            for node_id in node_ids
        }
        self.round_count = {
            node_id: 0 for node_id in node_ids
        }
        self.history = {
            node_id: [] for node_id in node_ids
        }
        self.excluded_nodes = set()
        self.total_rounds = 0

        logger.info(
            "ReputationScorer initialized: %d nodes "
            "initial_score=%.1f",
            len(node_ids), INITIAL_SCORE,
        )

    def update(
        self,
        accepted_nodes: list,
        rejected_nodes: list,
        participating_nodes: list,
    ) -> dict:
        """
        Update reputation scores after a round.

        Args:
            accepted_nodes:     nodes Bulyan accepted
            rejected_nodes:     nodes Bulyan rejected
            participating_nodes: all nodes in this round

        Returns:
            Updated scores dict
        """
        self.total_rounds += 1
        all_nodes = set(self.scores.keys())
        present_nodes = set(participating_nodes)
        absent_nodes = all_nodes - present_nodes

        # Reward accepted nodes
        for node_id in accepted_nodes:
            if node_id in self.scores:
                old = self.scores[node_id]
                # Exponential moving average toward 1.0
                self.scores[node_id] = old + REWARD * (
                    1.0 - old
                )
                self.scores[node_id] = min(
                    1.0, self.scores[node_id]
                )
                self.round_count[node_id] += 1
                self.history[node_id].append({
                    "round": self.total_rounds,
                    "status": "accepted",
                    "score": round(
                        self.scores[node_id], 4
                    ),
                })
                logger.info(
                    "Node %s ACCEPTED: %.3f -> %.3f",
                    node_id, old, self.scores[node_id],
                )

        # Penalise rejected nodes
        for node_id in rejected_nodes:
            if node_id in self.scores:
                old = self.scores[node_id]
                self.scores[node_id] = old - PENALTY * old
                self.scores[node_id] = max(
                    0.0, self.scores[node_id]
                )
                self.round_count[node_id] += 1
                self.history[node_id].append({
                    "round": self.total_rounds,
                    "status": "rejected",
                    "score": round(
                        self.scores[node_id], 4
                    ),
                })
                logger.warning(
                    "Node %s REJECTED: %.3f -> %.3f",
                    node_id, old, self.scores[node_id],
                )

        # Penalise absent nodes
        for node_id in absent_nodes:
            if node_id in self.scores:
                old = self.scores[node_id]
                self.scores[node_id] = (
                    old - ABSENT_PENALTY * old
                )
                self.scores[node_id] = max(
                    0.0, self.scores[node_id]
                )
                self.history[node_id].append({
                    "round": self.total_rounds,
                    "status": "absent",
                    "score": round(
                        self.scores[node_id], 4
                    ),
                })

        # Check for exclusion
        newly_excluded = []
        for node_id, score in self.scores.items():
            if (
                node_id not in self.excluded_nodes
                and score < EXCLUSION_THRESHOLD
                and self.round_count.get(node_id, 0)
                >= MIN_ROUNDS_BEFORE_EXCLUSION
            ):
                self.excluded_nodes.add(node_id)
                newly_excluded.append(node_id)
                logger.warning(
                    "Node %s EXCLUDED: score=%.3f "
                    "below threshold=%.1f",
                    node_id, score,
                    EXCLUSION_THRESHOLD,
                )

        if newly_excluded:
            logger.warning(
                "Newly excluded nodes: %s",
                newly_excluded,
            )

        return self.get_scores()

    def get_scores(self) -> dict:
        return {
            node_id: round(score, 4)
            for node_id, score in self.scores.items()
        }

    def get_active_nodes(self) -> list:
        """Return nodes not excluded."""
        return [
            node_id for node_id in self.scores
            if node_id not in self.excluded_nodes
        ]

    def is_excluded(self, node_id: str) -> bool:
        return node_id in self.excluded_nodes

    def readmit(self, node_id: str):
        """Manually readmit an excluded node."""
        if node_id in self.excluded_nodes:
            self.excluded_nodes.remove(node_id)
            self.scores[node_id] = INITIAL_SCORE * 0.5
            logger.info(
                "Node %s readmitted: score=%.3f",
                node_id, self.scores[node_id],
            )

    def status(self) -> dict:
        return {
            "scores": self.get_scores(),
            "excluded_nodes": list(self.excluded_nodes),
            "active_nodes": self.get_active_nodes(),
            "total_rounds": self.total_rounds,
            "thresholds": {
                "exclusion": EXCLUSION_THRESHOLD,
                "reward": REWARD,
                "penalty": PENALTY,
                "initial": INITIAL_SCORE,
            },
            "history": {
                node_id: hist[-5:]
                for node_id, hist in self.history.items()
            },
        }