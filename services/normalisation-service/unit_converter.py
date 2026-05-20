# Unit conversion functions for clinical values
# All values normalised to standard SI units

CONVERSIONS = {
    # Glucose: mg/dL <-> mmol/L
    ("glucose", "mg/dL", "mmol/L"): lambda x: round(x / 18.0, 2),
    ("glucose", "mmol/L", "mg/dL"): lambda x: round(x * 18.0, 2),

    # Creatinine: mg/dL <-> umol/L
    ("creatinine", "mg/dL", "umol/L"): lambda x: round(x * 88.4, 2),
    ("creatinine", "umol/L", "mg/dL"): lambda x: round(x / 88.4, 4),

    # Hemoglobin: g/dL <-> g/L
    ("hemoglobin", "g/dL", "g/L"): lambda x: round(x * 10.0, 2),
    ("hemoglobin", "g/L", "g/dL"): lambda x: round(x / 10.0, 2),

    # Cholesterol: mg/dL <-> mmol/L
    ("total_cholesterol", "mg/dL", "mmol/L"): lambda x: round(x / 38.67, 2),
    ("total_cholesterol", "mmol/L", "mg/dL"): lambda x: round(x * 38.67, 2),
    ("ldl_cholesterol", "mg/dL", "mmol/L"): lambda x: round(x / 38.67, 2),
    ("hdl_cholesterol", "mg/dL", "mmol/L"): lambda x: round(x / 38.67, 2),

    # Temperature: Fahrenheit -> Celsius
    ("body_temperature", "F", "C"): lambda x: round((x - 32) * 5/9, 2),
    ("body_temperature", "Fahrenheit", "C"): lambda x: round((x - 32) * 5/9, 2),

    # Weight: lbs -> kg
    ("body_weight", "lbs", "kg"): lambda x: round(x * 0.453592, 2),
    ("body_weight", "[lb_av]", "kg"): lambda x: round(x * 0.453592, 2),

    # Height: inches -> cm
    ("body_height", "in", "cm"): lambda x: round(x * 2.54, 2),
    ("body_height", "[in_i]", "cm"): lambda x: round(x * 2.54, 2),
}

# Standard units per feature
STANDARD_UNITS = {
    "heart_rate":        "bpm",
    "systolic_bp":       "mmHg",
    "diastolic_bp":      "mmHg",
    "blood_pressure":    "mmHg",
    "glucose":           "mg/dL",
    "hemoglobin":        "g/dL",
    "creatinine":        "mg/dL",
    "potassium":         "mmol/L",
    "sodium":            "mmol/L",
    "spo2":              "%",
    "body_temperature":  "C",
    "body_weight":       "kg",
    "body_height":       "cm",
    "bmi":               "kg/m2",
    "hba1c":             "%",
    "total_cholesterol": "mg/dL",
    "ldl_cholesterol":   "mg/dL",
    "hdl_cholesterol":   "mg/dL",
    "wbc":               "10*3/uL",
    "platelets":         "10*3/uL",
    "bun":               "mg/dL",
}

def convert_unit(
    feature_name: str,
    value: float,
    from_unit: str,
    to_unit: str = None
) -> tuple:
    """
    Convert value to standard unit.
    Returns (converted_value, standard_unit).
    """
    if to_unit is None:
        to_unit = STANDARD_UNITS.get(feature_name, from_unit)

    if from_unit == to_unit:
        return value, from_unit

    key = (feature_name, from_unit, to_unit)
    if key in CONVERSIONS:
        return CONVERSIONS[key](value), to_unit

    return value, from_unit

def get_standard_unit(feature_name: str) -> str:
    return STANDARD_UNITS.get(feature_name, "unknown")