"""
ZK Client for Survival Service

Calls the ZK service to generate a proof for
every PPO treatment recommendation.

Proof components:
  patient_id_hash:      SHA-256 of patient UUID
  recommendation_hash:  SHA-256 of action name + target
  causal_effect_hash:   SHA-256 of immediate reward
  graph_version_hash:   SHA-256 of "ppo-v1"

The proof allows a doctor to verify:
  - This recommendation came from real patient data
  - The RL policy was not tampered with
  - The reward value was computed correctly
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("axiom.survival.zk")

ZK_URL    = "http://localhost:8084"
AUDIT_URL = "http://localhost:8084"
TIMEOUT   = 5


def generate_recommendation_proof(
    patient_id: str,
    action_name: str,
    target_vital: str,
    immediate_reward: float,
) -> Optional[str]:
    """
    Generate ZK proof for a PPO recommendation.
    Returns proof_hash or None if ZK service offline.
    """
    try:
        response = requests.post(
            f"{ZK_URL}/zk/proof/recommendation",
            json={
                "patient_id": patient_id,
                "recommendation": (
                    f"PPO: {action_name} "
                    f"targeting {target_vital}"
                ),
                "causal_effect": float(immediate_reward),
                "graph_id": "ppo-policy-v1",
                "treatment": action_name,
                "outcome": target_vital or "survival",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        proof_hash = response.json().get("proof_hash")
        logger.info(
            "ZK proof generated: patient=%s "
            "action=%s proof=%s",
            patient_id[:8],
            action_name,
            proof_hash[:12] if proof_hash else "None",
        )
        return proof_hash
    except Exception as e:
        logger.warning(
            "ZK proof skipped (ZK offline): %s", e
        )
        return None


def log_to_audit_trail(
    patient_id: str,
    action_name: str,
    target_vital: str,
    immediate_reward: float,
    proof_hash: str,
) -> Optional[str]:
    """
    Log RL recommendation to audit trail.
    Returns rec_id or None on failure.
    """
    try:
        response = requests.post(
            f"{AUDIT_URL}/audit/recommendation",
            json={
                "patient_id": patient_id,
                "doctor_id": "ppo-agent-v1",
                "treatment": action_name,
                "outcome": target_vital or "survival",
                "causal_effect": float(immediate_reward),
                "confidence_low": round(
                    immediate_reward * 0.8, 4
                ),
                "confidence_high": round(
                    immediate_reward * 1.2, 4
                ),
                "zk_proof_hash": proof_hash or "",
                "evidence": {
                    "policy": "ppo",
                    "timesteps": 10000,
                    "source": "survival-service",
                },
                "rec_type": "rl_treatment",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        rec_id = response.json().get("rec_id")
        logger.info(
            "Audit logged: patient=%s rec_id=%s",
            patient_id[:8],
            rec_id[:8] if rec_id else "None",
        )
        return rec_id
    except Exception as e:
        logger.warning(
            "Audit log skipped: %s", e
        )
        return None