from pymongo import MongoClient
from datetime import datetime, timezone

client = MongoClient(
    "mongodb://axiom_user:axiom_secret@localhost:27018/axiom_clinical?authSource=admin"
)
db = client.axiom_clinical

note = {
    "patient_id": "3319a93d-e164-4ef1-beb9-ac5803d9cf51",
    "patient_name": "Amit Singh",
    "note_type": "progress_note",
    "author_id": "doctor-001",
    "author_role": "physician",
    "content": (
        "Patient creatinine rose after furosemide dose increase. "
        "Lisinopril improved blood pressure significantly. "
        "BP 142/88, HR 82, SpO2 94%. "
        "Creatinine 3.1 mg/dL, worsening with poor fluid intake. "
        "Metformin reduced glucose to 180 mg/dL. "
        "Poorly compliant with furosemide last week. "
        "Consider reducing furosemide as creatinine elevated."
    ),
    "recorded_at": datetime.now(timezone.utc),
    "nlp_processed": False,
    "tags": ["ckd", "hypertension"],
}
result = db.clinical_notes.insert_one(note)
print(f"Note inserted: {result.inserted_id}")
client.close()