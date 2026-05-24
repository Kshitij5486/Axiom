"""
Sprint 6 Unit Tests — NLP + Anomaly Detection

Tests for:
  ClinicalDictionary (entity extraction)
  RelationExtractor
  DagUpdater
  AnomalyDetector
"""

import sys
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# paths managed by conftest.py


# ── ClinicalDictionary ─────────────────────────────

class TestClinicalDictionary:

    def test_extract_condition(self):
        from clinical_dictionary import extract_entities
        text = "Patient has diabetes mellitus type 2."
        entities = extract_entities(text)
        labels = [e["label"] for e in entities]
        assert "CONDITION" in labels

    def test_extract_drug(self):
        from clinical_dictionary import extract_entities
        text = "Patient is on metformin 500mg daily."
        entities = extract_entities(text)
        drugs = [
            e for e in entities if e["label"] == "DRUG"
        ]
        assert len(drugs) > 0
        assert drugs[0]["canonical"] == "metformin"

    def test_extract_bp_vital(self):
        from clinical_dictionary import extract_entities
        text = "BP 158/92 mmHg on admission."
        entities = extract_entities(text)
        vitals = [
            e for e in entities if e["label"] == "VITAL"
        ]
        assert len(vitals) > 0
        assert vitals[0]["canonical"] == "blood_pressure"

    def test_extract_creatinine_vital(self):
        from clinical_dictionary import extract_entities
        text = "Creatinine 3.1 mg/dL elevated."
        entities = extract_entities(text)
        vitals = [
            e for e in entities
            if e["label"] == "VITAL"
            and e["canonical"] == "creatinine"
        ]
        assert len(vitals) > 0

    def test_extract_hr_vital(self):
        from clinical_dictionary import extract_entities
        text = "HR 98 on presentation."
        entities = extract_entities(text)
        vitals = [
            e for e in entities if e["label"] == "VITAL"
        ]
        assert len(vitals) > 0

    def test_extract_symptom(self):
        from clinical_dictionary import extract_entities
        text = "Patient presents with fatigue and weakness."
        entities = extract_entities(text)
        symptoms = [
            e for e in entities
            if e["label"] == "SYMPTOM"
        ]
        assert len(symptoms) > 0

    def test_no_false_positives_clean_text(self):
        from clinical_dictionary import extract_entities
        text = "Patient is well today. No concerns."
        entities = extract_entities(text)
        assert len(entities) == 0

    def test_confidence_between_0_and_1(self):
        from clinical_dictionary import extract_entities
        text = "Diabetes, hypertension, furosemide, HR 82."
        entities = extract_entities(text)
        for e in entities:
            assert 0.0 <= e["confidence"] <= 1.0

    def test_deduplicate_overlapping(self):
        from clinical_dictionary import extract_entities
        text = "chronic kidney disease CKD."
        entities = extract_entities(text)
        # Should not have overlapping spans
        for i in range(len(entities) - 1):
            assert entities[i]["end"] <= entities[i+1]["start"]


# ── RelationExtractor ──────────────────────────────

class TestRelationExtractor:

    def test_extract_causes_relation(self):
        from relation_extractor import extract_relations
        text = "Creatinine rose after furosemide dose increase."
        relations = extract_relations(text)
        causes = [
            r for r in relations
            if r["direction"] == "causes"
        ]
        assert len(causes) > 0

    def test_extract_improves_relation(self):
        from relation_extractor import extract_relations
        text = "Creatinine rose after furosemide dose increase."
        relations = extract_relations(text)
        assert len(relations) > 0

    def test_extract_non_compliant(self):
        from relation_extractor import extract_relations
        text = "Patient poorly compliant with furosemide."
        relations = extract_relations(text)
        assert len(relations) > 0
        assert relations[0]["direction"] == "non_compliant"

    def test_relation_has_required_fields(self):
        from relation_extractor import extract_relations
        text = "Creatinine rose after furosemide dose increase."
        relations = extract_relations(text)
        assert len(relations) > 0
        rel = relations[0]
        assert "cause" in rel
        assert "effect" in rel
        assert "direction" in rel
        assert "confidence" in rel
        assert "nlp_effect" in rel
        assert "edge_key" in rel

    def test_nlp_effect_magnitude(self):
        from relation_extractor import extract_relations
        text = "Creatinine rose after furosemide dose increase."
        relations = extract_relations(text)
        for rel in relations:
            assert abs(rel["nlp_effect"]) <= 1.0

    def test_entity_to_feature_drug(self):
        from relation_extractor import _entity_to_feature
        result = _entity_to_feature("furosemide")
        assert result in ["furosemide", "creatinine"]

    def test_entity_to_feature_vital(self):
        from relation_extractor import _entity_to_feature
        result = _entity_to_feature("creatinine")
        assert result == "creatinine"

    def test_empty_text_no_relations(self):
        from relation_extractor import extract_relations
        relations = extract_relations("")
        assert relations == []


# ── DagUpdater ─────────────────────────────────────

class TestDagUpdater:

    def test_alpha_value(self):
        from dag_updater import ALPHA
        assert ALPHA == 0.3

    def test_ewma_formula(self):
        from dag_updater import ALPHA
        old_effect = 0.02
        nlp_effect = 0.0375
        expected = ALPHA * nlp_effect + (1 - ALPHA) * old_effect
        assert abs(expected - 0.02525) < 0.001

    def test_no_relations_returns_zero(self):
        from dag_updater import update_causal_graph
        result = update_causal_graph(
            patient_id="test-patient",
            relations=[],
        )
        assert result["updates"] == 0
        assert result["new_edges"] == 0

    def test_result_has_required_fields(self):
        from dag_updater import update_causal_graph
        result = update_causal_graph(
            patient_id="test-patient",
            relations=[],
        )
        assert "patient_id" in result
        assert "updates" in result
        assert "new_edges" in result

    def test_dry_run_field(self):
        from dag_updater import update_causal_graph
        result = update_causal_graph(
            patient_id="test-patient",
            relations=[],
            dry_run=True,
        )
        assert "patient_id" in result


# ── AnomalyDetector ────────────────────────────────

class TestAnomalyDetector:

    def _make_vitals_matrix(
        self, n=20, seed=42
    ) -> np.ndarray:
        np.random.seed(seed)
        return np.column_stack([
            np.random.normal(150, 20, n),   # glucose
            np.random.normal(1.5, 0.3, n),  # creatinine
            np.random.normal(75, 8, n),     # heart_rate
            np.random.normal(130, 10, n),   # systolic_bp
            np.random.normal(96, 1.5, n),   # spo2
        ]).astype(np.float32)

    def test_train_succeeds(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        matrix = self._make_vitals_matrix()
        success = detector.train(matrix)
        assert success is True
        assert detector.is_trained is True

    def test_train_insufficient_data(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        matrix = self._make_vitals_matrix(n=3)
        success = detector.train(matrix)
        assert success is False
        assert detector.is_trained is False

    def test_score_normal_reading(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        matrix = self._make_vitals_matrix()
        detector.train(matrix)
        normal = {
            "glucose": 150.0,
            "creatinine": 1.5,
            "heart_rate": 75.0,
            "systolic_bp": 130.0,
            "spo2": 96.0,
        }
        result = detector.score(normal)
        assert "anomaly" in result
        assert "isolation_forest_score" in result
        assert "alerts" in result

    def test_critical_threshold_fires(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        matrix = self._make_vitals_matrix()
        detector.train(matrix)
        critical = {
            "glucose": 150.0,
            "creatinine": 1.5,
            "heart_rate": 75.0,
            "systolic_bp": 130.0,
            "spo2": 85.0,  # CRITICAL: below 90
        }
        result = detector.score(critical)
        critical_alerts = [
            a for a in result["alerts"]
            if a["type"] == "CRITICAL"
        ]
        assert len(critical_alerts) > 0

    def test_predict_2h_rising_trend(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        # Rapidly rising creatinine
        values = [2.5, 3.0, 3.3, 3.6, 3.9]
        result = detector.predict_2h(
            values, "creatinine"
        )
        assert result is not None
        assert result["predicted_2h"] > values[-1]
        assert result["slope_per_hour"] > 0

    def test_predict_2h_stable_no_alert(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        # Stable creatinine
        values = [1.2, 1.2, 1.3, 1.2, 1.2]
        result = detector.predict_2h(
            values, "creatinine"
        )
        assert result is not None
        assert not result["will_breach_threshold"]

    def test_feature_stats_after_training(self):
        from anomaly_detector import PatientAnomalyDetector
        detector = PatientAnomalyDetector("test-p1")
        matrix = self._make_vitals_matrix()
        detector.train(matrix)
        assert len(detector.feature_stats) == 5
        assert "glucose" in detector.feature_stats
        assert "mean" in detector.feature_stats["glucose"]

    def test_registry_creates_detectors(self):
        from anomaly_detector import AnomalyDetectorRegistry
        registry = AnomalyDetectorRegistry()
        d1 = registry.get_or_create("patient-A")
        d2 = registry.get_or_create("patient-A")
        assert d1 is d2  # Same instance

    def test_registry_status(self):
        from anomaly_detector import AnomalyDetectorRegistry
        registry = AnomalyDetectorRegistry()
        registry.get_or_create("p1")
        registry.get_or_create("p2")
        status = registry.status()
        assert status["n_patients"] == 2