# LOINC code to clinical feature name mapping
LOINC_TO_FEATURE = {
    "8867-4":  "heart_rate",
    "55284-4": "blood_pressure",
    "85354-9": "blood_pressure",
    "8480-6":  "systolic_bp",
    "8462-4":  "diastolic_bp",
    "2339-0":  "glucose",
    "718-7":   "hemoglobin",
    "2160-0":  "creatinine",
    "2823-3":  "potassium",
    "2951-2":  "sodium",
    "59408-5": "spo2",
    "8310-5":  "body_temperature",
    "8302-2":  "body_height",
    "29463-7": "body_weight",
    "39156-5": "bmi",
    "4548-4":  "hba1c",
    "2085-9":  "hdl_cholesterol",
    "2089-1":  "ldl_cholesterol",
    "2093-3":  "total_cholesterol",
    "1920-8":  "ast",
    "1742-6":  "alt",
    "6768-6":  "alkaline_phosphatase",
    "3094-0":  "bun",
    "2075-0":  "chloride",
    "2028-9":  "co2",
    "14627-4": "bicarbonate",
    "6690-2":  "wbc",
    "777-3":   "platelets",
    "789-8":   "rbc",
}

# Reference ranges for abnormality detection
REFERENCE_RANGES = {
    "heart_rate":        (50,   120),
    "systolic_bp":       (90,   160),
    "diastolic_bp":      (60,   100),
    "glucose":           (70,   200),
    "hemoglobin":        (8.0,  17.5),
    "creatinine":        (0.5,  2.5),
    "potassium":         (3.5,  5.5),
    "sodium":            (135,  145),
    "spo2":              (92,   100),
    "body_temperature":  (36.0, 38.5),
    "hba1c":             (0,    6.5),
    "hdl_cholesterol":   (40,   999),
    "ldl_cholesterol":   (0,    130),
    "total_cholesterol": (0,    200),
    "wbc":               (4.0,  11.0),
    "platelets":         (150,  400),
    "bun":               (7,    25),
}

def loinc_to_feature(loinc_code: str) -> str:
    return LOINC_TO_FEATURE.get(loinc_code, loinc_code)

def get_reference_range(feature_name: str):
    return REFERENCE_RANGES.get(feature_name, (None, None))

def is_abnormal(feature_name: str, value: float) -> bool:
    lo, hi = get_reference_range(feature_name)
    if lo is None or hi is None or value is None:
        return False
    return value < lo or value > hi