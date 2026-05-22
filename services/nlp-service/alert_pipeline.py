"""
Alert Pipeline

When an anomaly is detected:
  1. Save alert to MongoDB alert_history
  2. Publish to Kafka alerts.clinical topic
  3. Generate ZK proof for the alert
  4. Broadcast via WebSocket to connected clients

This creates a complete audit trail for every alert
with cryptographic proof — a doctor can verify
an alert was genuine and not fabricated.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

import requests
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logger = logging.getLogger("axiom.nlp.alert_pipeline")

KAFKA_BOOTSTRAP = "localhost:9094"
ALERT_TOPIC = "alerts.clinical"
ZK_URL = "http://localhost:8084"


class AlertPipeline:
    """
    Processes anomaly alerts through the full pipeline:
    MongoDB → Kafka → ZK proof → WebSocket
    """

    def __init__(self):
        self._producer = None
        self._producer_lock = threading.Lock()
        self._alerts_sent = 0
        self._zk_proofs_generated = 0

    def _get_producer(self) -> Optional[object]:
        with self._producer_lock:
            if self._producer is None:
                try:
                    self._producer = KafkaProducer(
                        bootstrap_servers=[KAFKA_BOOTSTRAP],
                        value_serializer=lambda x:
                            json.dumps(x).encode("utf-8"),
                    )
                    logger.info(
                        "Kafka producer connected"
                    )
                except NoBrokersAvailable:
                    logger.warning(
                        "Kafka unavailable for alerts"
                    )
            return self._producer

    def _generate_zk_proof(
        self,
        patient_id: str,
        alert_type: str,
        feature: str,
        value: float,
    ) -> Optional[str]:
        """Generate ZK proof for an alert."""
        try:
            response = requests.post(
                f"{ZK_URL}/zk/proof/recommendation",
                json={
                    "patient_id": patient_id,
                    "recommendation": (
                        f"ALERT: {alert_type} "
                        f"on {feature}"
                    ),
                    "causal_effect": float(value),
                    "graph_id": "anomaly-detector-v1",
                    "treatment": feature,
                    "outcome": "patient_safety",
                },
                timeout=5,
            )
            response.raise_for_status()
            proof_hash = response.json().get(
                "proof_hash"
            )
            self._zk_proofs_generated += 1
            return proof_hash
        except Exception as e:
            logger.warning(
                "ZK proof failed for alert: %s", e
            )
            return None

    def _publish_to_kafka(self, alert: dict):
        """Publish alert to Kafka alerts.clinical."""
        producer = self._get_producer()
        if producer:
            try:
                producer.send(
                    ALERT_TOPIC,
                    value=alert,
                    key=alert.get(
                        "patient_id", "unknown"
                    ).encode(),
                )
                producer.flush()
                logger.info(
                    "Alert published to Kafka: "
                    "patient=%s type=%s",
                    alert.get(
                        "patient_id", "?"
                    )[:8],
                    alert.get("alert_type"),
                )
            except Exception as e:
                logger.error(
                    "Kafka publish failed: %s", e
                )

    def process_alerts(
        self,
        patient_id: str,
        alerts: list,
        predictive_alerts: list = None,
        websocket_clients: list = None,
    ) -> list:
        """
        Process all alerts for a patient through
        the full pipeline.

        Returns list of processed alert records.
        """
        from db import save_alert
        processed = []
        all_alerts = list(alerts)

        if predictive_alerts:
            for pred in predictive_alerts:
                if pred.get("will_breach_threshold"):
                    all_alerts.append({
                        "type": "PREDICTIVE",
                        "feature": pred["feature"],
                        "value": pred["current_value"],
                        "threshold": pred[
                            "breach_threshold"
                        ],
                        "message": (
                            f"PREDICTIVE: "
                            f"{pred['feature']} "
                            f"predicted to breach "
                            f"{pred['breach_threshold']}"
                            f" in <2h "
                            f"(current: "
                            f"{pred['current_value']}, "
                            f"predicted: "
                            f"{pred['predicted_2h']})"
                        ),
                        "severity": "WARNING",
                        "predicted_value_2h": pred[
                            "predicted_2h"
                        ],
                    })

        for alert in all_alerts:
            alert_type = alert.get("type", "UNKNOWN")
            feature = alert.get(
                "feature", "unknown"
            )
            value = alert.get("value", 0.0)
            threshold = alert.get("threshold", 0.0)
            severity = alert.get(
                "severity", "WARNING"
            )
            message = alert.get("message", "")

            # Generate ZK proof
            zk_proof = self._generate_zk_proof(
                patient_id=patient_id,
                alert_type=alert_type,
                feature=feature,
                value=float(value),
            )

            # Save to MongoDB
            alert_id = save_alert(
                patient_id=patient_id,
                alert_type=alert_type,
                feature=feature,
                current_value=float(value),
                threshold=float(threshold),
                severity=severity,
                message=message,
                zk_proof_hash=zk_proof,
            )

            # Build full alert record
            alert_record = {
                "alert_id": alert_id,
                "patient_id": patient_id,
                "alert_type": alert_type,
                "feature": feature,
                "current_value": float(value),
                "threshold": float(threshold),
                "severity": severity,
                "message": message,
                "zk_proof_hash": zk_proof,
                "zk_proven": zk_proof is not None,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            if "predicted_value_2h" in alert:
                alert_record["predicted_value_2h"] = (
                    alert["predicted_value_2h"]
                )

            # Publish to Kafka
            self._publish_to_kafka(alert_record)

            # WebSocket broadcast
            if websocket_clients:
                import asyncio
                for client in websocket_clients:
                    try:
                        asyncio.create_task(
                            client.send_text(
                                json.dumps(alert_record)
                            )
                        )
                    except Exception:
                        pass

            processed.append(alert_record)
            self._alerts_sent += 1

            logger.warning(
                "ALERT: patient=%s type=%s "
                "feature=%s value=%s "
                "severity=%s zk=%s",
                patient_id[:8],
                alert_type, feature,
                value, severity,
                zk_proof[:12] if zk_proof else "None",
            )

        return processed

    def status(self) -> dict:
        return {
            "alerts_sent": self._alerts_sent,
            "zk_proofs_generated": (
                self._zk_proofs_generated
            ),
            "kafka_connected": (
                self._producer is not None
            ),
        }


_pipeline = AlertPipeline()


def get_pipeline() -> AlertPipeline:
    return _pipeline