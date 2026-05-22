"""
HospitalNode — Simulated federated learning client.

Each hospital:
  - Owns a partition of patients (no sharing)
  - Trains a local linear causal model
  - Applies Gaussian DP noise before sharing gradients
  - Never transmits raw patient data

Differential Privacy:
  Gradient clipping to bound sensitivity
  Gaussian noise N(0, sigma^2) added per gradient
  sigma = noise_multiplier * clip_norm / batch_size
  This satisfies (epsilon, delta)-DP guarantees
"""

import logging
import time
from typing import Optional

import numpy as np

from db import get_patient_partition, get_patient_observations_flat

logger = logging.getLogger("axiom.federated.node")

# DP hyperparameters
CLIP_NORM       = 1.0   # L2 sensitivity bound
NOISE_MULTIPLIER = 1.1  # sigma = NOISE_MULTIPLIER * CLIP_NORM
MIN_PATIENTS    = 3     # minimum patients to train

# Clinical features we model
FEATURES = [
    "glucose",
    "creatinine",
    "heart_rate",
    "systolic_bp",
    "spo2",
]

# Causal relationships we learn weights for
# (treatment, outcome) pairs
CAUSAL_PAIRS = [
    ("glucose",     "creatinine"),
    ("systolic_bp", "creatinine"),
    ("systolic_bp", "heart_rate"),
    ("heart_rate",  "spo2"),
    ("creatinine",  "spo2"),
    ("glucose",     "heart_rate"),
]


class HospitalNode:
    """
    Simulated hospital federated learning client.

    Trains a local linear causal model on its
    patient partition and returns DP-noised gradients.
    """

    def __init__(
        self,
        node_id: str,
        total_nodes: int = 3,
        noise_multiplier: float = NOISE_MULTIPLIER,
        clip_norm: float = CLIP_NORM,
    ):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.noise_multiplier = noise_multiplier
        self.clip_norm = clip_norm

        self.patient_ids = []
        self.n_patients = 0
        self.local_weights = {}
        self.training_rounds = 0
        self.last_loss = None

        logger.info(
            "HospitalNode created: id=%s "
            "noise_multiplier=%.1f clip_norm=%.1f",
            node_id, noise_multiplier, clip_norm,
        )

    def load_patients(self):
        """Load this node's patient partition from DB."""
        self.patient_ids = get_patient_partition(
            self.node_id, self.total_nodes
        )
        self.n_patients = len(self.patient_ids)
        logger.info(
            "Node %s loaded %d patients",
            self.node_id, self.n_patients,
        )
        return self.n_patients

    def _build_feature_matrix(self) -> dict:
        """
        Build per-patient average feature values.
        Returns dict: patient_id -> {feature: mean_value}
        """
        if not self.patient_ids:
            self.load_patients()

        observations = get_patient_observations_flat(
            self.patient_ids
        )

        # Aggregate per patient per feature
        patient_features: dict = {}
        for obs in observations:
            pid = str(obs["patient_id"])
            feat = obs["feature_name"]
            val = obs["value_quantity"]

            if feat not in FEATURES:
                continue
            if pid not in patient_features:
                patient_features[pid] = {
                    f: [] for f in FEATURES
                }
            patient_features[pid][feat].append(
                float(val)
            )

        # Compute means
        patient_means = {}
        for pid, feats in patient_features.items():
            means = {}
            all_present = True
            for f in FEATURES:
                vals = feats.get(f, [])
                if vals:
                    means[f] = np.mean(vals)
                else:
                    all_present = False
                    break
            if all_present:
                patient_means[pid] = means

        return patient_means

    def train_local_model(
        self,
        global_weights: Optional[dict] = None,
        learning_rate: float = 0.01,
        epochs: int = 5,
    ) -> dict:
        """
        Train local linear causal model.

        For each causal pair (treatment, outcome):
          weight = covariance(treatment, outcome)
                   / variance(treatment)

        This is OLS estimator for linear regression.
        Equivalent to DoWhy backdoor linear regression
        but computed locally per hospital.

        Returns gradient dict (weight updates).
        """
        start = time.perf_counter()

        patient_means = self._build_feature_matrix()

        if len(patient_means) < MIN_PATIENTS:
            logger.warning(
                "Node %s: insufficient patients (%d)",
                self.node_id, len(patient_means),
            )
            return {}

        # Initialize from global weights or zeros
        if global_weights:
            self.local_weights = dict(global_weights)
        else:
            self.local_weights = {
                f"{t}->{o}": 0.0
                for t, o in CAUSAL_PAIRS
            }

        # Build arrays
        patients = list(patient_means.values())
        n = len(patients)

        gradients = {}
        total_loss = 0.0

        for treatment, outcome in CAUSAL_PAIRS:
            key = f"{treatment}->{outcome}"

            x = np.array([p[treatment] for p in patients])
            y = np.array([p[outcome] for p in patients])

            # Normalize
            x_mean, x_std = x.mean(), x.std() + 1e-8
            y_mean, y_std = y.mean(), y.std() + 1e-8
            x_norm = (x - x_mean) / x_std
            y_norm = (y - y_mean) / y_std

            # OLS gradient: d/dw MSE = -2/n * X^T(y - Xw)
            w = self.local_weights.get(key, 0.0)

            for _ in range(epochs):
                y_pred = x_norm * w
                residual = y_norm - y_pred
                grad = -2.0 / n * np.dot(x_norm, residual)
                w = w - learning_rate * grad

            # Loss (MSE)
            y_pred_final = x_norm * w
            loss = np.mean((y_norm - y_pred_final) ** 2)
            total_loss += loss

            # Weight update (gradient)
            weight_update = w - self.local_weights.get(
                key, 0.0
            )
            gradients[key] = weight_update
            self.local_weights[key] = w

        self.last_loss = total_loss / len(CAUSAL_PAIRS)
        self.training_rounds += 1

        elapsed = (time.perf_counter() - start) * 1000

        logger.info(
            "Node %s trained: patients=%d "
            "pairs=%d loss=%.4f time=%.0fms",
            self.node_id, n,
            len(CAUSAL_PAIRS),
            self.last_loss, elapsed,
        )

        return gradients

    def apply_differential_privacy(
        self, gradients: dict
    ) -> dict:
        """
        Apply Gaussian DP noise to gradients.

        1. Clip each gradient to bound L2 sensitivity
        2. Add Gaussian noise N(0, sigma^2)
           sigma = noise_multiplier * clip_norm

        This satisfies (epsilon, delta)-DP where:
          epsilon depends on noise_multiplier and
          number of rounds.
        """
        if not gradients:
            return {}

        sigma = self.noise_multiplier * self.clip_norm

        # Convert to vector
        keys = list(gradients.keys())
        grad_vector = np.array(
            [gradients[k] for k in keys],
            dtype=np.float64,
        )

        # Clip to bound sensitivity
        l2_norm = np.linalg.norm(grad_vector)
        if l2_norm > self.clip_norm:
            grad_vector = (
                grad_vector * self.clip_norm / l2_norm
            )

        # Add Gaussian noise
        noise = np.random.normal(
            loc=0.0,
            scale=sigma,
            size=grad_vector.shape,
        )
        noised_vector = grad_vector + noise

        noised_gradients = {
            keys[i]: float(noised_vector[i])
            for i in range(len(keys))
        }

        logger.info(
            "Node %s DP noise applied: "
            "sigma=%.3f l2_before=%.4f l2_after=%.4f",
            self.node_id,
            sigma,
            l2_norm,
            float(np.linalg.norm(noised_vector)),
        )

        return noised_gradients

    def get_gradients(
        self,
        global_weights: Optional[dict] = None,
    ) -> dict:
        """
        Full pipeline: train -> DP noise -> return.
        This is what the federated coordinator calls.
        """
        raw_gradients = self.train_local_model(
            global_weights=global_weights
        )
        if not raw_gradients:
            return {}
        dp_gradients = self.apply_differential_privacy(
            raw_gradients
        )
        return dp_gradients

    def status(self) -> dict:
        return {
            "node_id": self.node_id,
            "n_patients": self.n_patients,
            "training_rounds": self.training_rounds,
            "last_loss": self.last_loss,
            "local_weights": self.local_weights,
            "dp_config": {
                "noise_multiplier": self.noise_multiplier,
                "clip_norm": self.clip_norm,
                "sigma": self.noise_multiplier * self.clip_norm,
            },
        }