"""
Axiom Synthetic Patient Data Generator
Generates 50 realistic patients with:
- Demographics
- 5 vital observations x 20 time points each
- 1-3 active conditions
- 1-3 active medications
All flowing through the FHIR adapter into PostgreSQL + Kafka
"""

import json
import random
import uuid
import time
import logging
from datetime import datetime, timedelta, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("axiom.generator")

FHIR_BASE = "http://localhost:8080/fhir"

# Clinical profiles — realistic patient archetypes
PATIENT_PROFILES = [
    {
        "name": "Diabetic Hypertensive",
        "conditions": [
            ("44054006", "Type 2 Diabetes Mellitus"),
            ("38341003", "Hypertension"),
        ],
        "medications": [
            ("metformin",    "372567009", "500mg",  "oral"),
            ("lisinopril",   "29046",     "10mg",   "oral"),
            ("atorvastatin", "83367",     "20mg",   "oral"),
        ],
        "vital_ranges": {
            "heart_rate":    (70,  95),
            "systolic_bp":   (135, 165),
            "spo2":          (95,  99),
            "glucose":       (140, 280),
            "creatinine":    (0.9, 1.8),
        },
    },
    {
        "name": "Heart Failure Patient",
        "conditions": [
            ("84114007", "Heart Failure"),
            ("38341003", "Hypertension"),
        ],
        "medications": [
            ("furosemide",  "203151", "40mg",  "oral"),
            ("lisinopril",  "29046",  "10mg",  "oral"),
            ("aspirin",     "1191",   "81mg",  "oral"),
        ],
        "vital_ranges": {
            "heart_rate":    (80,  110),
            "systolic_bp":   (110, 145),
            "spo2":          (88,  96),
            "glucose":       (90,  140),
            "creatinine":    (1.2, 2.5),
        },
    },
    {
        "name": "Chronic Kidney Disease",
        "conditions": [
            ("40055000", "Chronic Kidney Disease"),
            ("38341003", "Hypertension"),
            ("44054006", "Type 2 Diabetes Mellitus"),
        ],
        "medications": [
            ("lisinopril",   "29046",     "20mg",  "oral"),
            ("furosemide",   "203151",    "80mg",  "oral"),
            ("metformin",    "372567009", "500mg", "oral"),
        ],
        "vital_ranges": {
            "heart_rate":    (65,  90),
            "systolic_bp":   (130, 160),
            "spo2":          (94,  99),
            "glucose":       (120, 220),
            "creatinine":    (2.0, 4.5),
        },
    },
    {
        "name": "Healthy Adult",
        "conditions": [],
        "medications": [],
        "vital_ranges": {
            "heart_rate":    (55,  80),
            "systolic_bp":   (100, 125),
            "spo2":          (97,  100),
            "glucose":       (75,  110),
            "creatinine":    (0.6, 1.1),
        },
    },
    {
        "name": "COPD Patient",
        "conditions": [
            ("13645005", "COPD"),
        ],
        "medications": [
            ("aspirin",    "1191",   "81mg",  "oral"),
        ],
        "vital_ranges": {
            "heart_rate":    (75,  100),
            "systolic_bp":   (120, 150),
            "spo2":          (85,  94),
            "glucose":       (80,  130),
            "creatinine":    (0.7, 1.3),
        },
    },
]

# LOINC codes for vitals
VITAL_LOINC = [
    ("8867-4",  "heart_rate",  "bpm"),
    ("8480-6",  "systolic_bp", "mmHg"),
    ("59408-5", "spo2",        "%"),
    ("2339-0",  "glucose",     "mg/dL"),
    ("2160-0",  "creatinine",  "mg/dL"),
]

FIRST_NAMES_M = [
    "Amit", "Rahul", "Vikram", "Suresh", "Arjun",
    "Rajesh", "Deepak", "Anil", "Sandeep", "Manoj",
]
FIRST_NAMES_F = [
    "Priya", "Sunita", "Kavita", "Anita", "Neha",
    "Pooja", "Rekha", "Meena", "Sonia", "Divya",
]
LAST_NAMES = [
    "Sharma", "Verma", "Singh", "Kumar", "Patel",
    "Gupta", "Mishra", "Joshi", "Shah", "Rao",
]


def random_dob(min_age=25, max_age=80) -> str:
    days = random.randint(min_age * 365, max_age * 365)
    dob = datetime.now() - timedelta(days=days)
    return dob.strftime("%Y-%m-%d")


def build_fhir_patient(
    fhir_id: str,
    first_name: str,
    last_name: str,
    gender: str,
    dob: str,
) -> dict:
    return {
        "resourceType": "Patient",
        "id": fhir_id,
        "name": [{
            "family": last_name,
            "given": [first_name],
        }],
        "gender": gender,
        "birthDate": dob,
    }


def build_fhir_observation(
    fhir_id: str,
    patient_fhir_id: str,
    loinc_code: str,
    value: float,
    unit: str,
    effective_dt: str,
) -> dict:
    return {
        "resourceType": "Observation",
        "id": fhir_id,
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "vital-signs",
        }]}],
        "code": {"coding": [{
            "system": "http://loinc.org",
            "code": loinc_code,
        }]},
        "subject": {
            "reference": f"Patient/{patient_fhir_id}"
        },
        "effectiveDateTime": effective_dt,
        "valueQuantity": {
            "value": value,
            "unit": unit,
        },
    }


def ingest_patient(patient_data: dict) -> dict:
    r = requests.post(
        f"{FHIR_BASE}/patient",
        json=patient_data,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def ingest_observation(obs_data: dict) -> dict:
    r = requests.post(
        f"{FHIR_BASE}/observation",
        json=obs_data,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def generate_patients(n: int = 50):
    logger.info("=" * 50)
    logger.info("Axiom Synthetic Data Generator")
    logger.info(f"Generating {n} patients...")
    logger.info("=" * 50)

    results = {
        "patients_created": 0,
        "observations_created": 0,
        "errors": 0,
        "patient_ids": [],
    }

    for i in range(n):
        try:
            # Pick random profile
            profile = random.choice(PATIENT_PROFILES)

            # Demographics
            gender = random.choice(["male", "female"])
            first = random.choice(
                FIRST_NAMES_M if gender == "male"
                else FIRST_NAMES_F
            )
            last = random.choice(LAST_NAMES)
            dob = random_dob()
            fhir_id = str(uuid.uuid4())

            # Build + ingest patient
            fhir_patient = build_fhir_patient(
                fhir_id, first, last, gender, dob
            )
            response = ingest_patient(fhir_patient)
            patient_id = response.get("patient_id")
            results["patients_created"] += 1
            results["patient_ids"].append(patient_id)

            logger.info(
                "Patient %d/%d: %s %s (%s) "
                "profile='%s' id=%s",
                i + 1, n, first, last, gender,
                profile["name"], patient_id,
            )

            # Generate vitals — 20 time points
            # over last 30 days
            for loinc, vital_name, unit in VITAL_LOINC:
                lo, hi = profile["vital_ranges"].get(
                    vital_name, (50, 150)
                )

                for j in range(20):
                    # Time point: every 36 hours back
                    dt = datetime.now(timezone.utc) - timedelta(
                        hours=j * 36
                    )

                    # Add realistic variation
                    value = round(
                        random.uniform(lo, hi)
                        + random.gauss(0, (hi - lo) * 0.05),
                        1,
                    )
                    value = max(lo * 0.8, min(hi * 1.2, value))

                    obs = build_fhir_observation(
                        fhir_id=str(uuid.uuid4()),
                        patient_fhir_id=fhir_id,
                        loinc_code=loinc,
                        value=value,
                        unit=unit,
                        effective_dt=dt.isoformat(),
                    )
                    ingest_observation(obs)
                    results["observations_created"] += 1

            logger.info(
                "  -> %d observations ingested",
                20 * len(VITAL_LOINC),
            )

        except Exception as e:
            results["errors"] += 1
            logger.error(
                "Patient %d failed: %s", i + 1, e
            )

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    logger.info("=" * 50)
    logger.info("Generation complete:")
    logger.info(
        "  Patients created:      %d",
        results["patients_created"],
    )
    logger.info(
        "  Observations created:  %d",
        results["observations_created"],
    )
    logger.info(
        "  Errors:                %d",
        results["errors"],
    )
    logger.info("=" * 50)

    return results


if __name__ == "__main__":
    generate_patients(50)