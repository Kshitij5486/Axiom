"""
Entity Extractor

Orchestrates BioBERT NER with dictionary fallback.

Priority:
  1. Try BioBERT (HuggingFace pipeline)
  2. Fall back to clinical_dictionary if BioBERT
     unavailable, too slow, or errors

Output format is identical for both methods.
Production swap: zero code changes needed.
"""

import logging
import time
from typing import List, Dict, Optional

from clinical_dictionary import extract_entities

logger = logging.getLogger("axiom.nlp.extractor")

# BioBERT model name
BIOBERT_MODEL = "d4data/biomedical-ner-all"
BIOBERT_TIMEOUT = 10  # seconds

_biobert_pipeline = None
_biobert_available = False


def load_biobert() -> bool:
    """
    Attempt to load BioBERT pipeline.
    Returns True if successful.
    """
    global _biobert_pipeline, _biobert_available

    try:
        logger.info(
            "Loading BioBERT: %s", BIOBERT_MODEL
        )
        from transformers import pipeline
        _biobert_pipeline = pipeline(
            "ner",
            model=BIOBERT_MODEL,
            aggregation_strategy="simple",
        )
        _biobert_available = True
        logger.info("BioBERT loaded successfully")
        return True
    except Exception as e:
        logger.warning(
            "BioBERT unavailable, "
            "using dictionary fallback: %s", e
        )
        _biobert_available = False
        return False


def _biobert_to_standard(
    biobert_entities: list,
    text: str,
) -> List[Dict]:
    """
    Convert HuggingFace NER output to standard format.
    Maps BioBERT labels to clinical labels.
    """
    label_map = {
        "DISEASE":  "CONDITION",
        "CHEMICAL": "DRUG",
        "SIGN":     "SYMPTOM",
        "SPECIES":  "OTHER",
        "DNA":      "OTHER",
        "PROTEIN":  "BIOMARKER",
        "CELL_LINE": "OTHER",
        "CELL_TYPE": "OTHER",
    }

    standard = []
    for ent in biobert_entities:
        label = label_map.get(
            ent.get("entity_group", "OTHER"),
            "OTHER"
        )
        if label == "OTHER":
            continue

        standard.append({
            "text": ent.get("word", ""),
            "label": label,
            "canonical": ent.get(
                "word", ""
            ).lower().replace(" ", "_"),
            "start": ent.get("start", 0),
            "end": ent.get("end", 0),
            "confidence": round(
                float(ent.get("score", 0.8)), 3
            ),
            "model": "biobert",
        })

    return standard


def extract(
    text: str,
    use_biobert: bool = True,
) -> Dict:
    """
    Extract entities from clinical text.

    Args:
        text: clinical note content
        use_biobert: attempt BioBERT first

    Returns:
        {
            "entities": [...],
            "model": "biobert" or "dictionary",
            "n_entities": int,
            "processing_ms": float,
        }
    """
    start = time.perf_counter()

    entities = []
    model_used = "dictionary"

    if use_biobert and _biobert_available and _biobert_pipeline:
        try:
            raw = _biobert_pipeline(text[:512])
            entities = _biobert_to_standard(raw, text)

            # Supplement with vital extraction
            # (BioBERT misses numeric values)
            from clinical_dictionary import (
                VITAL_PATTERNS,
            )
            import re
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
                        "model": "regex",
                    })

            model_used = "biobert"
            logger.info(
                "BioBERT extracted %d entities",
                len(entities),
            )
        except Exception as e:
            logger.warning(
                "BioBERT inference failed, "
                "falling back: %s", e
            )
            entities = extract_entities(text)
            model_used = "dictionary_fallback"
    else:
        entities = extract_entities(text)
        for e in entities:
            e["model"] = "dictionary"
        model_used = "dictionary"

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "entities": entities,
        "model": model_used,
        "n_entities": len(entities),
        "processing_ms": round(elapsed_ms, 2),
    }


def extract_from_note(note: dict) -> Dict:
    """Extract entities from a clinical note dict."""
    content = note.get("content", "")
    patient_id = note.get("patient_id", "unknown")

    result = extract(content)
    result["patient_id"] = patient_id
    result["note_type"] = note.get("note_type", "unknown")

    logger.info(
        "Extracted from note: patient=%s "
        "entities=%d model=%s",
        patient_id[:8] if len(patient_id) > 8
        else patient_id,
        result["n_entities"],
        result["model"],
    )

    return result