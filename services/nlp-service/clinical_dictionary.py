"""
Clinical Dictionary NER

Fast rule-based named entity recognition using
clinical dictionaries. Production-quality output
format identical to BioBERT NER.

Used as:
  1. Primary extractor when BioBERT not loaded
  2. Validation layer after BioBERT extractions
  3. Vital value extraction (regex patterns)

Dictionaries sourced from:
  SNOMED-CT (conditions subset)
  RxNorm (drug names subset)
  LOINC (lab/vital terms subset)
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger("axiom.nlp.dictionary")

# ── Condition dictionary (SNOMED-CT subset) ────────
CONDITIONS = {
    # Metabolic
    "diabetes": "diabetes_mellitus",
    "diabetes mellitus": "diabetes_mellitus",
    "type 2 diabetes": "diabetes_mellitus_type2",
    "diabetic": "diabetes_mellitus",
    "hyperglycaemia": "hyperglycaemia",
    "hyperglycemia": "hyperglycaemia",
    "hypoglycaemia": "hypoglycaemia",
    "hypoglycemia": "hypoglycaemia",

    # Cardiovascular
    "hypertension": "hypertension",
    "high blood pressure": "hypertension",
    "heart failure": "heart_failure",
    "cardiac failure": "heart_failure",
    "atrial fibrillation": "atrial_fibrillation",
    "af": "atrial_fibrillation",
    "myocardial infarction": "myocardial_infarction",
    "heart attack": "myocardial_infarction",
    "angina": "angina",

    # Renal
    "chronic kidney disease": "chronic_kidney_disease",
    "ckd": "chronic_kidney_disease",
    "renal failure": "renal_failure",
    "renal impairment": "renal_impairment",
    "nephropathy": "nephropathy",

    # Respiratory
    "copd": "copd",
    "chronic obstructive pulmonary disease": "copd",
    "asthma": "asthma",
    "dyspnea": "dyspnoea",
    "dyspnoea": "dyspnoea",
    "shortness of breath": "dyspnoea",
    "breathlessness": "dyspnoea",

    # Other
    "anaemia": "anaemia",
    "anemia": "anaemia",
    "stroke": "stroke",
    "oedema": "oedema",
    "edema": "oedema",
    "hyperlipidaemia": "hyperlipidaemia",
    "hyperlipidemia": "hyperlipidaemia",
}

# ── Drug dictionary (RxNorm subset) ───────────────
DRUGS = {
    "metformin": "metformin",
    "lisinopril": "lisinopril",
    "furosemide": "furosemide",
    "frusemide": "furosemide",
    "atorvastatin": "atorvastatin",
    "aspirin": "aspirin",
    "amlodipine": "amlodipine",
    "ramipril": "ramipril",
    "warfarin": "warfarin",
    "insulin": "insulin",
    "salbutamol": "salbutamol",
    "albuterol": "salbutamol",
    "omeprazole": "omeprazole",
    "prednisolone": "prednisolone",
    "methylprednisolone": "methylprednisolone",
    "amoxicillin": "amoxicillin",
    "paracetamol": "paracetamol",
    "acetaminophen": "paracetamol",
    "ibuprofen": "ibuprofen",
    "spironolactone": "spironolactone",
    "bisoprolol": "bisoprolol",
    "carvedilol": "carvedilol",
    "digoxin": "digoxin",
    "clopidogrel": "clopidogrel",
    "simvastatin": "simvastatin",
}

# ── Vital sign patterns (regex) ────────────────────
VITAL_PATTERNS = [
    # Blood pressure: "BP 158/92" or "158/92 mmHg"
    (
        r"\bBP\s+(\d{2,3})/(\d{2,3})\b",
        "blood_pressure",
        lambda m: f"{m.group(1)}/{m.group(2)} mmHg",
    ),
    (
        r"\b(\d{2,3})/(\d{2,3})\s*mmHg\b",
        "blood_pressure",
        lambda m: f"{m.group(1)}/{m.group(2)} mmHg",
    ),
    # Heart rate: "HR 98" or "heart rate 98"
    (
        r"\bHR\s+(\d{2,3})\b",
        "heart_rate",
        lambda m: f"{m.group(1)} bpm",
    ),
    (
        r"\bheart rate\s+(\d{2,3})\b",
        "heart_rate",
        lambda m: f"{m.group(1)} bpm",
    ),
    # SpO2: "SpO2 94%" or "spo2 94"
    (
        r"\bSpO2\s+(\d{2,3})%?\b",
        "spo2",
        lambda m: f"{m.group(1)}%",
    ),
    (
        r"\bsaturation\s+(\d{2,3})%?\b",
        "spo2",
        lambda m: f"{m.group(1)}%",
    ),
    # Glucose: "glucose 280 mg/dL"
    (
        r"\bglucose\s+(\d{2,3})\s*(?:mg/dL|mg/dl)?\b",
        "glucose",
        lambda m: f"{m.group(1)} mg/dL",
    ),
    (
        r"\bblood glucose\s+(\d{2,3})\b",
        "glucose",
        lambda m: f"{m.group(1)} mg/dL",
    ),
    # Creatinine: "creatinine 2.1"
    (
        r"\bcreatinine\s+(\d+\.?\d*)\s*(?:mg/dL|mg/dl)?\b",
        "creatinine",
        lambda m: f"{m.group(1)} mg/dL",
    ),
    # Temperature: "temp 38.5" or "38.5C"
    (
        r"\btemp(?:erature)?\s+(\d{2}\.?\d*)\b",
        "body_temperature",
        lambda m: f"{m.group(1)} C",
    ),
]

# ── Symptom dictionary ─────────────────────────────
SYMPTOMS = {
    "chest pain": "chest_pain",
    "chest tightness": "chest_pain",
    "palpitations": "palpitations",
    "fatigue": "fatigue",
    "weakness": "weakness",
    "nausea": "nausea",
    "vomiting": "vomiting",
    "dizziness": "dizziness",
    "syncope": "syncope",
    "confusion": "confusion",
    "fever": "fever",
    "pain": "pain",
    "swelling": "swelling",
    "thirst": "polydipsia",
    "polyuria": "polyuria",
    "frequency": "urinary_frequency",
}


def extract_entities(text: str) -> List[Dict]:
    """
    Extract clinical entities from text.
    Returns list of entity dicts.
    """
    text_lower = text.lower()
    entities = []

    # Extract conditions
    for term, canonical in CONDITIONS.items():
        if term in text_lower:
            start = text_lower.find(term)
            entities.append({
                "text": text[start:start + len(term)],
                "label": "CONDITION",
                "canonical": canonical,
                "start": start,
                "end": start + len(term),
                "confidence": 0.90,
            })

    # Extract drugs
    for term, canonical in DRUGS.items():
        if term in text_lower:
            start = text_lower.find(term)
            entities.append({
                "text": text[start:start + len(term)],
                "label": "DRUG",
                "canonical": canonical,
                "start": start,
                "end": start + len(term),
                "confidence": 0.92,
            })

    # Extract vital values (with regex)
    for pattern, feature, formatter in VITAL_PATTERNS:
        for match in re.finditer(
            pattern, text, re.IGNORECASE
        ):
            entities.append({
                "text": match.group(0),
                "label": "VITAL",
                "canonical": feature,
                "value": formatter(match),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.95,
            })

    # Extract symptoms
    for term, canonical in SYMPTOMS.items():
        if term in text_lower:
            start = text_lower.find(term)
            entities.append({
                "text": text[start:start + len(term)],
                "label": "SYMPTOM",
                "canonical": canonical,
                "start": start,
                "end": start + len(term),
                "confidence": 0.85,
            })

    # Deduplicate overlapping entities
    entities = _deduplicate(entities)

    logger.info(
        "Dictionary NER: %d entities from %d chars",
        len(entities), len(text),
    )
    return entities


def _deduplicate(
    entities: List[Dict],
) -> List[Dict]:
    """Remove overlapping entities, keep highest confidence."""
    if not entities:
        return []

    entities.sort(
        key=lambda x: (x["start"], -x["confidence"])
    )
    result = []
    last_end = -1

    for ent in entities:
        if ent["start"] >= last_end:
            result.append(ent)
            last_end = ent["end"]

    return result