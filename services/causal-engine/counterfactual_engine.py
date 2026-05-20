"""
Counterfactual Query Engine

Answers clinical "what-if" questions using the
patient's causal graph and DoWhy.

Examples:
  "What if this patient's glucose drops by 20 mg/dL?
   What effect does that have on creatinine?"

  "What if we add lisinopril?
   How much does systolic_bp change?"

This is the core clinical value of Axiom —
not just correlation but actual causal effect
estimation per patient.
"""

import logging
import json
from typing import Optional

import numpy as np
import pandas as pd

from clinical_priors import (
    CLINICAL_PRIOR_EDGES,
    VITAL_PRIOR_EDGES,
    OUTCOME_NODES,
    CONFOUNDER_NODES,
    MIN_OBSERVATIONS,
)
from db import (
    fetch_patient_observations,
    load_causal_graph,
    get_conn,
)

logger = logging.getLogger("axiom.causal.counterfactual")


class CounterfactualEngine:
    """
    Answers counterfactual queries for a patient.

    Two query modes:
    1. Graph-based: use stored effect sizes
       (fast, <1ms)
    2. DoWhy-based: recompute from observations
       (slow, ~5s, more accurate)
    """

    def query_from_graph(
        self,
        patient_id: str,
        treatment: str,
        outcome: str,
        intervention_value: Optional[float] = None,
    ) -> dict:
        """
        Fast counterfactual using stored causal graph.
        Returns the stored effect size for
        treatment->outcome.
        """
        graph = load_causal_graph(patient_id)
        if not graph:
            return {
                "error": "No causal graph found. "
                         "Build graph first.",
                "patient_id": patient_id,
            }

        effect_sizes = graph.get("effect_sizes", {})
        if isinstance(effect_sizes, str):
            effect_sizes = json.loads(effect_sizes)

        key = f"{treatment}->{outcome}"
        if key not in effect_sizes:
            return {
                "patient_id": patient_id,
                "treatment": treatment,
                "outcome": outcome,
                "effect": None,
                "found": False,
                "message": (
                    f"No causal relationship found "
                    f"between {treatment} and {outcome} "
                    f"for this patient."
                ),
            }

        entry = effect_sizes[key]
        effect = entry["effect"]

        result = {
            "patient_id": patient_id,
            "treatment": treatment,
            "outcome": outcome,
            "effect_per_unit": effect,
            "found": True,
            "samples": entry.get("samples", 0),
            "interpretation": (
                f"A 1-unit increase in {treatment} "
                f"causes a {effect:+.4f} change "
                f"in {outcome} for this patient."
            ),
        }

        # If intervention value provided, compute
        # expected outcome change
        if intervention_value is not None:
            current = self._get_latest_value(
                patient_id, outcome
            )
            predicted_change = (
                effect * intervention_value
            )
            result["intervention_value"] = (
                intervention_value
            )
            result["predicted_change"] = round(
                predicted_change, 4
            )
            result["current_outcome"] = current
            if current is not None:
                result["predicted_outcome"] = round(
                    current + predicted_change, 4
                )
            result["interpretation"] = (
                f"Changing {treatment} by "
                f"{intervention_value:+.1f} units "
                f"is predicted to change {outcome} by "
                f"{predicted_change:+.4f} units "
                f"(from {current} to "
                f"{result.get('predicted_outcome', '?')})"
            )

        return result

    def query_from_data(
        self,
        patient_id: str,
        treatment: str,
        outcome: str,
        intervention_value: Optional[float] = None,
    ) -> dict:
        """
        Precise counterfactual by rerunning DoWhy
        on patient observations.
        Slower but more accurate than graph lookup.
        """
        from dowhy import CausalModel
        from causal_graph_builder import (
            PatientCausalGraphBuilder,
        )

        observations = fetch_patient_observations(
            patient_id, limit=200
        )
        if len(observations) < MIN_OBSERVATIONS:
            return {
                "error": "Insufficient observations",
                "patient_id": patient_id,
            }

        builder = PatientCausalGraphBuilder()
        df = builder._prepare_dataframe(observations)

        if df.empty:
            return {
                "error": "Could not prepare DataFrame",
                "patient_id": patient_id,
            }

        if treatment not in df.columns:
            return {
                "error": (
                    f"Treatment '{treatment}' not "
                    f"found in patient data. "
                    f"Available: {list(df.columns)}"
                ),
                "patient_id": patient_id,
            }

        if outcome not in df.columns:
            return {
                "error": (
                    f"Outcome '{outcome}' not found "
                    f"in patient data. "
                    f"Available: {list(df.columns)}"
                ),
                "patient_id": patient_id,
            }

        confounders = [
            c for c in CONFOUNDER_NODES
            if c in df.columns
            and c != treatment
            and c != outcome
        ]

        cols = (
            [treatment, outcome] + confounders
        )
        sub_df = df[
            [c for c in cols if c in df.columns]
        ].dropna()

        if len(sub_df) < MIN_OBSERVATIONS:
            return {
                "error": "Insufficient data after "
                         "filtering",
                "patient_id": patient_id,
            }

        try:
            model = CausalModel(
                data=sub_df,
                treatment=treatment,
                outcome=outcome,
                common_causes=confounders,
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

            result = {
                "patient_id": patient_id,
                "treatment": treatment,
                "outcome": outcome,
                "effect_per_unit": round(effect, 4),
                "samples": len(sub_df),
                "method": "dowhy_linear_regression",
                "found": True,
                "interpretation": (
                    f"A 1-unit increase in {treatment} "
                    f"causes a {effect:+.4f} change "
                    f"in {outcome} (recomputed from "
                    f"{len(sub_df)} observations)."
                ),
            }

            if intervention_value is not None:
                current = self._get_latest_value(
                    patient_id, outcome
                )
                predicted_change = (
                    effect * intervention_value
                )
                result["intervention_value"] = (
                    intervention_value
                )
                result["predicted_change"] = round(
                    predicted_change, 4
                )
                result["current_outcome"] = current
                if current is not None:
                    result["predicted_outcome"] = round(
                        current + predicted_change, 4
                    )

            return result

        except Exception as e:
            logger.error(
                "Counterfactual failed: "
                "patient=%s %s->%s error=%s",
                patient_id[:8], treatment, outcome, e,
            )
            return {
                "error": str(e),
                "patient_id": patient_id,
                "treatment": treatment,
                "outcome": outcome,
            }

    def compare_interventions(
        self,
        patient_id: str,
        treatments: list,
        outcome: str,
    ) -> dict:
        """
        Compare multiple treatments for the same outcome.
        Returns ranked list by causal effect size.
        """
        results = []
        for treatment in treatments:
            r = self.query_from_graph(
                patient_id, treatment, outcome
            )
            if r.get("found"):
                results.append({
                    "treatment": treatment,
                    "effect": r["effect_per_unit"],
                    "abs_effect": abs(
                        r["effect_per_unit"]
                    ),
                    "samples": r.get("samples", 0),
                })

        results.sort(
            key=lambda x: x["abs_effect"],
            reverse=True,
        )

        return {
            "patient_id": patient_id,
            "outcome": outcome,
            "ranked_treatments": results,
            "best_treatment": (
                results[0]["treatment"]
                if results else None
            ),
            "total_compared": len(treatments),
            "found": len(results),
        }

    def _get_latest_value(
        self, patient_id: str, feature_name: str
    ) -> Optional[float]:
        """Get the most recent value for a feature."""
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT value_quantity
                FROM observations
                WHERE patient_id = %s
                  AND feature_name = %s
                ORDER BY effective_at DESC
                LIMIT 1
                """,
                (patient_id, feature_name),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return float(row[0]) if row else None
        except Exception:
            return None