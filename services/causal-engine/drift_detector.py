"""
Causal Drift Detector

Monitors changes in causal effect magnitudes
over time for each patient.

A significant change in effect size means:
  - Disease progression
  - New drug interaction
  - Physiological state change

This is unique to Axiom — not just "vitals changed"
but "the CAUSAL STRUCTURE changed", which is a
much earlier and more meaningful clinical signal.
"""

import logging
import json
import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import psycopg2.extras

from db import get_conn

logger = logging.getLogger("axiom.causal.drift")

# Threshold for significant drift
# Effect must change by this fraction to alert
DRIFT_THRESHOLD = 0.25  # 25% change


class CausalDriftDetector:
    """
    Detects when a patient causal graph changes
    significantly between builds.

    Compares current graph effect sizes with
    the previous graph effect sizes and flags
    relationships that have drifted.
    """

    def detect_drift(
        self, patient_id: str
    ) -> dict:
        """
        Compare current vs previous causal graph.
        Returns drift events for changed effects.
        """
        graphs = self._get_last_two_graphs(
            patient_id
        )

        if len(graphs) < 2:
            return {
                "patient_id": patient_id,
                "drift_detected": False,
                "reason": "insufficient_history",
                "graphs_available": len(graphs),
            }

        current = graphs[0]
        previous = graphs[1]

        current_effects = current.get(
            "effect_sizes", {}
        )
        previous_effects = previous.get(
            "effect_sizes", {}
        )

        if isinstance(current_effects, str):
            current_effects = json.loads(
                current_effects
            )
        if isinstance(previous_effects, str):
            previous_effects = json.loads(
                previous_effects
            )

        drift_events = []
        all_keys = set(current_effects.keys()) | set(
            previous_effects.keys()
        )

        for key in all_keys:
            curr_entry = current_effects.get(key)
            prev_entry = previous_effects.get(key)

            # New relationship appeared
            if curr_entry and not prev_entry:
                drift_events.append({
                    "relationship": key,
                    "drift_type": "new_relationship",
                    "previous_effect": None,
                    "current_effect": curr_entry[
                        "effect"
                    ],
                    "change_pct": None,
                    "severity": "info",
                })
                continue

            # Relationship disappeared
            if prev_entry and not curr_entry:
                drift_events.append({
                    "relationship": key,
                    "drift_type": "lost_relationship",
                    "previous_effect": prev_entry[
                        "effect"
                    ],
                    "current_effect": None,
                    "change_pct": None,
                    "severity": "warning",
                })
                continue

            # Effect size changed significantly
            prev_val = prev_entry["effect"]
            curr_val = curr_entry["effect"]

            if abs(prev_val) < 1e-10:
                continue

            change_pct = abs(
                (curr_val - prev_val) / abs(prev_val)
            )

            if change_pct >= DRIFT_THRESHOLD:
                severity = (
                    "critical" if change_pct >= 1.0
                    else "warning" if change_pct >= 0.5
                    else "info"
                )
                drift_events.append({
                    "relationship": key,
                    "drift_type": "effect_changed",
                    "previous_effect": round(
                        prev_val, 4
                    ),
                    "current_effect": round(
                        curr_val, 4
                    ),
                    "change_pct": round(
                        change_pct * 100, 1
                    ),
                    "direction": (
                        "strengthened"
                        if abs(curr_val) > abs(prev_val)
                        else "weakened"
                    ),
                    "severity": severity,
                })

        # Sort by severity then change magnitude
        severity_order = {
            "critical": 0,
            "warning": 1,
            "info": 2,
        }
        drift_events.sort(
            key=lambda x: (
                severity_order.get(
                    x["severity"], 3
                ),
                -(x.get("change_pct") or 0),
            )
        )

        result = {
            "patient_id": patient_id,
            "drift_detected": len(drift_events) > 0,
            "drift_count": len(drift_events),
            "critical_count": sum(
                1 for e in drift_events
                if e["severity"] == "critical"
            ),
            "warning_count": sum(
                1 for e in drift_events
                if e["severity"] == "warning"
            ),
            "drift_events": drift_events,
            "current_graph_built": str(
                current.get("created_at", "")
            ),
            "previous_graph_built": str(
                previous.get("created_at", "")
            ),
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if drift_events:
            logger.warning(
                "DRIFT DETECTED: patient=%s "
                "events=%d critical=%d",
                patient_id[:8],
                len(drift_events),
                result["critical_count"],
            )
        else:
            logger.info(
                "No drift: patient=%s",
                patient_id[:8],
            )

        return result

    def detect_all_patients(self) -> dict:
        """
        Run drift detection for all patients
        that have at least 2 graph versions.
        """
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT patient_id
            FROM causal_graphs
            GROUP BY patient_id
            HAVING COUNT(*) >= 2
            """
        )
        patient_ids = [
            str(row[0]) for row in cursor.fetchall()
        ]
        cursor.close()
        conn.close()

        results = {
            "total_checked": len(patient_ids),
            "drift_detected": 0,
            "critical_alerts": 0,
            "patients_with_drift": [],
        }

        for pid in patient_ids:
            result = self.detect_drift(pid)
            if result.get("drift_detected"):
                results["drift_detected"] += 1
                results["critical_alerts"] += result.get(
                    "critical_count", 0
                )
                results["patients_with_drift"].append({
                    "patient_id": pid,
                    "drift_count": result[
                        "drift_count"
                    ],
                    "critical_count": result[
                        "critical_count"
                    ],
                })

        return results

    def _get_last_two_graphs(
        self, patient_id: str
    ) -> list:
        """Get the two most recent graphs."""
        conn = get_conn()
        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        cursor.execute(
            """
            SELECT *
            FROM causal_graphs
            WHERE patient_id = %s
            ORDER BY created_at DESC
            LIMIT 2
            """,
            (patient_id,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return rows