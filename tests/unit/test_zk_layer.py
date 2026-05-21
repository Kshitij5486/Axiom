"""
Sprint 3 Unit Tests — ZK Trust Layer

Tests for:
  ClinicalRecommendationProof
  CausalGraphIntegrityProof
  AuditTrail
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..",
    "services", "zk-service"
))


# ── ClinicalRecommendationProof ────────────────────

class TestClinicalRecommendationProof:

    def test_generate_returns_proof(self):
        from zk_proof import ClinicalRecommendationProof
        proof = ClinicalRecommendationProof.generate(
            patient_id="test-patient-001",
            recommendation="Reduce BP with lisinopril",
            causal_effect=0.0239,
            graph_id="test-graph-001",
            treatment="systolic_bp",
            outcome="creatinine",
        )
        assert "proof_hash" in proof
        assert "proof_id" in proof
        assert proof["verified"] is True
        assert proof["algorithm"] == "sha256-composite-v1"
        assert len(proof["proof_hash"]) == 64

    def test_proof_hash_is_deterministic_same_date(self):
        from zk_proof import ClinicalRecommendationProof
        from unittest.mock import patch
        import datetime

        fixed_dt = datetime.datetime(
            2026, 5, 20, 12, 0, 0,
            tzinfo=datetime.timezone.utc
        )
        with patch(
            "zk_proof.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.timezone = datetime.timezone

            proof1 = ClinicalRecommendationProof.generate(
                patient_id="p1",
                recommendation="rec1",
                causal_effect=0.5,
                graph_id="g1",
                treatment="t1",
                outcome="o1",
            )
            proof2 = ClinicalRecommendationProof.generate(
                patient_id="p1",
                recommendation="rec1",
                causal_effect=0.5,
                graph_id="g1",
                treatment="t1",
                outcome="o1",
            )
        assert proof1["proof_hash"] == proof2["proof_hash"]

    def test_verify_valid_proof(self):
        from zk_proof import ClinicalRecommendationProof
        import datetime

        today = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%d")

        proof = ClinicalRecommendationProof.generate(
            patient_id="test-patient",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
        )

        result = ClinicalRecommendationProof.verify(
            proof_hash=proof["proof_hash"],
            patient_id="test-patient",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
            timestamp_date=today,
        )
        assert result["valid"] is True
        assert result["match"] is True

    def test_verify_tampered_hash_fails(self):
        from zk_proof import ClinicalRecommendationProof
        import datetime

        today = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%d")

        proof = ClinicalRecommendationProof.generate(
            patient_id="test-patient",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
        )

        # Tamper the hash
        tampered = "00" + proof["proof_hash"][2:]

        result = ClinicalRecommendationProof.verify(
            proof_hash=tampered,
            patient_id="test-patient",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
            timestamp_date=today,
        )
        assert result["valid"] is False
        assert result["match"] is False

    def test_verify_wrong_effect_fails(self):
        from zk_proof import ClinicalRecommendationProof
        import datetime

        today = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%d")

        proof = ClinicalRecommendationProof.generate(
            patient_id="test-patient",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
        )

        result = ClinicalRecommendationProof.verify(
            proof_hash=proof["proof_hash"],
            patient_id="test-patient",
            recommendation="Reduce BP",
            causal_effect=0.999,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
            timestamp_date=today,
        )
        assert result["valid"] is False

    def test_different_patients_different_hashes(self):
        from zk_proof import ClinicalRecommendationProof

        proof1 = ClinicalRecommendationProof.generate(
            patient_id="patient-A",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="graph-1",
            treatment="systolic_bp",
            outcome="creatinine",
        )
        proof2 = ClinicalRecommendationProof.generate(
            patient_id="patient-B",
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="graph-1",
            treatment="systolic_bp",
            outcome="creatinine",
        )
        assert proof1["proof_hash"] != proof2["proof_hash"]

    def test_patient_id_never_in_proof(self):
        from zk_proof import ClinicalRecommendationProof

        patient_id = "3319a93d-e164-4ef1-beb9-ac5803d9cf51"
        proof = ClinicalRecommendationProof.generate(
            patient_id=patient_id,
            recommendation="Reduce BP",
            causal_effect=0.0239,
            graph_id="test-graph",
            treatment="systolic_bp",
            outcome="creatinine",
        )
        # Raw patient ID should never appear in proof
        assert patient_id not in proof["proof_hash"]
        assert patient_id not in proof.get(
            "recommendation_hash", ""
        )


# ── CausalGraphIntegrityProof ──────────────────────

class TestCausalGraphIntegrityProof:

    def _make_graph_data(self):
        return {
            "graph_id": "test-graph-001",
            "patient_id": "test-patient-001",
            "edges": [
                "age -> creatinine",
                "glucose -> creatinine",
            ],
            "effect_sizes": {
                "age->creatinine": {"effect": 0.054},
                "glucose->creatinine": {"effect": 0.0002},
            },
            "built_at": "2026-05-20T07:42:19",
        }

    def test_generate_returns_proof(self):
        from zk_proof import CausalGraphIntegrityProof
        data = self._make_graph_data()
        proof = CausalGraphIntegrityProof.generate(
            **data
        )
        assert "integrity_proof" in proof
        assert "edges_hash" in proof
        assert "effects_hash" in proof
        assert len(proof["integrity_proof"]) == 64

    def test_verify_valid_proof(self):
        from zk_proof import CausalGraphIntegrityProof
        data = self._make_graph_data()
        proof = CausalGraphIntegrityProof.generate(
            **data
        )
        result = CausalGraphIntegrityProof.verify(
            integrity_proof=proof["integrity_proof"],
            **data,
        )
        assert result["valid"] is True
        assert result["match"] is True

    def test_tampered_edges_fails(self):
        from zk_proof import CausalGraphIntegrityProof
        data = self._make_graph_data()
        proof = CausalGraphIntegrityProof.generate(
            **data
        )
        # Tamper edges
        tampered_data = dict(data)
        tampered_data["edges"] = [
            "age -> creatinine",
            "glucose -> spo2",  # changed
        ]
        result = CausalGraphIntegrityProof.verify(
            integrity_proof=proof["integrity_proof"],
            **tampered_data,
        )
        assert result["valid"] is False

    def test_tampered_effect_fails(self):
        from zk_proof import CausalGraphIntegrityProof
        data = self._make_graph_data()
        proof = CausalGraphIntegrityProof.generate(
            **data
        )
        tampered_data = dict(data)
        tampered_data["effect_sizes"] = {
            "age->creatinine": {"effect": 0.999},
        }
        result = CausalGraphIntegrityProof.verify(
            integrity_proof=proof["integrity_proof"],
            **tampered_data,
        )
        assert result["valid"] is False

    def test_edge_count_in_proof(self):
        from zk_proof import CausalGraphIntegrityProof
        data = self._make_graph_data()
        proof = CausalGraphIntegrityProof.generate(
            **data
        )
        assert proof["edge_count"] == len(data["edges"])
        assert proof["effect_count"] == len(
            data["effect_sizes"]
        )

    def test_patient_id_hashed_not_exposed(self):
        from zk_proof import CausalGraphIntegrityProof
        data = self._make_graph_data()
        proof = CausalGraphIntegrityProof.generate(
            **data
        )
        assert data["patient_id"] not in proof[
            "integrity_proof"
        ]
        assert data["patient_id"] not in proof[
            "edges_hash"
        ]


# ── ZK Client ──────────────────────────────────────

class TestZKClient:

    def test_generate_graph_proof_calls_service(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "services", "causal-engine"
        ))
        from zk_client import generate_graph_proof

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "integrity_proof": "abc123def456"
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = generate_graph_proof(
                graph_id="test-graph",
                patient_id="test-patient",
                edges=["a -> b"],
                effect_sizes={"a->b": {"effect": 0.5}},
                built_at="2026-05-20",
            )
        assert result == "abc123def456"

    def test_generate_graph_proof_returns_none_on_failure(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "services", "causal-engine"
        ))
        from zk_client import generate_graph_proof

        with patch(
            "requests.post",
            side_effect=Exception("Connection refused")
        ):
            result = generate_graph_proof(
                graph_id="test-graph",
                patient_id="test-patient",
                edges=["a -> b"],
                effect_sizes={},
                built_at="2026-05-20",
            )
        assert result is None