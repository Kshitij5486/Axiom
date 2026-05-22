"""
Patient Encoder

Converts per-patient causal graph + raw vitals
into a fixed-length 11-dimensional state vector.

This vector is the input to both:
  - Deep Cox model (survival prediction)
  - PPO environment state (treatment policy)

Dimensions:
  [0]  glucose_mean          (mg/dL, normalized)
  [1]  creatinine_mean       (mg/dL, normalized)
  [2]  heart_rate_mean       (bpm, normalized)
  [3]  systolic_bp_mean      (mmHg, normalized)
  [4]  spo2_mean             (%, normalized)
  [5]  glucose->creatinine   causal effect
  [6]  systolic_bp->creatinine causal effect
  [7]  systolic_bp->heart_rate causal effect
  [8]  heart_rate->spo2      causal effect
  [9]  creatinine->spo2      causal effect
  [10] glucose->heart_rate   causal effect

Normalization ranges (clinical reference):
  glucose:      70  - 400  mg/dL
  creatinine:   0.5 - 5.0  mg/dL
  heart_rate:   40  - 150  bpm
  systolic_bp:  80  - 200  mmHg
  spo2:         80  - 100  %
  effects:      clipped to [-2, 2] then /2 -> [-1,1]
"""

import json
import logging
from typing import Optional

import numpy as np
import psycopg2
import psycopg2.extras

logger = logging.getLogger("axiom.survival.encoder")

DB_CONFIG = {
    "host":     "localhost",
    "port":     5439,
    "dbname":   "axiom",
    "user":     "axiom_user",
    "password": "axiom_secret",
}

# Normalization ranges
VITAL_RANGES = {
    "glucose":     (70.0,  400.0),
    "creatinine":  (0.5,   5.0),
    "heart_rate":  (40.0,  150.0),
    "systolic_bp": (80.0,  200.0),
    "spo2":        (80.0,  100.0),
}

# Causal effect keys in fixed order
CAUSAL_KEYS = [
    "glucose->creatinine",
    "systolic_bp->creatinine",
    "systolic_bp->heart_rate",
    "heart_rate->spo2",
    "creatinine->spo2",
    "glucose->heart_rate",
]

STATE_DIM = 11  # 5 vitals + 6 causal effects


def normalize_vital(
    value: float, feature: str
) -> float:
    lo, hi = VITAL_RANGES.get(feature, (0.0, 1.0))
    normalized = (value - lo) / (hi - lo)
    return float(np.clip(normalized, 0.0, 1.0))


def normalize_effect(value: float) -> float:
    clipped = np.clip(value, -2.0, 2.0)
    return float(clipped / 2.0)


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_patient_vitals(patient_id: str) -> dict:
    """Get average vitals for a patient."""
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT feature_name, AVG(value_quantity) as avg_val
        FROM observations
        WHERE patient_id = %s
          AND feature_name IN (
            'glucose', 'creatinine', 'heart_rate',
            'systolic_bp', 'spo2'
          )
          AND value_quantity IS NOT NULL
        GROUP BY feature_name
        """,
        (patient_id,),
    )
    rows = {
        r["feature_name"]: float(r["avg_val"])
        for r in cursor.fetchall()
    }
    cursor.close()
    conn.close()
    return rows


def get_causal_effects(patient_id: str) -> dict:
    """Get causal effect sizes from stored graph."""
    conn = get_conn()
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor.execute(
        """
        SELECT effect_sizes
        FROM causal_graphs
        WHERE patient_id = %s
          AND is_current = TRUE
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return {}

    effect_sizes = row["effect_sizes"]
    if isinstance(effect_sizes, str):
        effect_sizes = json.loads(effect_sizes)

    # Extract scalar effect values
    effects = {}
    for key, val in effect_sizes.items():
        if isinstance(val, dict):
            effects[key] = float(val.get("effect", 0.0))
        else:
            effects[key] = float(val)

    return effects


def encode_patient(
    patient_id: str,
) -> Optional[np.ndarray]:
    """
    Encode patient into 11-dimensional state vector.
    Returns None if insufficient data.
    """
    vitals = get_patient_vitals(patient_id)
    effects = get_causal_effects(patient_id)

    if not vitals:
        logger.warning(
            "No vitals for patient %s", patient_id[:8]
        )
        return None

    # Build state vector
    state = np.zeros(STATE_DIM, dtype=np.float32)

    # Dimensions 0-4: normalized vitals
    features = [
        "glucose", "creatinine", "heart_rate",
        "systolic_bp", "spo2",
    ]
    for i, feat in enumerate(features):
        val = vitals.get(feat, 0.0)
        state[i] = normalize_vital(val, feat)

    # Dimensions 5-10: normalized causal effects
    for i, key in enumerate(CAUSAL_KEYS):
        effect = effects.get(key, 0.0)
        state[5 + i] = normalize_effect(effect)

    logger.debug(
        "Encoded patient %s: state=%s",
        patient_id[:8], state.tolist(),
    )

    return state


def encode_patient_with_metadata(
    patient_id: str,
) -> dict:
    """
    Encode patient and return state + raw values.
    Used for debugging and API responses.
    """
    vitals = get_patient_vitals(patient_id)
    effects = get_causal_effects(patient_id)
    state = encode_patient(patient_id)

    if state is None:
        return {
            "patient_id": patient_id,
            "state": None,
            "error": "insufficient_data",
        }

    return {
        "patient_id": patient_id,
        "state_vector": state.tolist(),
        "state_dim": STATE_DIM,
        "raw_vitals": vitals,
        "causal_effects": {
            k: effects.get(k, 0.0)
            for k in CAUSAL_KEYS
        },
        "normalized_vitals": {
            feat: float(state[i])
            for i, feat in enumerate([
                "glucose", "creatinine",
                "heart_rate", "systolic_bp", "spo2",
            ])
        },
    }


def encode_all_patients() -> dict:
    """Encode all patients. Returns {patient_id: state}."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients ORDER BY created_at"
    )
    patient_ids = [str(r[0]) for r in cursor.fetchall()]
    cursor.close()
    conn.close()

    encoded = {}
    failed = []

    for pid in patient_ids:
        state = encode_patient(pid)
        if state is not None:
            encoded[pid] = state
        else:
            failed.append(pid)

    logger.info(
        "Encoded %d/%d patients (%d failed)",
        len(encoded), len(patient_ids), len(failed),
    )

    return encoded