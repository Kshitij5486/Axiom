"""
Sprint 2 Unit Tests — Causal Engine

Tests for:
  PatientCausalGraphBuilder
  CounterfactualEngine
  InterventionSimulator
  CausalDriftDetector
"""

import sys
import os
import json
import pytest
import numpy as np
from unittest.mock import MagicMock, patch



# ── PatientCausalGraphBuilder ──────────────────────

class TestPatientCausalGraphBuilder:

    def _make_observations(
        self, n=20, feature="glucose", value=150.0
    ):
        return [
            {
                "feature_name": feat,
                "value_quantity": val + i * 0.1,
                "effective_at": f"2026-05-{i+1:02d}",
                "date_of_birth": "1960-01-01",
                "gender": "male",
            }
            for i in range(n)
            for feat, val in [
                ("glucose",      150.0),
                ("creatinine",   1.5),
                ("heart_rate",   75.0),
                ("systolic_bp",  130.0),
                ("spo2",         96.0),
            ]
        ]

    def test_prepare_dataframe_shape(self):
        from causal_graph_builder import (
            PatientCausalGraphBuilder,
        )
        builder = PatientCausalGraphBuilder()
        obs = self._make_observations()
        df = builder._prepare_dataframe(obs)
        assert not df.empty
        assert len(df) == 20
        assert "glucose" in df.columns
        assert "creatinine" in df.columns

    def test_prepare_dataframe_demographics(self):
        from causal_graph_builder import (
            PatientCausalGraphBuilder,
        )
        builder = PatientCausalGraphBuilder()
        obs = self._make_observations()
        df = builder._prepare_dataframe(obs)
        assert "age" in df.columns
        assert "gender_encoded" in df.columns
        assert df["gender_encoded"].iloc[0] == 1

    def test_prepare_dataframe_empty_on_no_data(self):
        from causal_graph_builder import (
            PatientCausalGraphBuilder,
        )
        builder = PatientCausalGraphBuilder()
        df = builder._prepare_dataframe([])
        assert df.empty

    def test_prepare_dataframe_insufficient_data(self):
        from causal_graph_builder import (
            PatientCausalGraphBuilder,
        )
        builder = PatientCausalGraphBuilder()
        obs = self._make_observations(n=2)
        df = builder._prepare_dataframe(obs)
        assert df.empty

    def test_status_initial(self):
        from causal_graph_builder import (
            PatientCausalGraphBuilder,
        )
        builder = PatientCausalGraphBuilder()
        status = builder.status()
        assert status["graphs_built"] == 0
        assert status["graphs_failed"] == 0


# ── ClinicalPriors ─────────────────────────────────

class TestClinicalPriors:

    def test_prior_edges_exist(self):
        from clinical_priors import CLINICAL_PRIOR_EDGES
        assert len(CLINICAL_PRIOR_EDGES) > 0

    def test_vital_prior_edges_exist(self):
        from clinical_priors import VITAL_PRIOR_EDGES
        assert len(VITAL_PRIOR_EDGES) > 0

    def test_outcome_nodes_exist(self):
        from clinical_priors import OUTCOME_NODES
        assert "glucose" in OUTCOME_NODES
        assert "creatinine" in OUTCOME_NODES
        assert "spo2" in OUTCOME_NODES

    def test_confounder_nodes(self):
        from clinical_priors import CONFOUNDER_NODES
        assert "age" in CONFOUNDER_NODES
        assert "gender_encoded" in CONFOUNDER_NODES

    def test_get_prior_edges_for_nodes(self):
        from clinical_priors import (
            get_prior_edges_for_nodes,
        )
        nodes = {
            "glucose", "creatinine",
            "age", "gender_encoded",
        }
        edges = get_prior_edges_for_nodes(nodes)
        assert len(edges) > 0
        for src, dst in edges:
            assert src in nodes
            assert dst in nodes

    def test_get_outcomes_in_data(self):
        from clinical_priors import get_outcomes_in_data
        available = {
            "glucose", "creatinine", "heart_rate",
            "unknown_feature",
        }
        outcomes = get_outcomes_in_data(available)
        assert "glucose" in outcomes
        assert "creatinine" in outcomes
        assert "unknown_feature" not in outcomes

    def test_vital_edges_both_directions(self):
        from clinical_priors import VITAL_PRIOR_EDGES
        for src, dst in VITAL_PRIOR_EDGES:
            assert isinstance(src, str)
            assert isinstance(dst, str)
            assert src != dst


# ── CounterfactualEngine ───────────────────────────

class TestCounterfactualEngine:

    def _make_mock_graph(self):
        return {
            "effect_sizes": json.dumps({
                "glucose->creatinine": {
                    "effect": 0.0002,
                    "treatment": "glucose",
                    "outcome": "creatinine",
                    "samples": 20,
                },
                "systolic_bp->creatinine": {
                    "effect": 0.024,
                    "treatment": "systolic_bp",
                    "outcome": "creatinine",
                    "samples": 20,
                },
                "systolic_bp->heart_rate": {
                    "effect": -0.30,
                    "treatment": "systolic_bp",
                    "outcome": "heart_rate",
                    "samples": 20,
                },
            }),
        }

    def test_query_from_graph_found(self):
        from counterfactual_engine import (
            CounterfactualEngine,
        )
        engine = CounterfactualEngine()
        with patch(
            "counterfactual_engine.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            with patch.object(
                engine, "_get_latest_value",
                return_value=3.1,
            ):
                result = engine.query_from_graph(
                    patient_id="test-patient",
                    treatment="glucose",
                    outcome="creatinine",
                    intervention_value=-20.0,
                )
        assert result["found"] is True
        assert result["effect_per_unit"] == 0.0002
        assert result["predicted_change"] == pytest.approx(
            -0.004, abs=0.001
        )

    def test_query_from_graph_not_found(self):
        from counterfactual_engine import (
            CounterfactualEngine,
        )
        engine = CounterfactualEngine()
        with patch(
            "counterfactual_engine.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            result = engine.query_from_graph(
                patient_id="test-patient",
                treatment="heart_rate",
                outcome="creatinine",
            )
        assert result["found"] is False

    def test_query_no_graph(self):
        from counterfactual_engine import (
            CounterfactualEngine,
        )
        engine = CounterfactualEngine()
        with patch(
            "counterfactual_engine.load_causal_graph",
            return_value={},
        ):
            result = engine.query_from_graph(
                patient_id="test-patient",
                treatment="glucose",
                outcome="creatinine",
            )
        assert "error" in result

    def test_compare_interventions_ranked(self):
        from counterfactual_engine import (
            CounterfactualEngine,
        )
        engine = CounterfactualEngine()
        with patch(
            "counterfactual_engine.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            result = engine.compare_interventions(
                patient_id="test-patient",
                treatments=[
                    "glucose", "systolic_bp"
                ],
                outcome="creatinine",
            )
        assert result["best_treatment"] == "systolic_bp"
        assert result["found"] == 2
        ranked = result["ranked_treatments"]
        assert ranked[0]["abs_effect"] >= (
            ranked[1]["abs_effect"]
        )

    def test_intervention_value_computation(self):
        from counterfactual_engine import (
            CounterfactualEngine,
        )
        engine = CounterfactualEngine()
        with patch(
            "counterfactual_engine.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            with patch.object(
                engine, "_get_latest_value",
                return_value=130.0,
            ):
                result = engine.query_from_graph(
                    patient_id="test-patient",
                    treatment="systolic_bp",
                    outcome="heart_rate",
                    intervention_value=-10.0,
                )
        assert result["found"] is True
        assert result["predicted_change"] == pytest.approx(
            3.0, abs=0.1
        )


# ── InterventionSimulator ──────────────────────────

class TestInterventionSimulator:

    def _make_mock_graph(self):
        return {
            "effect_sizes": json.dumps({
                "glucose->creatinine": {
                    "effect": 0.0002,
                    "treatment": "glucose",
                    "outcome": "creatinine",
                    "samples": 20,
                },
            }),
        }

    def test_simulate_returns_distribution(self):
        from intervention_simulator import (
            InterventionSimulator,
        )
        sim = InterventionSimulator()
        with patch(
            "intervention_simulator.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            with patch.object(
                sim, "_get_latest_value",
                return_value=3.1,
            ):
                result = sim.simulate(
                    patient_id="test-patient",
                    treatment="glucose",
                    outcome="creatinine",
                    intervention_value=-20.0,
                    n_simulations=100,
                )
        assert "distribution" in result
        dist = result["distribution"]
        assert "mean" in dist
        assert "std" in dist
        assert "p5" in dist
        assert "p95" in dist

    def test_simulate_scenarios(self):
        from intervention_simulator import (
            InterventionSimulator,
        )
        sim = InterventionSimulator()
        with patch(
            "intervention_simulator.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            with patch.object(
                sim, "_get_latest_value",
                return_value=3.1,
            ):
                result = sim.simulate(
                    patient_id="test-patient",
                    treatment="glucose",
                    outcome="creatinine",
                    intervention_value=-20.0,
                    n_simulations=100,
                )
        assert "scenarios" in result
        assert "best_case" in result["scenarios"]
        assert "most_likely" in result["scenarios"]
        assert "worst_case" in result["scenarios"]

    def test_simulate_confidence_interval(self):
        from intervention_simulator import (
            InterventionSimulator,
        )
        sim = InterventionSimulator()
        with patch(
            "intervention_simulator.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            with patch.object(
                sim, "_get_latest_value",
                return_value=3.1,
            ):
                result = sim.simulate(
                    patient_id="test-patient",
                    treatment="glucose",
                    outcome="creatinine",
                    intervention_value=-20.0,
                    n_simulations=1000,
                )
        ci = result["confidence_interval_95"]
        assert ci["low"] < ci["high"]
        assert ci["low"] <= result[
            "distribution"
        ]["mean"]
        assert ci["high"] >= result[
            "distribution"
        ]["mean"]

    def test_simulate_prob_improvement(self):
        from intervention_simulator import (
            InterventionSimulator,
        )
        sim = InterventionSimulator()
        with patch(
            "intervention_simulator.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            with patch.object(
                sim, "_get_latest_value",
                return_value=3.1,
            ):
                result = sim.simulate(
                    patient_id="test-patient",
                    treatment="glucose",
                    outcome="creatinine",
                    intervention_value=-20.0,
                    n_simulations=1000,
                )
        assert 0.0 <= result["prob_improvement"] <= 1.0

    def test_simulate_no_graph(self):
        from intervention_simulator import (
            InterventionSimulator,
        )
        sim = InterventionSimulator()
        with patch(
            "intervention_simulator.load_causal_graph",
            return_value={},
        ):
            result = sim.simulate(
                patient_id="test-patient",
                treatment="glucose",
                outcome="creatinine",
                intervention_value=-20.0,
            )
        assert "error" in result

    def test_simulate_missing_path(self):
        from intervention_simulator import (
            InterventionSimulator,
        )
        sim = InterventionSimulator()
        with patch(
            "intervention_simulator.load_causal_graph",
            return_value=self._make_mock_graph(),
        ):
            result = sim.simulate(
                patient_id="test-patient",
                treatment="heart_rate",
                outcome="glucose",
                intervention_value=10.0,
            )
        assert "error" in result


# ── CausalDriftDetector ────────────────────────────

class TestCausalDriftDetector:

    def _make_graph(self, effects: dict):
        return {
            "effect_sizes": json.dumps(effects),
            "created_at": "2026-05-20 12:00:00",
        }

    def test_no_drift_same_effects(self):
        from drift_detector import CausalDriftDetector
        detector = CausalDriftDetector()
        effects = {
            "glucose->creatinine": {
                "effect": 0.0002,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            }
        }
        graphs = [
            self._make_graph(effects),
            self._make_graph(effects),
        ]
        with patch.object(
            detector,
            "_get_last_two_graphs",
            return_value=graphs,
        ):
            result = detector.detect_drift(
                "test-patient"
            )
        assert result["drift_detected"] is False
        assert result["drift_count"] == 0

    def test_drift_detected_large_change(self):
        from drift_detector import CausalDriftDetector
        detector = CausalDriftDetector()
        current = self._make_graph({
            "glucose->creatinine": {
                "effect": 0.002,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            }
        })
        previous = self._make_graph({
            "glucose->creatinine": {
                "effect": 0.0002,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            }
        })
        with patch.object(
            detector,
            "_get_last_two_graphs",
            return_value=[current, previous],
        ):
            result = detector.detect_drift(
                "test-patient"
            )
        assert result["drift_detected"] is True
        assert result["drift_count"] >= 1

    def test_new_relationship_detected(self):
        from drift_detector import CausalDriftDetector
        detector = CausalDriftDetector()
        current = self._make_graph({
            "glucose->creatinine": {
                "effect": 0.002,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            },
            "systolic_bp->creatinine": {
                "effect": 0.024,
                "treatment": "systolic_bp",
                "outcome": "creatinine",
                "samples": 20,
            },
        })
        previous = self._make_graph({
            "glucose->creatinine": {
                "effect": 0.002,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            }
        })
        with patch.object(
            detector,
            "_get_last_two_graphs",
            return_value=[current, previous],
        ):
            result = detector.detect_drift(
                "test-patient"
            )
        assert result["drift_detected"] is True
        new_rels = [
            e for e in result["drift_events"]
            if e["drift_type"] == "new_relationship"
        ]
        assert len(new_rels) >= 1

    def test_insufficient_history(self):
        from drift_detector import CausalDriftDetector
        detector = CausalDriftDetector()
        with patch.object(
            detector,
            "_get_last_two_graphs",
            return_value=[],
        ):
            result = detector.detect_drift(
                "test-patient"
            )
        assert result["drift_detected"] is False
        assert result["reason"] == (
            "insufficient_history"
        )

    def test_severity_levels(self):
        from drift_detector import CausalDriftDetector
        detector = CausalDriftDetector()
        current = self._make_graph({
            "glucose->creatinine": {
                "effect": 0.02,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            }
        })
        previous = self._make_graph({
            "glucose->creatinine": {
                "effect": 0.0002,
                "treatment": "glucose",
                "outcome": "creatinine",
                "samples": 20,
            }
        })
        with patch.object(
            detector,
            "_get_last_two_graphs",
            return_value=[current, previous],
        ):
            result = detector.detect_drift(
                "test-patient"
            )
        assert result["drift_detected"] is True
        severities = [
            e["severity"]
            for e in result["drift_events"]
        ]
        assert any(
            s in ["warning", "critical"]
            for s in severities
        )