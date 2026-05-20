import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from fastapi import FastAPI
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

from loinc_mapper import loinc_to_feature, is_abnormal
from snomed_mapper import snomed_to_condition
from unit_converter import convert_unit, get_standard_unit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.normalisation")

app = FastAPI(
    title="Axiom Normalisation Service",
    version="1.0.0",
)

# State
_consumer_running = False
_messages_processed = 0
_messages_failed = 0
_start_time = time.time()


def get_db_conn():
    return psycopg2.connect(
        host="localhost",
        port=5439,
        dbname="axiom",
        user="axiom_user",
        password="axiom_secret",
    )


def normalise_vital_event(raw: dict) -> dict:
    """
    Normalise a raw vital/lab event from FHIR adapter.
    - Map LOINC code to feature name
    - Convert units to standard
    - Flag abnormal values
    - Add normalisation metadata
    """
    loinc_code = raw.get("code", "")
    feature_name = loinc_to_feature(loinc_code)

    value = raw.get("value")
    unit = raw.get("unit", "")

    # Unit conversion
    value_normalised, unit_standard = convert_unit(
        feature_name, float(value) if value else 0.0, unit
    )

    # Abnormality check
    abnormal = is_abnormal(feature_name, value_normalised)

    normalised = {
        **raw,
        "feature_name": feature_name,
        "value_normalised": value_normalised,
        "unit_standard": unit_standard,
        "is_abnormal": abnormal,
        "normalised_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "normalised": True,
    }

    if abnormal:
        logger.warning(
            "ABNORMAL: patient=%s feature=%s "
            "value=%.2f %s",
            raw.get("patient_id", "unknown"),
            feature_name,
            value_normalised,
            unit_standard,
        )

    return normalised


def update_observation_in_db(normalised: dict):
    """Update observation with normalised values."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE observations
            SET feature_name    = %s,
                value_quantity  = %s,
                unit            = %s,
                is_abnormal     = %s
            WHERE patient_id = %s
              AND code = %s
              AND recorded_at = (
                  SELECT MAX(recorded_at)
                  FROM observations
                  WHERE patient_id = %s
                    AND code = %s
              )
            """,
            (
                normalised.get("feature_name"),
                normalised.get("value_normalised"),
                normalised.get("unit_standard"),
                normalised.get("is_abnormal"),
                normalised.get("patient_id"),
                normalised.get("code"),
                normalised.get("patient_id"),
                normalised.get("code"),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error("DB update failed: %s", e)


def consume_and_normalise():
    global _consumer_running, _messages_processed, _messages_failed

    logger.info(
        "Normalisation consumer starting..."
    )

    # Retry Kafka connection
    consumer = None
    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                "patient.vitals",
                "patient.labs",
                bootstrap_servers=["localhost:9094"],
                group_id="normalisation-service",
                value_deserializer=lambda x: json.loads(
                    x.decode("utf-8")
                ),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            logger.info("Kafka consumer connected")
            break
        except NoBrokersAvailable:
            logger.warning(
                "Kafka not ready, retry %d/10...",
                attempt + 1,
            )
            time.sleep(5)

    if consumer is None:
        logger.error(
            "Could not connect to Kafka after 10 attempts"
        )
        return

    producer = KafkaProducer(
        bootstrap_servers=["localhost:9094"],
        value_serializer=lambda x: json.dumps(
            x
        ).encode("utf-8"),
    )

    _consumer_running = True
    logger.info(
        "Consuming from: patient.vitals, patient.labs"
    )

    for message in consumer:
        try:
            raw = message.value
            normalised = normalise_vital_event(raw)

            # Publish normalised event
            producer.send(
                f"{message.topic}.normalised",
                value=normalised,
                key=str(
                    raw.get("patient_id", "unknown")
                ).encode(),
            )

            # Update DB
            update_observation_in_db(normalised)

            _messages_processed += 1

            logger.info(
                "Normalised: patient=%s "
                "feature=%s value=%.2f %s "
                "abnormal=%s",
                normalised.get("patient_id", "?"),
                normalised.get("feature_name"),
                normalised.get("value_normalised", 0),
                normalised.get("unit_standard"),
                normalised.get("is_abnormal"),
            )

        except Exception as e:
            _messages_failed += 1
            logger.error(
                "Normalisation failed: %s", e
            )


@app.on_event("startup")
async def startup():
    t = threading.Thread(
        target=consume_and_normalise, daemon=True
    )
    t.start()
    logger.info(
        "Normalisation service started on port 8086"
    )


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-normalisation",
        "version": "1.0.0",
        "consumer_running": _consumer_running,
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/stats")
def stats():
    return {
        "messages_processed": _messages_processed,
        "messages_failed": _messages_failed,
        "consumer_running": _consumer_running,
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
    }


@app.post("/normalise")
def normalise_single(payload: dict):
    """Normalise a single observation payload."""
    try:
        result = normalise_vital_event(payload)
        return {"status": "ok", "normalised": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, host="0.0.0.0", port=8086
    )