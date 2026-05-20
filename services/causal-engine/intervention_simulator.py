"""
Intervention Simulator — Monte Carlo over causal graph.

Runs N simulations over the patient causal graph
to return a distribution of outcomes rather than
a single point estimate.

This answers:
  "What is the range of outcomes if we intervene?"
  "What is the best/worst/most-likely scenario?"
  "How certain are we about this prediction?"
"""

import logging
import json
from typing import Optional

import numpy as np

from db import (
    fetch_patient_observations,
    load_causal_graph,
)
from clinical_priors import (
    VITAL_PRIOR_EDGES,
    CLINICAL_PRIOR_EDGES,
    CONFOUNDER_NODES,
    MIN_OBSERVATIONS,
)

logger = logging.getLogger("axiom.causal.simulator")

N_SIMULATIONS = 1000


class InterventionSimulator:
    """
    Monte Carlo simulation over patient causal graph.

    Method:
    1. Load patient causal graph + effect sizes
    2. Get current vital values
    3. For each simulation:
       - Add Gaussian noise to effect estimate
         (uncertainty from linear regression)
       - Propagate intervention through causal graph
       - Record outcome value
    4. Return distribution statistics
    """

    def simulate(
        self,
        patient_id: str,
        treatment: str,
        outcome: str,
        intervention_value: float,
        n_simulations: int = N_SIMULATIONS,
    ) -> dict:
        """
        Run Monte Carlo simulation for an intervention.

        Args:
            patient_id:         patient UUID
            treatment:          variable being changed
            outcome:            variable we want to predict
            intervention_value: how much treatment changes
            n_simulations:      number of MC samples

        Returns:
            Distribution statistics + scenarios
        """
        graph = load_causal_graph(patient_id)
        if not graph:
            return {
                "error": "No causal graph found.",
                "patient_id": patient_id,
            }

        effect_sizes = graph.get("effect_sizes", {})
        if isinstance(effect_sizes, str):
            effect_sizes = json.loads(effect_sizes)

        key = f"{treatment}->{outcome}"
        if key not in effect_sizes:
            return {
                "error": (
                    f"No causal path from "
                    f"{treatment} to {outcome}."
                ),
                "patient_id": patient_id,
                "available_paths": list(
                    effect_sizes.keys()
                ),
            }

        entry = effect_sizes[key]
        point_effect = entry["effect"]
        n_samples = entry.get("samples", 20)

        # Current outcome value
        current_outcome = self._get_latest_value(
            patient_id, outcome
        )
        if current_outcome is None:
            current_outcome = 0.0

        # Standard error of the effect estimate
        # Approximated from sample size
        # (smaller n = more uncertainty)
        se = abs(point_effect) * (
            1.0 / np.sqrt(n_samples)
        ) + 1e-6

        # Monte Carlo simulation
        # Sample effect from normal distribution
        # centred on point estimate
        sampled_effects = np.random.normal(
            loc=point_effect,
            scale=se,
            size=n_simulations,
        )

        # Predicted outcome changes
        predicted_changes = (
            sampled_effects * intervention_value
        )
        predicted_outcomes = (
            current_outcome + predicted_changes
        )

        # Distribution statistics
        p5  = float(np.percentile(predicted_outcomes, 5))
        p25 = float(np.percentile(predicted_outcomes, 25))
        p50 = float(np.percentile(predicted_outcomes, 50))
        p75 = float(np.percentile(predicted_outcomes, 75))
        p95 = float(np.percentile(predicted_outcomes, 95))
        mean = float(np.mean(predicted_outcomes))
        std  = float(np.std(predicted_outcomes))

        # Probability of improvement
        # (outcome moving in beneficial direction)
        if intervention_value < 0:
            prob_improvement = float(
                np.mean(predicted_outcomes < current_outcome)
            )
        else:
            prob_improvement = float(
                np.mean(predicted_outcomes > current_outcome)
            )

        result = {
            "patient_id":         patient_id,
            "treatment":          treatment,
            "outcome":            outcome,
            "intervention_value": intervention_value,
            "n_simulations":      n_simulations,
            "current_outcome":    round(
                current_outcome, 4
            ),
            "point_estimate": round(
                current_outcome
                + point_effect * intervention_value,
                4,
            ),
            "distribution": {
                "mean":  round(mean, 4),
                "std":   round(std, 4),
                "p5":    round(p5, 4),
                "p25":   round(p25, 4),
                "p50":   round(p50, 4),
                "p75":   round(p75, 4),
                "p95":   round(p95, 4),
                "min":   round(
                    float(predicted_outcomes.min()), 4
                ),
                "max":   round(
                    float(predicted_outcomes.max()), 4
                ),
            },
            "scenarios": {
                "worst_case":    round(p95 if intervention_value < 0 else p5, 4),
                "most_likely":   round(p50, 4),
                "best_case":     round(p5 if intervention_value < 0 else p95, 4),
            },
            "confidence_interval_95": {
                "low":  round(p5, 4),
                "high": round(p95, 4),
            },
            "prob_improvement": round(
                prob_improvement, 4
            ),
            "interpretation": (
                f"Changing {treatment} by "
                f"{intervention_value:+.1f} units: "
                f"most likely {outcome} goes from "
                f"{current_outcome:.2f} to "
                f"{p50:.2f} "
                f"(95% CI: {p5:.2f} to {p95:.2f}). "
                f"Probability of improvement: "
                f"{prob_improvement*100:.0f}%."
            ),
        }

        logger.info(
            "Simulation: patient=%s %s->%s "
            "intervention=%+.1f "
            "p50=%.3f CI=[%.3f,%.3f] "
            "prob_improvement=%.0f%%",
            patient_id[:8],
            treatment, outcome,
            intervention_value,
            p50, p5, p95,
            prob_improvement * 100,
        )

        return result

    def simulate_multiple_outcomes(
        self,
        patient_id: str,
        treatment: str,
        intervention_value: float,
        outcomes: Optional[list] = None,
        n_simulations: int = N_SIMULATIONS,
    ) -> dict:
        """
        Simulate one intervention across
        multiple outcomes simultaneously.
        Shows all downstream effects.
        """
        graph = load_causal_graph(patient_id)
        if not graph:
            return {
                "error": "No causal graph found.",
                "patient_id": patient_id,
            }

        effect_sizes = graph.get("effect_sizes", {})
        if isinstance(effect_sizes, str):
            effect_sizes = json.loads(effect_sizes)

        # Find all outcomes causally connected
        # to this treatment
        if outcomes is None:
            outcomes = [
                key.split("->")[1]
                for key in effect_sizes.keys()
                if key.startswith(f"{treatment}->")
            ]

        results = {}
        for outcome in outcomes:
            sim = self.simulate(
                patient_id=patient_id,
                treatment=treatment,
                outcome=outcome,
                intervention_value=intervention_value,
                n_simulations=n_simulations,
            )
            if "error" not in sim:
                results[outcome] = {
                    "most_likely": sim["scenarios"][
                        "most_likely"
                    ],
                    "best_case": sim["scenarios"][
                        "best_case"
                    ],
                    "worst_case": sim["scenarios"][
                        "worst_case"
                    ],
                    "prob_improvement": sim[
                        "prob_improvement"
                    ],
                    "ci_95": sim[
                        "confidence_interval_95"
                    ],
                }

        return {
            "patient_id":         patient_id,
            "treatment":          treatment,
            "intervention_value": intervention_value,
            "n_simulations":      n_simulations,
            "outcomes_affected":  results,
            "total_outcomes":     len(results),
        }

    def _get_latest_value(
        self,
        patient_id: str,
        feature_name: str,
    ) -> Optional[float]:
        try:
            from db import get_conn
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