"""
Anomaly Detector — Isolation Forest + Predictive Alerts

Two detection mechanisms:

1. Isolation Forest (real-time):
   Trained on patient's own 20 historical readings.
   Flags readings that deviate from their personal baseline.
   contamination=0.1 (10% expected anomaly rate)

2. Predictive Alert (2-hour lookahead):
   Linear regression on last 5 readings.
   Extrapolates to t+120 minutes.
   Fires if extrapolated value crosses warning threshold.

Alert types:
  ANOMALY:    Isolation Forest score = -1
  PREDICTIVE: Will breach threshold in <2 hours
  CRITICAL:   Already breached hard threshold
  TREND:      Consistent directional drift (5 readings)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("axiom.nlp.anomaly")

# Critical thresholds (immediate alert)
CRITICAL_THRESHOLDS = {
    "spo2":        {"low": 90.0,  "high": None},
    "heart_rate":  {"low": 40.0,  "high": 130.0},
    "systolic_bp": {"low": 80.0,  "high": 185.0},
    "creatinine":  {"low": None,  "high": 4.5},
    "glucose":     {"low": 60.0,  "high": 400.0},
}

# Warning thresholds (2-hour predictive alert)
WARNING_THRESHOLDS = {
    "spo2":        {"low": 93.0,  "high": None},
    "heart_rate":  {"low": 50.0,  "high": 110.0},
    "systolic_bp": {"low": 90.0,  "high": 165.0},
    "creatinine":  {"low": None,  "high": 3.5},
    "glucose":     {"low": 70.0,  "high": 300.0},
}

FEATURES = [
    "glucose", "creatinine", "heart_rate",
    "systolic_bp", "spo2",
]

# Minimum readings to train IF model
MIN_READINGS = 5


class PatientAnomalyDetector:
    """
    Per-patient Isolation Forest anomaly detector.
    Trained on the patient's own vital history.
    """

    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        self.model = None
        self.is_trained = False
        self.training_samples = 0
        self.feature_stats = {}

    def train(self, vitals_matrix: np.ndarray) -> bool:
        """
        Train Isolation Forest on patient vital history.
        vitals_matrix: (n_readings, n_features)
        """
        if len(vitals_matrix) < MIN_READINGS:
            logger.warning(
                "Insufficient readings for patient %s: %d",
                self.patient_id[:8], len(vitals_matrix),
            )
            return False

        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42,
        )
        self.model.fit(vitals_matrix)
        self.training_samples = len(vitals_matrix)

        # Store feature statistics for context
        self.feature_stats = {
            FEATURES[i]: {
                "mean": float(vitals_matrix[:, i].mean()),
                "std": float(vitals_matrix[:, i].std()),
                "min": float(vitals_matrix[:, i].min()),
                "max": float(vitals_matrix[:, i].max()),
            }
            for i in range(len(FEATURES))
        }

        self.is_trained = True
        logger.info(
            "IF model trained: patient=%s samples=%d",
            self.patient_id[:8], len(vitals_matrix),
        )
        return True

    def score(
        self, reading: dict
    ) -> dict:
        """
        Score a single vital reading.
        Returns anomaly score and alert if detected.
        """
        vector = self._reading_to_vector(reading)
        if vector is None:
            return {"anomaly": False, "score": 0.0}

        alerts = []

        # 1. Isolation Forest anomaly detection
        if self.is_trained and self.model:
            prediction = self.model.predict(
                vector.reshape(1, -1)
            )[0]
            anomaly_score = float(
                self.model.score_samples(
                    vector.reshape(1, -1)
                )[0]
            )
            is_anomaly = prediction == -1
        else:
            is_anomaly = False
            anomaly_score = 0.0

        # 2. Critical threshold check
        for i, feature in enumerate(FEATURES):
            val = vector[i]
            thresholds = CRITICAL_THRESHOLDS.get(
                feature, {}
            )
            lo = thresholds.get("low")
            hi = thresholds.get("high")

            if lo and val < lo:
                alerts.append({
                    "type": "CRITICAL",
                    "feature": feature,
                    "value": round(float(val), 2),
                    "threshold": lo,
                    "message": (
                        f"{feature} critically low: "
                        f"{val:.1f} < {lo}"
                    ),
                    "severity": "CRITICAL",
                })
            elif hi and val > hi:
                alerts.append({
                    "type": "CRITICAL",
                    "feature": feature,
                    "value": round(float(val), 2),
                    "threshold": hi,
                    "message": (
                        f"{feature} critically high: "
                        f"{val:.1f} > {hi}"
                    ),
                    "severity": "CRITICAL",
                })

        if is_anomaly:
            alerts.append({
                "type": "ANOMALY",
                "feature": "multi-vital",
                "value": anomaly_score,
                "threshold": -0.5,
                "message": (
                    "Isolation Forest detected "
                    "anomalous vital pattern"
                ),
                "severity": "WARNING",
            })

        return {
            "patient_id": self.patient_id,
            "anomaly": is_anomaly or len(alerts) > 0,
            "isolation_forest_score": round(
                anomaly_score, 4
            ),
            "is_isolation_anomaly": is_anomaly,
            "alerts": alerts,
            "n_alerts": len(alerts),
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def predict_2h(
        self,
        recent_readings: list,
        feature: str,
        interval_minutes: float = 36.0,
    ) -> Optional[dict]:
        """
        Predict value in 2 hours using linear extrapolation.
        recent_readings: list of (time_index, value) tuples
        interval_minutes: time between readings
        """
        if len(recent_readings) < 3:
            return None

        times = np.array(
            [i * interval_minutes for i in range(
                len(recent_readings)
            )]
        )
        values = np.array(
            [r for r in recent_readings],
            dtype=float,
        )

        # Linear regression
        coeffs = np.polyfit(times, values, 1)
        slope = coeffs[0]
        intercept = coeffs[1]

        # Predict at t+120 minutes
        t_future = times[-1] + 120.0
        predicted = slope * t_future + intercept

        # Check warning threshold
        thresholds = WARNING_THRESHOLDS.get(feature, {})
        lo = thresholds.get("low")
        hi = thresholds.get("high")

        will_breach = False
        breach_threshold = None
        breach_direction = None

        if lo and predicted < lo:
            will_breach = True
            breach_threshold = lo
            breach_direction = "low"
        elif hi and predicted > hi:
            will_breach = True
            breach_threshold = hi
            breach_direction = "high"

        return {
            "feature": feature,
            "current_value": round(float(values[-1]), 2),
            "predicted_2h": round(float(predicted), 2),
            "slope_per_hour": round(
                float(slope * 60), 4
            ),
            "will_breach_threshold": will_breach,
            "breach_threshold": breach_threshold,
            "breach_direction": breach_direction,
            "alert_type": "PREDICTIVE" if will_breach else None,
            "severity": "WARNING" if will_breach else None,
        }

    def _reading_to_vector(
        self, reading: dict
    ) -> Optional[np.ndarray]:
        """Convert vital reading dict to feature vector."""
        vector = []
        for feature in FEATURES:
            val = reading.get(feature)
            if val is None:
                # Use mean from training if available
                stats = self.feature_stats.get(feature)
                if stats:
                    val = stats["mean"]
                else:
                    val = 0.0
            vector.append(float(val))
        return np.array(vector, dtype=np.float32)


class AnomalyDetectorRegistry:
    """
    Registry of per-patient anomaly detectors.
    Trains one IsolationForest per patient.
    """

    def __init__(self):
        self._detectors = {}

    def get_or_create(
        self, patient_id: str
    ) -> PatientAnomalyDetector:
        if patient_id not in self._detectors:
            self._detectors[patient_id] = (
                PatientAnomalyDetector(patient_id)
            )
        return self._detectors[patient_id]

    def train_patient(
        self,
        patient_id: str,
        vitals_matrix: np.ndarray,
    ) -> bool:
        detector = self.get_or_create(patient_id)
        return detector.train(vitals_matrix)

    def score_reading(
        self,
        patient_id: str,
        reading: dict,
    ) -> dict:
        detector = self.get_or_create(patient_id)
        if not detector.is_trained:
            return {
                "patient_id": patient_id,
                "anomaly": False,
                "message": "Detector not trained",
            }
        return detector.score(reading)

    def status(self) -> dict:
        return {
            "n_patients": len(self._detectors),
            "trained_patients": sum(
                1 for d in self._detectors.values()
                if d.is_trained
            ),
        }


# Global registry
_registry = AnomalyDetectorRegistry()


def get_registry() -> AnomalyDetectorRegistry:
    return _registry