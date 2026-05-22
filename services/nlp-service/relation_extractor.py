"""
Relation Extractor

Extracts causal relationships from clinical text
using dependency grammar patterns.

Output relations feed directly into the per-patient
causal DAG via incremental EWMA update (Day 39).

Patterns:
  CAUSES:    "X after Y", "X due to Y", "Y caused X"
  IMPROVES:  "X improved after Y", "Y reduced X"
  WORSENS:   "X worsened with Y", "Y increased X"
  CORRELATES: "X with Y", "X associated with Y"

Entity mapping:
  Extracted entity -> causal graph feature name
  "furosemide"  -> causal effect on "creatinine"
  "lisinopril"  -> causal effect on "systolic_bp"
  "metformin"   -> causal effect on "glucose"
"""

import re
import logging
from typing import List, Dict

from clinical_dictionary import (
    CONDITIONS, DRUGS, SYMPTOMS
)

logger = logging.getLogger("axiom.nlp.relations")

# Map drug/condition names to causal graph features
ENTITY_TO_FEATURE = {
    # Drugs -> their primary target
    "furosemide":    "creatinine",
    "lisinopril":    "systolic_bp",
    "metformin":     "glucose",
    "aspirin":       "heart_rate",
    "atorvastatin":  "total_cholesterol",
    "insulin":       "glucose",
    "salbutamol":    "spo2",
    "prednisolone":  "glucose",
    "ramipril":      "systolic_bp",
    "amlodipine":    "systolic_bp",
    "bisoprolol":    "heart_rate",
    "carvedilol":    "heart_rate",
    "spironolactone": "creatinine",

    # Conditions -> their primary biomarker
    "diabetes_mellitus":     "glucose",
    "hypertension":          "systolic_bp",
    "heart_failure":         "spo2",
    "chronic_kidney_disease": "creatinine",
    "copd":                  "spo2",
    "anaemia":               "hemoglobin",
    "hyperglycaemia":        "glucose",

    # Direct feature mentions
    "glucose":      "glucose",
    "creatinine":   "creatinine",
    "blood_pressure": "systolic_bp",
    "heart_rate":   "heart_rate",
    "spo2":         "spo2",
    "dyspnoea":     "spo2",
    "oedema":       "creatinine",
}

# Simpler targeted patterns added Day 38
SIMPLE_PATTERNS = [
    # "X rose after Y" / "X increased after Y"
    (r"(\w+)\s+(?:rose|increased|elevated|worsened)\s+after\s+([\w\s]+?)(?:\.|,)", 2, 1, "causes", 0.75),
    # "Y improved X" / "Y reduced X" / "Y lowered X"
    (r"([\w]+)\s+(?:improved|reduced|lowered|controlled|decreased)\s+([\w\s]+?)(?:\.|,|to\s)", 1, 2, "improves", 0.75),
    # "X worsening with Y"
    (r"(\w+)\s+worsening\s+with\s+([\w\s]+?)(?:\.|,)", 2, 1, "worsens", 0.65),
]
# Causal relation patterns
# Each: (regex, cause_group, effect_group, direction)
CAUSAL_PATTERNS = [
    # "X developed/rose/increased after Y"
    (
        r"(\w[\w\s]+?)\s+"
        r"(?:developed|rose|increased|worsened|elevated)"
        r"\s+(?:after|following|due to|secondary to)\s+"
        r"([\w\s]+?)(?:\.|,|$)",
        2, 1, "causes", 0.75,
    ),
    # "Y caused/induced X"
    (
        r"([\w\s]+?)\s+"
        r"(?:caused|induced|triggered|led to|resulted in)\s+"
        r"([\w\s]+?)(?:\.|,|$)",
        1, 2, "causes", 0.80,
    ),
    # "X improved/decreased after/following Y"
    (
        r"([\w\s]+?)\s+"
        r"(?:improved|decreased|reduced|fell|dropped)"
        r"\s+(?:after|following|with)\s+"
        r"([\w\s]+?)(?:\.|,|$)",
        2, 1, "improves", 0.75,
    ),
    # "Y improved/reduced X"
    (
        r"([\w\s]+?)\s+"
        r"(?:improved|reduced|lowered|controlled)\s+"
        r"([\w\s]+?)(?:\.|,|$)",
        1, 2, "improves", 0.70,
    ),
    # "X worsening with Y"
    (
        r"([\w\s]+?)\s+"
        r"(?:worsening|worsened|deteriorating)\s+"
        r"(?:with|alongside|despite)\s+"
        r"([\w\s]+?)(?:\.|,|$)",
        2, 1, "worsens", 0.65,
    ),
    # "poorly compliant with Y" → Y not working
    (
        r"poorly\s+(?:compliant|controlled)\s+"
        r"(?:with|on)\s+([\w\s]+?)(?:\.|,|$)",
        None, 1, "non_compliant", 0.60,
    ),
]

# Direction to effect sign mapping
DIRECTION_TO_SIGN = {
    "causes":       +1,
    "worsens":      +1,
    "improves":     -1,

    "non_compliant": 0,
}

# Simpler direct patterns (added Day 38)
SIMPLE_PATTERNS = [
    (r"(\w+)\s+(?:rose|increased|elevated)\s+after\s+([\w\s]+?)(?:\.|,)", 2, 1, "causes", 0.75),
    (r"([\w]+)\s+(?:improved|reduced|lowered|controlled|decreased)\s+([\w\s]+?)(?:\.|,|to\s)", 1, 2, "improves", 0.75),
    (r"(\w+)\s+worsening\s+with\s+([\w\s]+?)(?:\.|,)", 2, 1, "worsens", 0.65),
    (r"([\w]+)\s+(?:caused|induced|triggered)\s+([\w\s]+?)(?:\.|,)", 1, 2, "causes", 0.80),
]


def _normalize_entity(text: str) -> str:
    """Clean and normalize entity text."""
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    # Remove common stop words
    for stop in [
        "the", "a", "an", "patient", "his", "her",
        "their", "with", "of", "in", "on", "and",
    ]:
        text = re.sub(
            r'\b' + stop + r'\b', '', text
        ).strip()
    return text.strip()


def _entity_to_feature(entity: str) -> str:
    """Map entity text to causal graph feature.
    
    For CAUSE entities: return drug/condition name
    For EFFECT entities: return the feature name
    Context-free: caller must interpret.
    """
    entity_clean = _normalize_entity(entity)

    # Direct lookup in feature map
    if entity_clean in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[entity_clean]

    # Drug match: return the drug canonical name
    # (NOT its target feature - caller decides context)
    for drug, canonical in DRUGS.items():
        if drug in entity_clean:
            return canonical

    # Condition match: return feature
    for cond, canonical in CONDITIONS.items():
        if cond in entity_clean:
            return ENTITY_TO_FEATURE.get(canonical, canonical)

    # First word match
    first_word = entity_clean.split()[0] if entity_clean else ""
    if first_word in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[first_word]

    return entity_clean.replace(" ", "_")


def extract_relations(
    text: str,
    entities: List[Dict] = None,
) -> List[Dict]:
    """
    Extract causal relations from clinical text.

    Returns list of relation dicts:
    {
        "cause":      feature name,
        "effect":     feature name,
        "direction":  "causes|improves|worsens",
        "sign":       +1 or -1,
        "confidence": float,
        "evidence":   original text snippet,
        "nlp_effect": float (for EWMA update),
    }
    """
    relations = []
    text_lower = text.lower()

    all_patterns = SIMPLE_PATTERNS + CAUSAL_PATTERNS
    for pattern, cause_grp, effect_grp, direction, confidence in all_patterns:
        for match in re.finditer(
            pattern, text_lower, re.IGNORECASE
        ):
            try:
                cause_text = (
                    match.group(cause_grp).strip()
                    if cause_grp else None
                )
                effect_text = match.group(
                    effect_grp
                ).strip()

                cause_feature = (
                    _entity_to_feature(cause_text)
                    if cause_text else None
                )
                effect_feature = _entity_to_feature(
                    effect_text
                )

                if not effect_feature:
                    continue

                sign = DIRECTION_TO_SIGN.get(
                    direction, 0
                )

                # NLP effect estimate
                # Small magnitude, weighted by confidence
                nlp_effect = sign * 0.05 * confidence

                relation = {
                    "cause": cause_feature,
                    "effect": effect_feature,
                    "direction": direction,
                    "sign": sign,
                    "confidence": confidence,
                    "evidence": match.group(0)[:100],
                    "nlp_effect": round(nlp_effect, 4),
                    "edge_key": (
                        f"{cause_feature}->{effect_feature}"
                        if cause_feature
                        else f"?->{effect_feature}"
                    ),
                }
                relations.append(relation)

            except (IndexError, AttributeError):
                continue

    # Filter: keep relations where effect is a known
    # clinical feature and cause != effect
    known_features = set(ENTITY_TO_FEATURE.values())
    known_drugs = set(DRUGS.values())
    all_known = known_features | known_drugs
    filtered = []
    for rel in relations:
        cause = rel.get("cause")
        effect = rel.get("effect")
        if (
            effect in known_features
            and cause != effect
            and (cause is None or cause in all_known
                 or len(cause) > 2)
        ):
            filtered.append(rel)

    logger.info(
        "Relation extraction: %d patterns matched, "
        "%d valid relations",
        len(relations), len(filtered),
    )

    return filtered


def extract_relations_from_note(
    note: dict,
    entities: List[Dict] = None,
) -> Dict:
    """Extract relations from a clinical note dict."""
    content = note.get("content", "")
    patient_id = note.get("patient_id", "unknown")

    relations = extract_relations(content, entities)

    logger.info(
        "Note relations: patient=%s "
        "relations=%d",
        patient_id[:8] if len(patient_id) > 8
        else patient_id,
        len(relations),
    )

    return {
        "patient_id": patient_id,
        "note_type": note.get("note_type", "unknown"),
        "relations": relations,
        "n_relations": len(relations),
    }