"""
Causal Engine Kafka Consumer

Listens to patient.vitals.normalised topic.
When new vitals arrive for a patient,
triggers causal graph rebuild for that patient.

This makes Axiom reactive:
  New vital arrives
    -> consumer receives it
    -> checks if enough time has passed
       since last rebuild (cooldown)
    -> rebuilds causal graph
    -> runs drift detection
    -> publishes causal.updates event
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

from causal_graph_builder import PatientCausalGraphBuilder
from drift_detector import CausalDriftDetector

logger = logging.getLogger("axiom.causal.consumer")

KAFKA_BOOTSTRAP = "localhost:9094"
CONSUME_TOPIC   = "patient.vitals.normalised"
PUBLISH_TOPIC   = "causal.updates"

# Minimum seconds between rebuilds per patient
# Prevents excessive rebuilding on burst of vitals
REBUILD_COOLDOWN_SECONDS = 60


class CausalKafkaConsumer:
    """
    Kafka consumer that triggers causal graph
    rebuilds when new patient vitals arrive.
    """

    def __init__(self):
        self._running = False
        self._messages_consumed = 0
        self._rebuilds_triggered = 0
        self._rebuilds_completed = 0
        self._drift_events = 0
        self._start_time = time.time()

        # Track last rebuild time per patient
        # to enforce cooldown
        self._last_rebuild: dict = {}
        self._lock = threading.Lock()

        self._builder = PatientCausalGraphBuilder()
        self._drift_detector = CausalDriftDetector()
        self._producer = None

    def _get_producer(self):
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=[KAFKA_BOOTSTRAP],
                    value_serializer=lambda x:
                        json.dumps(x).encode("utf-8"),
                )
            except Exception as e:
                logger.error(
                    "Kafka producer failed: %s", e
                )
        return self._producer

    def _should_rebuild(
        self, patient_id: str
    ) -> bool:
        """Check cooldown before rebuilding."""
        with self._lock:
            last = self._last_rebuild.get(
                patient_id, 0
            )
            elapsed = time.time() - last
            if elapsed >= REBUILD_COOLDOWN_SECONDS:
                self._last_rebuild[patient_id] = (
                    time.time()
                )
                return True
            return False

    def _process_vital_event(
        self, event: dict
    ):
        """
        Process a single vital event.
        Rebuild causal graph if cooldown passed.
        """
        patient_id = event.get("patient_id")
        if not patient_id:
            return

        self._messages_consumed += 1

        if not self._should_rebuild(patient_id):
            return

        self._rebuilds_triggered += 1
        logger.info(
            "Rebuilding graph: patient=%s "
            "trigger=new_vital",
            str(patient_id)[:8],
        )

        try:
            # Rebuild causal graph
            graph = self._builder.build_causal_graph(
                str(patient_id)
            )
            self._rebuilds_completed += 1

            # Run drift detection
            drift = self._drift_detector.detect_drift(
                str(patient_id)
            )

            if drift.get("drift_detected"):
                self._drift_events += 1
                logger.warning(
                    "DRIFT after rebuild: "
                    "patient=%s events=%d",
                    str(patient_id)[:8],
                    drift.get("drift_count", 0),
                )

            # Publish causal update event
            producer = self._get_producer()
            if producer:
                update_event = {
                    "event_type": "causal.graph.updated",
                    "patient_id": str(patient_id),
                    "graph_id": graph.get("graph_id"),
                    "effect_count": graph.get(
                        "effect_count", 0
                    ),
                    "drift_detected": drift.get(
                        "drift_detected", False
                    ),
                    "drift_count": drift.get(
                        "drift_count", 0
                    ),
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                producer.send(
                    PUBLISH_TOPIC,
                    value=update_event,
                    key=str(patient_id).encode(),
                )
                logger.info(
                    "Published causal.updates: "
                    "patient=%s effects=%d",
                    str(patient_id)[:8],
                    graph.get("effect_count", 0),
                )

        except Exception as e:
            logger.error(
                "Rebuild failed patient=%s: %s",
                str(patient_id)[:8], e,
            )

    def start(self):
        """Start consuming in background thread."""
        t = threading.Thread(
            target=self._consume_loop,
            daemon=True,
            name="causal-kafka-consumer",
        )
        t.start()
        logger.info(
            "Causal Kafka consumer started "
            "topic=%s cooldown=%ds",
            CONSUME_TOPIC,
            REBUILD_COOLDOWN_SECONDS,
        )

    def _consume_loop(self):
        """Main consumer loop with retry logic."""
        consumer = None

        for attempt in range(10):
            try:
                consumer = KafkaConsumer(
                    CONSUME_TOPIC,
                    bootstrap_servers=[
                        KAFKA_BOOTSTRAP
                    ],
                    group_id="causal-engine",
                    value_deserializer=lambda x:
                        json.loads(x.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    consumer_timeout_ms=1000,
                )
                logger.info(
                    "Kafka consumer connected "
                    "attempt=%d", attempt + 1,
                )
                break
            except NoBrokersAvailable:
                logger.warning(
                    "Kafka not ready, retry %d/10",
                    attempt + 1,
                )
                time.sleep(5)

        if consumer is None:
            logger.error(
                "Could not connect to Kafka"
            )
            return

        self._running = True
        logger.info(
            "Consuming from %s", CONSUME_TOPIC
        )

        while self._running:
            try:
                for message in consumer:
                    if not self._running:
                        break
                    self._process_vital_event(
                        message.value
                    )
            except Exception as e:
                if self._running:
                    logger.error(
                        "Consumer error: %s", e
                    )
                    time.sleep(5)

    def stop(self):
        self._running = False
        logger.info("Causal consumer stopped")

    def status(self) -> dict:
        return {
            "running": self._running,
            "messages_consumed": (
                self._messages_consumed
            ),
            "rebuilds_triggered": (
                self._rebuilds_triggered
            ),
            "rebuilds_completed": (
                self._rebuilds_completed
            ),
            "drift_events": self._drift_events,
            "uptime_seconds": round(
                time.time() - self._start_time, 1
            ),
        }