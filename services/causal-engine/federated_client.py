"""
Federated Learning Client — Causal Engine Side

Called by the causal graph builder to fetch
global model weights from the federated service.

These weights act as Bayesian priors:
  - If patient has few observations (n<10),
    federated weights dominate
  - If patient has many observations (n>20),
    local DoWhy estimate dominates
  - Blend = alpha * local + (1-alpha) * federated
    alpha = min(1.0, n_observations / 20.0)

This solves the cold-start problem:
  A new patient with only 3 vitals gets a
  reasonable causal estimate from the
  federated population model immediately.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("axiom.causal.federated")

FEDERATED_URL = "http://localhost:8085"
TIMEOUT = 5


def get_global_weights() -> Optional[dict]:
    """
    Fetch current global model weights from
    federated service.
    Returns None if service unavailable.
    """
    try:
        response = requests.get(
            f"{FEDERATED_URL}/federated/weights",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        weights = data.get("global_weights", {})
        if weights:
            logger.info(
                "Federated weights fetched: %d pairs",
                len(weights),
            )
        return weights
    except Exception as e:
        logger.debug(
            "Federated service unavailable: %s", e
        )
        return None


def blend_with_federated(
    local_effects: dict,
    n_observations: int,
    federated_weights: Optional[dict] = None,
) -> dict:
    """
    Blend local DoWhy effects with federated priors.

    alpha = min(1.0, n_observations / 20.0)
    blended = alpha * local + (1-alpha) * federated

    With 20+ observations: pure local estimate
    With 5 observations:   25% local, 75% federated
    With 0 observations:   pure federated prior
    """
    if not federated_weights:
        return local_effects

    alpha = min(1.0, n_observations / 20.0)
    blended = {}

    all_keys = set(local_effects.keys()) | set(
        federated_weights.keys()
    )

    for key in all_keys:
        local_val = local_effects.get(key)
        fed_val = federated_weights.get(key)

        if local_val is not None and fed_val is not None:
            # Extract effect value if dict
            if isinstance(local_val, dict):
                local_effect = local_val.get("effect", 0.0)
            else:
                local_effect = float(local_val)

            blended_effect = (
                alpha * local_effect
                + (1 - alpha) * fed_val
            )

            if isinstance(local_val, dict):
                blended[key] = {
                    **local_val,
                    "effect": round(blended_effect, 6),
                    "federated_prior": round(fed_val, 6),
                    "local_weight": round(alpha, 3),
                    "federated_weight": round(
                        1 - alpha, 3
                    ),
                    "blended": True,
                }
            else:
                blended[key] = round(blended_effect, 6)

        elif local_val is not None:
            blended[key] = local_val
        elif fed_val is not None:
            # Cold start: use federated prior directly
            blended[key] = {
                "effect": round(fed_val, 6),
                "treatment": key.split("->")[0],
                "outcome": key.split("->")[1],
                "samples": 0,
                "federated_prior": round(fed_val, 6),
                "local_weight": 0.0,
                "federated_weight": 1.0,
                "blended": True,
                "cold_start": True,
            }

    logger.info(
        "Blended effects: alpha=%.2f local=%d "
        "federated=%d total=%d",
        alpha,
        len(local_effects),
        len(federated_weights),
        len(blended),
    )

    return blended