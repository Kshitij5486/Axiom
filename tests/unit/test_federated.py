"""
Sprint 4 Unit Tests — Federated Learning Layer

Tests for:
  HospitalNode
  ByzantineAggregator
  ReputationScorer
  FederatedClient (blend_with_federated)
"""

import sys
import os
import json
import pytest
import numpy as np
from unittest.mock import patch, MagicMock



# ── ByzantineAggregator ────────────────────────────

class TestByzantineAggregator:

    def _make_gradients(
        self, n_nodes=3, scale=1.0, seed=42
    ):
        np.random.seed(seed)
        keys = [
            "glucose->creatinine",
            "systolic_bp->creatinine",
            "heart_rate->spo2",
        ]
        result = {}
        for i in range(n_nodes):
            node_id = f"hospital-{i+1}"
            result[node_id] = {
                k: float(
                    np.random.normal(0, scale)
                )
                for k in keys
            }
        return result

    def test_aggregate_honest_nodes(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator(
            max_byzantine=1, min_nodes=2
        )
        grads = self._make_gradients(n_nodes=3)
        result = agg.aggregate(grads)
        assert result["consensus_reached"] is True
        assert len(result["accepted_nodes"]) >= 2
        assert "aggregated_gradients" in result
        assert len(result["aggregated_gradients"]) == 3

    def test_byzantine_attack_detected(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator(
            max_byzantine=1, min_nodes=2
        )
        grads = self._make_gradients(n_nodes=3)

        # Inject sign_flip attack on hospital-3
        attacked = agg.simulate_byzantine_attack(
            grads["hospital-3"],
            attack_type="sign_flip",
        )
        grads["hospital-3"] = attacked

        result = agg.aggregate(grads)
        assert result["consensus_reached"] is True
        assert "hospital-3" in result["rejected_nodes"]
        assert "hospital-3" not in result["accepted_nodes"]

    def test_insufficient_nodes(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator(
            max_byzantine=1, min_nodes=2
        )
        grads = self._make_gradients(n_nodes=1)
        result = agg.aggregate(grads)
        assert result["consensus_reached"] is False
        assert "error" in result

    def test_aggregated_gradients_within_range(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator(
            max_byzantine=1, min_nodes=2
        )
        grads = self._make_gradients(n_nodes=3, scale=0.1)
        result = agg.aggregate(grads)
        for key, val in result[
            "aggregated_gradients"
        ].items():
            assert abs(val) < 10.0

    def test_simulate_sign_flip(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator()
        grads = {"a->b": 1.0, "c->d": 2.0}
        attacked = agg.simulate_byzantine_attack(
            grads, "sign_flip"
        )
        assert attacked["a->b"] == -10.0
        assert attacked["c->d"] == -20.0

    def test_simulate_zero_attack(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator()
        grads = {"a->b": 1.0, "c->d": 2.0}
        attacked = agg.simulate_byzantine_attack(
            grads, "zero"
        )
        assert all(v == 0.0 for v in attacked.values())

    def test_distance_sums_in_result(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator(
            max_byzantine=1, min_nodes=2
        )
        grads = self._make_gradients(n_nodes=3)
        result = agg.aggregate(grads)
        assert "distance_sums" in result
        assert len(result["distance_sums"]) == 3

    def test_bulyan_trim_single_row(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator(max_byzantine=0)
        matrix = np.array([[1.0, 2.0, 3.0]])
        result = agg._bulyan_trim(matrix)
        assert result.shape == (3,)

    def test_pairwise_l2_diagonal_zero(self):
        from byzantine_aggregator import ByzantineAggregator
        agg = ByzantineAggregator()
        matrix = np.array([
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ])
        distances = agg._pairwise_l2(matrix)
        assert distances[0, 0] == 0.0
        assert distances[1, 1] == 0.0
        assert distances[2, 2] == 0.0


# ── ReputationScorer ───────────────────────────────

class TestReputationScorer:

    def test_initial_scores(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(
            ["hospital-1", "hospital-2", "hospital-3"]
        )
        scores = scorer.get_scores()
        assert scores["hospital-1"] == 0.7
        assert scores["hospital-2"] == 0.7
        assert scores["hospital-3"] == 0.7

    def test_accepted_node_score_increases(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1", "h2"])
        initial = scorer.scores["h1"]
        scorer.update(
            accepted_nodes=["h1"],
            rejected_nodes=[],
            participating_nodes=["h1", "h2"],
        )
        assert scorer.scores["h1"] > initial

    def test_rejected_node_score_decreases(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1", "h2"])
        initial = scorer.scores["h1"]
        scorer.update(
            accepted_nodes=["h2"],
            rejected_nodes=["h1"],
            participating_nodes=["h1", "h2"],
        )
        assert scorer.scores["h1"] < initial

    def test_exclusion_after_repeated_rejections(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1", "h2", "h3"])
        for _ in range(10):
            scorer.update(
                accepted_nodes=["h1", "h2"],
                rejected_nodes=["h3"],
                participating_nodes=["h1", "h2", "h3"],
            )
        assert "h3" in scorer.excluded_nodes
        assert "h3" not in scorer.get_active_nodes()

    def test_honest_node_never_excluded(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1", "h2", "h3"])
        for _ in range(10):
            scorer.update(
                accepted_nodes=["h1", "h2", "h3"],
                rejected_nodes=[],
                participating_nodes=["h1", "h2", "h3"],
            )
        assert "h1" not in scorer.excluded_nodes
        assert "h2" not in scorer.excluded_nodes
        assert "h3" not in scorer.excluded_nodes

    def test_score_bounded_0_to_1(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1"])
        for _ in range(50):
            scorer.update(
                accepted_nodes=["h1"],
                rejected_nodes=[],
                participating_nodes=["h1"],
            )
        assert scorer.scores["h1"] <= 1.0
        assert scorer.scores["h1"] >= 0.0

    def test_readmit_excluded_node(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1", "h2", "h3"])
        for _ in range(10):
            scorer.update(
                accepted_nodes=["h1", "h2"],
                rejected_nodes=["h3"],
                participating_nodes=["h1", "h2", "h3"],
            )
        assert "h3" in scorer.excluded_nodes
        scorer.readmit("h3")
        assert "h3" not in scorer.excluded_nodes

    def test_history_tracked(self):
        from reputation_scorer import ReputationScorer
        scorer = ReputationScorer(["h1", "h2"])
        scorer.update(
            accepted_nodes=["h1"],
            rejected_nodes=["h2"],
            participating_nodes=["h1", "h2"],
        )
        assert len(scorer.history["h1"]) == 1
        assert scorer.history["h1"][0]["status"] == "accepted"
        assert scorer.history["h2"][0]["status"] == "rejected"


# ── FederatedClient (blend_with_federated) ─────────

class TestFederatedClient:

    def test_blend_full_local_at_n20(self):
        from federated_client import blend_with_federated
        local = {
            "glucose->creatinine": {
                "effect": 0.0002,
                "samples": 20,
            }
        }
        federated = {"glucose->creatinine": 0.5}
        result = blend_with_federated(
            local, n_observations=20,
            federated_weights=federated,
        )
        # alpha=1.0 at n=20, pure local
        assert result["glucose->creatinine"][
            "effect"
        ] == pytest.approx(0.0002, abs=0.001)

    def test_blend_half_at_n10(self):
        from federated_client import blend_with_federated
        local = {
            "glucose->creatinine": {
                "effect": 0.0,
                "samples": 10,
            }
        }
        federated = {"glucose->creatinine": 1.0}
        result = blend_with_federated(
            local, n_observations=10,
            federated_weights=federated,
        )
        # alpha=0.5, blend = 0.5*0.0 + 0.5*1.0 = 0.5
        effect = result["glucose->creatinine"]["effect"]
        assert effect == pytest.approx(0.5, abs=0.01)

    def test_cold_start_pure_federated(self):
        from federated_client import blend_with_federated
        local = {}
        federated = {"glucose->creatinine": 0.42}
        result = blend_with_federated(
            local, n_observations=0,
            federated_weights=federated,
        )
        assert "glucose->creatinine" in result
        assert result["glucose->creatinine"][
            "cold_start"
        ] is True
        assert result["glucose->creatinine"][
            "effect"
        ] == pytest.approx(0.42, abs=0.001)

    def test_no_federated_returns_local(self):
        from federated_client import blend_with_federated
        local = {"a->b": {"effect": 0.5, "samples": 20}}
        result = blend_with_federated(
            local, n_observations=20,
            federated_weights=None,
        )
        assert result == local

    def test_blend_metadata_present(self):
        from federated_client import blend_with_federated
        local = {
            "glucose->creatinine": {
                "effect": 0.1,
                "samples": 10,
            }
        }
        federated = {"glucose->creatinine": 0.5}
        result = blend_with_federated(
            local, n_observations=10,
            federated_weights=federated,
        )
        entry = result["glucose->creatinine"]
        assert "federated_prior" in entry
        assert "local_weight" in entry
        assert "federated_weight" in entry
        assert entry["blended"] is True

    def test_get_global_weights_returns_none_on_failure(self):
        from federated_client import get_global_weights
        with patch(
            "requests.get",
            side_effect=Exception("Connection refused")
        ):
            result = get_global_weights()
        assert result is None