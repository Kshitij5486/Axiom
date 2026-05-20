"""
Axiom Audit Trail

Every AI recommendation is logged with:
  - The recommendation itself
  - The causal evidence (effect size, treatment, outcome)
  - The ZK proof hash
  - The doctor who received it
  - The action taken (accepted/rejected/deferred)
  - The patient outcome (if known)

Full lineage: data -> causal graph -> recommendation
              -> ZK proof -> audit log -> doctor action

HIPAA-aligned: patient_id stored as UUID,
proof hash stored for cryptographic verification.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger("axiom.audit")

DB_CONFIG = {
    "host":     "localhost",
    "port":     5439,
    "dbname":   "axiom",
    "user":     "axiom_user",
    "password": "axiom_secret",
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


class AuditTrail:
    """
    Logs every AI recommendation with full
    cryptographic lineage to PostgreSQL.
    """

    def log_recommendation(
        self,
        patient_id: str,
        doctor_id: str,
        treatment: str,
        outcome: str,
        causal_effect: float,
        confidence_low: float,
        confidence_high: float,
        zk_proof_hash: str,
        evidence: dict,
        rec_type: str = "treatment",
    ) -> dict:
        """
        Log an AI recommendation to audit_log
        and recommendations tables.
        """
        rec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        intervention = (
            f"Modify {treatment} to affect {outcome}"
        )

        try:
            conn = get_conn()
            cursor = conn.cursor()

            # Insert into recommendations
            cursor.execute(
                """
                INSERT INTO recommendations (
                    rec_id, patient_id, doctor_id,
                    rec_type, intervention,
                    causal_effect,
                    confidence_low, confidence_high,
                    evidence_json, zk_proof_hash,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    rec_id,
                    patient_id,
                    doctor_id,
                    rec_type,
                    intervention,
                    causal_effect,
                    confidence_low,
                    confidence_high,
                    json.dumps(evidence),
                    zk_proof_hash,
                    now,
                ),
            )

            # Insert into audit_log
            cursor.execute(
                """
                INSERT INTO audit_log (
                    audit_id, event_type,
                    entity_type, entity_id,
                    actor_id, actor_role,
                    details_json, zk_proof_hash,
                    occurred_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    str(uuid.uuid4()),
                    "recommendation.generated",
                    "recommendation",
                    rec_id,
                    doctor_id,
                    "ai_system",
                    json.dumps({
                        "patient_id": patient_id,
                        "treatment": treatment,
                        "outcome": outcome,
                        "causal_effect": causal_effect,
                        "zk_proof_hash": zk_proof_hash,
                    }),
                    zk_proof_hash,
                    now,
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(
                "Recommendation logged: rec_id=%s "
                "patient=%s treatment=%s->%s "
                "effect=%.4f proof=%s",
                rec_id,
                patient_id[:8],
                treatment, outcome,
                causal_effect,
                zk_proof_hash[:12],
            )

            return {
                "rec_id": rec_id,
                "logged": True,
                "zk_proof_hash": zk_proof_hash,
                "timestamp": now.isoformat(),
            }

        except Exception as e:
            logger.error(
                "Audit log failed: %s", e
            )
            return {
                "rec_id": rec_id,
                "logged": False,
                "error": str(e),
            }

    def log_doctor_action(
        self,
        rec_id: str,
        doctor_id: str,
        action: str,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Log when a doctor acts on a recommendation.
        action: accepted / rejected / deferred
        """
        now = datetime.now(timezone.utc)
        try:
            conn = get_conn()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE recommendations
                SET doctor_action = %s
                WHERE rec_id = %s
                """,
                (action, rec_id),
            )

            cursor.execute(
                """
                INSERT INTO audit_log (
                    audit_id, event_type,
                    entity_type, entity_id,
                    actor_id, actor_role,
                    details_json, occurred_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    str(uuid.uuid4()),
                    f"recommendation.{action}",
                    "recommendation",
                    rec_id,
                    doctor_id,
                    "doctor",
                    json.dumps({
                        "action": action,
                        "notes": notes,
                    }),
                    now,
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(
                "Doctor action: rec=%s action=%s "
                "doctor=%s",
                rec_id[:8], action, doctor_id,
            )

            return {
                "rec_id": rec_id,
                "action": action,
                "logged": True,
                "timestamp": now.isoformat(),
            }

        except Exception as e:
            logger.error(
                "Doctor action log failed: %s", e
            )
            return {
                "rec_id": rec_id,
                "logged": False,
                "error": str(e),
            }

    def get_patient_audit_trail(
        self,
        patient_id: str,
        limit: int = 20,
    ) -> list:
        """Get full audit trail for a patient."""
        try:
            conn = get_conn()
            cursor = conn.cursor(
                cursor_factory=(
                    psycopg2.extras.RealDictCursor
                )
            )
            cursor.execute(
                """
                SELECT
                    r.rec_id,
                    r.intervention,
                    r.causal_effect,
                    r.confidence_low,
                    r.confidence_high,
                    r.zk_proof_hash,
                    r.doctor_action,
                    r.created_at,
                    r.doctor_id
                FROM recommendations r
                WHERE r.patient_id = %s
                ORDER BY r.created_at DESC
                LIMIT %s
                """,
                (patient_id, limit),
            )
            rows = [
                dict(r) for r in cursor.fetchall()
            ]
            cursor.close()
            conn.close()
            return rows
        except Exception as e:
            logger.error(
                "Audit trail fetch failed: %s", e
            )
            return []

    def get_recent_audit_events(
        self, limit: int = 50
    ) -> list:
        """Get recent audit log events."""
        try:
            conn = get_conn()
            cursor = conn.cursor(
                cursor_factory=(
                    psycopg2.extras.RealDictCursor
                )
            )
            cursor.execute(
                """
                SELECT
                    audit_id, event_type,
                    entity_type, entity_id,
                    actor_id, actor_role,
                    zk_proof_hash, occurred_at
                FROM audit_log
                ORDER BY occurred_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = [
                dict(r) for r in cursor.fetchall()
            ]
            cursor.close()
            conn.close()
            return rows
        except Exception as e:
            logger.error(
                "Audit events fetch failed: %s", e
            )
            return []