# SNOMED-CT code to clinical feature name mapping
SNOMED_TO_CONDITION = {
    "44054006":  "diabetes_mellitus_type2",
    "73211009":  "diabetes_mellitus",
    "38341003":  "hypertension",
    "13645005":  "copd",
    "84114007":  "heart_failure",
    "40055000":  "chronic_kidney_disease",
    "22298006":  "myocardial_infarction",
    "230690007": "stroke",
    "195967001": "asthma",
    "73211009":  "diabetes",
    "34000006":  "crohns_disease",
    "24700007":  "multiple_sclerosis",
    "363346000": "cancer",
    "49436004":  "atrial_fibrillation",
    "271737000": "anaemia",
    "302870006": "hyperlipidaemia",
    "15777000":  "hypothyroidism",
}

# Medication RxNorm to feature name
RXNORM_TO_MED = {
    "372567009": "metformin",
    "29046":     "lisinopril",
    "203151":    "furosemide",
    "83367":     "atorvastatin",
    "1191":      "aspirin",
    "41493":     "amlodipine",
    "19831":     "omeprazole",
    "627":       "amoxicillin",
    "7052":      "paracetamol",
    "10582":     "warfarin",
}

def snomed_to_condition(snomed_code: str) -> str:
    return SNOMED_TO_CONDITION.get(
        snomed_code, f"condition_{snomed_code}"
    )

def rxnorm_to_medication(rxnorm_code: str) -> str:
    return RXNORM_TO_MED.get(
        rxnorm_code, f"medication_{rxnorm_code}"
    )