"""
Incremental DAG Updater

Updates per-patient causal graph effect sizes
using NLP-extracted relations via EWMA.

Does NOT rebuild the full DoWhy graph (20 seconds).
Instead updates individual edge weights in <10ms.

EWMA formula:
  new_effect = alpha * nlp_effect + (1-alpha) * old_effect
  alpha = 0.3  (NLP weighted less than DoWhy data evidence)

Why alpha=0.3:
  DoWhy computes effects from actual patient vitals.
  NLP extracts from free text which is noisier.
  We trust data more than text, but text adds signal
  not available in structured data (drug compliance,
  temporal context, doctor observations).

New edges (not in DoWhy graph):
  Directly added with nlp_effect as initial value.
  Flagged as nlp_source=True for transparency.
"""

import logging
import json
from datetime import datetime, timezone
from typing import List, Dict

logger = logging.getLogger("axiom.nlp.dag_updater")

ALPHA = 0.3  # NLP weight in EWMA


def update_causal_graph(
    patient_id: str,
    relations: List[Dict],
    dry_run: bool = False,
) -> dict:
    """
    Update causal graph effect sizes with NLP relations.

    Args:
        patient_id: patient UUID
        relations:  list of extracted relations
        dry_run:    if True, compute but don't save

    Returns:
        Summary of updates made
    """
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        "nlp_db",
        os.path.join(os.path.dirname(__file__), "db.py")
    )
    nlp_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nlp_db)
    get_current_causal_effects = nlp_db.get_current_causal_effects
    update_causal_graph_effects = nlp_db.update_causal_graph_effects

    if not relations:
        return {
            "patient_id": patient_id,
            "updates": 0,
            "new_edges": 0,
            "message": "No relations to update",
        }

    # Load current effects
    current_effects = get_current_causal_effects(
        patient_id
    )

    if not current_effects:
        logger.warning(
            "No causal graph for patient %s",
            patient_id[:8],
        )
        return {
            "patient_id": patient_id,
            "updates": 0,
            "new_edges": 0,
            "message": "No causal graph found. "
                       "Build graph first.",
        }

    updated_effects = dict(current_effects)
    updates = []
    new_edges = []

    # Deduplicate relations by edge_key
    seen_keys = set()
    unique_relations = []
    for rel in relations:
        key = rel.get("edge_key", "")
        if key and key not in seen_keys:
            seen_keys.add(key)
            unique_relations.append(rel)

    for rel in unique_relations:
        cause = rel.get("cause")
        effect = rel.get("effect")
        nlp_effect = rel.get("nlp_effect", 0.0)
        confidence = rel.get("confidence", 0.5)
        direction = rel.get("direction", "causes")

        if not cause or not effect:
            continue

        edge_key = f"{cause}->{effect}"

        # Check if edge exists in current graph
        if edge_key in updated_effects:
            # EWMA update
            current = updated_effects[edge_key]
            if isinstance(current, dict):
                old_effect = float(
                    current.get("effect", 0.0)
                )
                new_effect = (
                    ALPHA * nlp_effect
                    + (1 - ALPHA) * old_effect
                )
                updated_effects[edge_key] = {
                    **current,
                    "effect": round(new_effect, 6),
                    "nlp_updated": True,
                    "nlp_effect": round(nlp_effect, 6),
                    "nlp_confidence": confidence,
                    "nlp_direction": direction,
                    "updated_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                updates.append({
                    "edge": edge_key,
                    "old_effect": round(old_effect, 6),
                    "nlp_effect": round(nlp_effect, 6),
                    "new_effect": round(new_effect, 6),
                    "alpha": ALPHA,
                })
                logger.info(
                    "EWMA update: %s "
                    "%.4f -> %.4f (nlp=%.4f)",
                    edge_key,
                    old_effect,
                    new_effect,
                    nlp_effect,
                )
            else:
                old_effect = float(current)
                new_effect = (
                    ALPHA * nlp_effect
                    + (1 - ALPHA) * old_effect
                )
                updated_effects[edge_key] = round(
                    new_effect, 6
                )
                updates.append({
                    "edge": edge_key,
                    "old_effect": round(old_effect, 6),
                    "nlp_effect": round(nlp_effect, 6),
                    "new_effect": round(new_effect, 6),
                })
        else:
            # New edge from NLP
            updated_effects[edge_key] = {
                "effect": round(nlp_effect, 6),
                "treatment": cause,
                "outcome": effect,
                "samples": 0,
                "nlp_source": True,
                "nlp_confidence": confidence,
                "nlp_direction": direction,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            new_edges.append({
                "edge": edge_key,
                "nlp_effect": round(nlp_effect, 6),
                "confidence": confidence,
            })
            logger.info(
                "New NLP edge: %s effect=%.4f",
                edge_key, nlp_effect,
            )

    # Save to PostgreSQL
    if not dry_run and (updates or new_edges):
        success = update_causal_graph_effects(
            patient_id, updated_effects
        )
        if not success:
            return {
                "patient_id": patient_id,
                "error": "Failed to save updates",
                "updates": len(updates),
                "new_edges": len(new_edges),
            }

    result = {
        "patient_id": patient_id,
        "updates": len(updates),
        "new_edges": len(new_edges),
        "total_changes": len(updates) + len(new_edges),
        "alpha": ALPHA,
        "dry_run": dry_run,
        "ewma_updates": updates,
        "new_nlp_edges": new_edges,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    logger.info(
        "DAG updated: patient=%s updates=%d new=%d",
        patient_id[:8],
        len(updates),
        len(new_edges),
    )

    return result