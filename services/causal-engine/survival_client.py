"""
Survival Service Client — Causal Engine Side

Called after causal graph build to enrich the
response with survival prediction and RL recommendation.

This connects Sprint 2 (causal) + Sprint 5 (survival):
  causal graph built
    -> survival risk predicted (Deep Cox)
    -> treatment recommended (PPO)
    -> ZK proof generated (Sprint 3)
    -> audit logged (Sprint 3)
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("axiom.causal.survival")

SURVIVAL_URL = "http://localhost:8082"
TIMEOUT = 10


def get_survival_prediction(
    patient_id: str,
) -> Optional[dict]:
    """
    Fetch survival curve for a patient
    from the survival service.
    Returns None if service unavailable.
    """
    try:
        response = requests.get(
            f"{SURVIVAL_URL}/survival/predict/{patient_id}",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            return None
        logger.info(
            "Survival prediction: patient=%s "
            "risk=%.3f median=%s days",
            patient_id[:8],
            data.get("risk_score", 0),
            data.get("median_survival_days"),
        )
        return data
    except Exception as e:
        logger.debug(
            "Survival service unavailable: %s", e
        )
        return None


def get_treatment_recommendation(
    patient_id: str,
) -> Optional[dict]:
    """
    Fetch PPO treatment recommendation for a patient.
    Returns None if service unavailable or not trained.
    """
    try:
        response = requests.get(
            f"{SURVIVAL_URL}/survival/recommend/{patient_id}",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            return None
        logger.info(
            "Treatment recommendation: patient=%s "
            "action=%s reward=%.3f zk=%s",
            patient_id[:8],
            data.get("recommended_action"),
            data.get("ranked_actions", [{}])[0].get(
                "immediate_reward", 0
            ),
            data.get("zk_proven", False),
        )
        return data
    except Exception as e:
        logger.debug(
            "Survival recommend unavailable: %s", e
        )
        return None