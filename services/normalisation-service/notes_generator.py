"""
Generate synthetic clinical notes for all 50 patients
and insert into MongoDB clinical_notes collection.
"""

import random
import psycopg2
from pymongo import MongoClient
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("axiom.notes_generator")

MONGO_URI = (
    "mongodb://axiom_user:axiom_secret"
    "@localhost:27018/axiom_clinical"
    "?authSource=admin"
)

NOTE_TEMPLATES = {
    "heart_failure": [
        (
            "Patient presents with worsening dyspnea and "
            "bilateral leg oedema. BP {bp}, HR {hr}, "
            "SpO2 {spo2}%. Currently on furosemide. "
            "Creatinine {cr} mg/dL. Consider uptitrating "
            "diuretic therapy. Echo ordered."
        ),
        (
            "Follow-up for heart failure. Patient reports "
            "improved exercise tolerance. Weight down 2kg. "
            "SpO2 {spo2}% on room air. HR {hr}. "
            "Creatinine stable at {cr}. Continue current "
            "medications. Review in 4 weeks."
        ),
    ],
    "diabetes": [
        (
            "Type 2 diabetic on metformin. Fasting glucose "
            "{glucose} mg/dL. HbA1c due next visit. "
            "BP {bp}, HR {hr}. Creatinine {cr} - renal "
            "function stable. Advised dietary compliance "
            "and regular exercise."
        ),
        (
            "Diabetic review. Blood glucose poorly controlled "
            "at {glucose} mg/dL. Consider adding second "
            "agent. BP {bp}. Creatinine {cr}. "
            "Ophthalmology referral placed. Foot exam normal."
        ),
    ],
    "ckd": [
        (
            "CKD stage 3 review. Creatinine {cr} mg/dL, "
            "up from last visit. eGFR declining. "
            "BP {bp} - optimise ACE inhibitor dose. "
            "Potassium 4.8 - monitor closely. "
            "Nephrology referral discussed."
        ),
    ],
    "copd": [
        (
            "COPD review. SpO2 {spo2}% on room air. "
            "HR {hr}. No acute exacerbation currently. "
            "Spirometry scheduled. Patient on salbutamol PRN. "
            "Smoking cessation counselling provided."
        ),
    ],
    "general": [
        (
            "Routine follow-up. Vitals: BP {bp}, HR {hr}, "
            "SpO2 {spo2}%. Blood glucose {glucose} mg/dL. "
            "Creatinine {cr}. No acute concerns. "
            "Continue current medications. Review in 3 months."
        ),
    ],
}

PROFILE_TO_CATEGORY = {
    "Heart Failure Patient": "heart_failure",
    "Diabetic Hypertensive": "diabetes",
    "Chronic Kidney Disease": "ckd",
    "COPD Patient": "copd",
    "Healthy Adult": "general",
}


def get_patients():
    conn = psycopg2.connect(
        host="localhost", port=5439,
        dbname="axiom", user="axiom_user",
        password="axiom_secret",
    )
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id, first_name, last_name "
        "FROM patients ORDER BY created_at"
    )
    patients = cursor.fetchall()
    conn.close()
    return patients


def generate_notes():
    patients = get_patients()
    client = MongoClient(MONGO_URI)
    db = client.axiom_clinical

    notes = []
    profiles = list(PROFILE_TO_CATEGORY.keys())

    for patient_id, first, last in patients:
        profile = random.choice(profiles)
        category = PROFILE_TO_CATEGORY[profile]
        templates = NOTE_TEMPLATES[category]
        template = random.choice(templates)

        # Generate realistic values
        content = template.format(
            bp=f"{random.randint(110,170)}/"
               f"{random.randint(70,100)}",
            hr=random.randint(60, 110),
            spo2=random.randint(88, 99),
            glucose=random.randint(80, 280),
            cr=round(random.uniform(0.6, 3.5), 1),
        )

        note = {
            "patient_id": str(patient_id),
            "patient_name": f"{first} {last}",
            "note_type": random.choice([
                "progress_note",
                "admission_note",
                "discharge_summary",
                "outpatient_review",
            ]),
            "author_id": random.choice([
                "doctor-001", "doctor-002",
                "doctor-003",
            ]),
            "author_role": "physician",
            "content": content,
            "profile": profile,
            "recorded_at": datetime.now(timezone.utc),
            "nlp_processed": False,
            "tags": [category],
        }
        notes.append(note)

    result = db.clinical_notes.insert_many(notes)
    logger.info(
        "Inserted %d clinical notes for %d patients",
        len(result.inserted_ids), len(patients),
    )

    total = db.clinical_notes.count_documents({})
    logger.info("Total notes in MongoDB: %d", total)
    client.close()


if __name__ == "__main__":
    generate_notes()