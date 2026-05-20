"""
Axiom MongoDB Schema Setup
Collections:
  clinical_notes     - free-text doctor notes
  imaging_metadata   - radiology/imaging metadata
  nlp_extractions    - BioBERT extracted entities
  alert_history      - clinical alert log
"""

from pymongo import MongoClient, ASCENDING, TEXT
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("axiom.mongo_setup")

MONGO_URI = (
    "mongodb://axiom_user:axiom_secret"
    "@localhost:27018/axiom_clinical"
    "?authSource=admin"
)


def setup_mongodb():
    client = MongoClient(MONGO_URI)
    db = client.axiom_clinical

    logger.info("Setting up MongoDB collections...")

    # ── clinical_notes ─────────────────────────────
    if "clinical_notes" not in db.list_collection_names():
        db.create_collection("clinical_notes")
        logger.info("Created: clinical_notes")

    db.clinical_notes.create_index([
        ("patient_id", ASCENDING),
        ("recorded_at", ASCENDING),
    ], name="idx_notes_patient_time")

    db.clinical_notes.create_index([
        ("content", TEXT),
    ], name="idx_notes_fulltext")

    db.clinical_notes.create_index([
        ("nlp_processed", ASCENDING),
    ], name="idx_notes_nlp_processed")

    # ── imaging_metadata ────────────────────────────
    if "imaging_metadata" not in db.list_collection_names():
        db.create_collection("imaging_metadata")
        logger.info("Created: imaging_metadata")

    db.imaging_metadata.create_index([
        ("patient_id", ASCENDING),
        ("study_date", ASCENDING),
    ], name="idx_imaging_patient")

    # ── nlp_extractions ─────────────────────────────
    if "nlp_extractions" not in db.list_collection_names():
        db.create_collection("nlp_extractions")
        logger.info("Created: nlp_extractions")

    db.nlp_extractions.create_index([
        ("patient_id", ASCENDING),
        ("processed_at", ASCENDING),
    ], name="idx_nlp_patient")

    db.nlp_extractions.create_index([
        ("note_id", ASCENDING),
    ], name="idx_nlp_note")

    # ── alert_history ────────────────────────────────
    if "alert_history" not in db.list_collection_names():
        db.create_collection("alert_history")
        logger.info("Created: alert_history")

    db.alert_history.create_index([
        ("patient_id", ASCENDING),
        ("created_at", ASCENDING),
    ], name="idx_alert_patient")

    db.alert_history.create_index([
        ("severity", ASCENDING),
        ("acknowledged", ASCENDING),
    ], name="idx_alert_severity")

    logger.info("All collections and indexes created.")

    # ── Insert sample clinical notes ─────────────────
    sample_notes = [
        {
            "patient_id": "sample-001",
            "note_type": "progress_note",
            "author_id": "doctor-001",
            "author_role": "physician",
            "content": (
                "Patient presents with worsening dyspnea "
                "over 3 days. BP 158/92, HR 98, SpO2 94%. "
                "History of heart failure and hypertension. "
                "Currently on furosemide 40mg daily. "
                "Consider increasing diuretic dose. "
                "Labs show creatinine 1.8 mg/dL, up from "
                "1.4 last week. Monitor renal function closely."
            ),
            "recorded_at": datetime.now(timezone.utc),
            "nlp_processed": False,
            "tags": ["heart_failure", "hypertension",
                     "creatinine_elevated"],
        },
        {
            "patient_id": "sample-002",
            "note_type": "admission_note",
            "author_id": "doctor-002",
            "author_role": "physician",
            "content": (
                "68-year-old male with Type 2 Diabetes "
                "admitted for hyperglycaemia. Blood glucose "
                "340 mg/dL on admission. HbA1c 9.2%. "
                "Currently on metformin 500mg but poorly "
                "compliant. Started insulin sliding scale. "
                "Nephrology consulted for creatinine 2.1. "
                "Patient reports increased thirst and polyuria "
                "for past 2 weeks."
            ),
            "recorded_at": datetime.now(timezone.utc),
            "nlp_processed": False,
            "tags": ["diabetes", "hyperglycaemia",
                     "insulin", "ckd"],
        },
        {
            "patient_id": "sample-003",
            "note_type": "discharge_summary",
            "author_id": "doctor-001",
            "author_role": "physician",
            "content": (
                "Patient discharged after 4-day admission "
                "for COPD exacerbation. SpO2 improved from "
                "82% on admission to 94% on 2L O2. "
                "Treated with salbutamol nebulisers and "
                "IV methylprednisolone. Chest X-ray showed "
                "hyperinflation consistent with COPD. "
                "Discharged on oral prednisolone 30mg "
                "tapering course. Follow up in 2 weeks."
            ),
            "recorded_at": datetime.now(timezone.utc),
            "nlp_processed": False,
            "tags": ["copd", "exacerbation",
                     "salbutamol", "steroids"],
        },
    ]

    result = db.clinical_notes.insert_many(sample_notes)
    logger.info(
        "Inserted %d sample notes: %s",
        len(result.inserted_ids),
        result.inserted_ids,
    )

    # Verify
    logger.info("\nCollection summary:")
    for coll in db.list_collection_names():
        count = db[coll].count_documents({})
        logger.info("  %-25s %d documents", coll, count)

    client.close()
    logger.info("MongoDB setup complete.")


if __name__ == "__main__":
    setup_mongodb()