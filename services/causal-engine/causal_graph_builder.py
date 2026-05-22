"""
PatientCausalGraphBuilder — Fixed for vital-only data.

When medication/condition nodes are not in observations,
we compute vital->vital causal effects using the
prior edges between outcome nodes.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

import pandas as pd

from clinical_priors import (
    CLINICAL_PRIOR_EDGES,
    OUTCOME_NODES,
    CONFOUNDER_NODES,
    MIN_OBSERVATIONS,
    get_prior_edges_for_nodes,
)
from zk_client import generate_graph_proof
from federated_client import get_global_weights, blend_with_federated
from db import (
    fetch_patient_observations,
    save_causal_graph,
)

logger = logging.getLogger("axiom.causal.builder")

# Vital-to-vital causal relationships
# These fire when only vitals are available
VITAL_PRIOR_EDGES = [
    ("glucose",      "creatinine"),
    ("systolic_bp",  "heart_rate"),
    ("heart_rate",   "spo2"),
    ("creatinine",   "spo2"),
    ("glucose",      "heart_rate"),
    ("systolic_bp",  "creatinine"),
]


class PatientCausalGraphBuilder:

    def __init__(self):
        self._graphs_built = 0
        self._graphs_failed = 0

    def _prepare_dataframe(
        self, observations: list
    ) -> pd.DataFrame:
        """
        Group observations by feature, align by index.
        Each row = one synthetic time point.
        """
        if not observations:
            return pd.DataFrame()

        dob = None
        gender = "unknown"
        for obs in observations:
            if obs.get("date_of_birth"):
                dob = obs["date_of_birth"]
                gender = obs.get("gender", "unknown")
                break

        age = 50.0
        if dob:
            try:
                dob_dt = pd.to_datetime(dob)
                age = round(
                    (pd.Timestamp.now() - dob_dt).days
                    / 365.25, 1
                )
            except Exception:
                pass

        gender_encoded = 1 if gender == "male" else 0

        feature_values: dict = {}
        for obs in observations:
            feature = obs.get("feature_name", "")
            value = obs.get("value_quantity")
            if not feature or value is None:
                continue
            if feature not in feature_values:
                feature_values[feature] = []
            feature_values[feature].append(float(value))

        if not feature_values:
            return pd.DataFrame()

        min_len = min(
            len(v) for v in feature_values.values()
        )
        if min_len < MIN_OBSERVATIONS:
            return pd.DataFrame()

        data = {}
        for feature, values in feature_values.items():
            data[feature] = values[:min_len]

        data["age"] = [age] * min_len
        data["gender_encoded"] = [
            gender_encoded
        ] * min_len

        df = pd.DataFrame(data)
        logger.info(
            "DataFrame: shape=%s columns=%s",
            df.shape, list(df.columns),
        )
        return df

    def _compute_effect_sizes(
        self, df: pd.DataFrame, patient_id: str
    ) -> dict:
        from dowhy import CausalModel

        available = set(df.columns.tolist())
        confounders = [
            c for c in CONFOUNDER_NODES
            if c in available
        ]

        # Use clinical priors + vital-vital edges
        all_edges = (
            CLINICAL_PRIOR_EDGES + VITAL_PRIOR_EDGES
        )

        # Find pairs where both nodes are in data
        candidate_pairs = [
            (src, dst) for src, dst in all_edges
            if src in available and dst in available
            and src != dst
        ]

        logger.info(
            "Patient %s: %d candidate pairs "
            "from %d available columns",
            patient_id[:8],
            len(candidate_pairs),
            len(available),
        )

        effect_sizes = {}

        for treatment, outcome in candidate_pairs:
            cols = (
                [treatment, outcome]
                + [
                    c for c in confounders
                    if c != treatment and c != outcome
                ]
            )
            sub_df = df[
                [c for c in cols if c in df.columns]
            ].dropna()

            if len(sub_df) < MIN_OBSERVATIONS:
                continue

            try:
                model = CausalModel(
                    data=sub_df,
                    treatment=treatment,
                    outcome=outcome,
                    common_causes=[
                        c for c in confounders
                        if c in sub_df.columns
                        and c != treatment
                        and c != outcome
                    ],
                )
                identified = model.identify_effect(
                    proceed_when_unidentifiable=True
                )
                estimate = model.estimate_effect(
                    identified,
                    method_name=(
                        "backdoor.linear_regression"
                    ),
                    test_significance=False,
                )
                effect = float(estimate.value)
                key = f"{treatment}->{outcome}"
                effect_sizes[key] = {
                    "effect": round(effect, 4),
                    "treatment": treatment,
                    "outcome": outcome,
                    "samples": len(sub_df),
                }
                logger.info(
                    "Patient %s: %s->%s effect=%.4f",
                    patient_id[:8],
                    treatment, outcome, effect,
                )
            except Exception as e:
                logger.debug(
                    "Effect failed %s->%s: %s",
                    treatment, outcome, e,
                )

        return effect_sizes

    def build_causal_graph(
        self, patient_id: str
    ) -> dict:
        start = time.perf_counter()
        logger.info(
            "Building causal graph: patient=%s",
            patient_id[:8],
        )

        observations = fetch_patient_observations(
            patient_id, limit=200
        )

        if len(observations) < MIN_OBSERVATIONS:
            return {
                "patient_id": patient_id,
                "graph_id": str(uuid.uuid4()),
                "edges": [], "effect_sizes": {},
                "node_count": 0, "edge_count": 0,
                "empty": True,
                "reason": "insufficient_data",
                "built_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        df = self._prepare_dataframe(observations)

        if df.empty or len(df) < MIN_OBSERVATIONS:
            return {
                "patient_id": patient_id,
                "graph_id": str(uuid.uuid4()),
                "edges": [], "effect_sizes": {},
                "node_count": 0, "edge_count": 0,
                "empty": True,
                "reason": "dataframe_empty",
                "built_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        effect_sizes = self._compute_effect_sizes(
            df, patient_id
        )

        available = set(df.columns.tolist())
        all_edges = (
            CLINICAL_PRIOR_EDGES + VITAL_PRIOR_EDGES
        )
        edges = [
            (s, d) for s, d in all_edges
            if s in available and d in available
        ]
        edge_list = [
            f"{s} -> {d}" for s, d in edges
        ]
        node_set = set()
        for s, d in edges:
            node_set.add(s)
            node_set.add(d)
        node_list = sorted(list(node_set))

        build_time_ms = (
            time.perf_counter() - start
        ) * 1000

        # Blend with federated global weights
        try:
            fed_weights = get_global_weights()
            if fed_weights:
                effect_sizes = blend_with_federated(
                    local_effects=effect_sizes,
                    n_observations=len(df),
                    federated_weights=fed_weights,
                )
                logger.info(
                    'Federated blend applied: patient=%s',
                    patient_id[:8],
                )
        except Exception as e:
            logger.debug(
                'Federated blend skipped: %s', e
            )

        # Generate ZK integrity proof BEFORE saving
        zk_proof = None
        try:
            zk_proof = generate_graph_proof(
                graph_id=str(uuid.uuid4()),
                patient_id=patient_id,
                edges=edge_list,
                effect_sizes=effect_sizes,
                built_at=datetime.now(timezone.utc).isoformat(),
            )
            if zk_proof:
                logger.info(
                    "ZK proof: patient=%s proof=%s",
                    patient_id[:8], zk_proof[:12],
                )
        except Exception as e:
            logger.warning(
                "ZK proof skipped: %s", e
            )

        try:
            save_causal_graph(
                patient_id=patient_id,
                adjacency_json=edge_list,
                effect_sizes=effect_sizes,
                node_list=node_list,
                samples_used=len(df),
                build_time_ms=round(build_time_ms, 2),
                zk_integrity_proof=zk_proof,
            )
        except Exception as e:
            logger.error(
                "Save failed %s: %s",
                patient_id[:8], e,
            )

        self._graphs_built += 1
        result = {
            "patient_id": patient_id,
            "graph_id": str(uuid.uuid4()),
            "edges": edge_list,
            "effect_sizes": effect_sizes,
            "node_list": node_list,
            "node_count": len(node_list),
            "edge_count": len(edge_list),
            "effect_count": len(effect_sizes),
            "samples_used": len(df),
            "build_time_ms": round(build_time_ms, 2),
            "empty": len(effect_sizes) == 0,
            "zk_integrity_proof": zk_proof,
            "built_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        logger.info(
            "Graph built: patient=%s nodes=%d "
            "edges=%d effects=%d time=%.0fms",
            patient_id[:8],
            result["node_count"],
            result["edge_count"],
            result["effect_count"],
            build_time_ms,
        )
        return result

    def status(self) -> dict:
        return {
            "graphs_built": self._graphs_built,
            "graphs_failed": self._graphs_failed,
        }