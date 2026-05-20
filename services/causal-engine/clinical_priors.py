"""
Clinical Causal Prior Knowledge

These are established clinical causal relationships.
We tell DoWhy to respect these edges rather than
trying to learn them purely from data.

This is the key difference between Axiom and a
naive ML model:
  - ML asks "what correlates with what?"
  - Axiom asks "what causes what, clinically?"

Prior edges are asymmetric and directional:
  ("cause", "effect")
"""

# Clinically established causal edges
# Each tuple: (cause, effect)
CLINICAL_PRIOR_EDGES = [
    # Conditions cause vital/lab changes
    ("diabetes",              "glucose"),
    ("diabetes",              "creatinine"),
    ("diabetes",              "hemoglobin"),
    ("hypertension",          "systolic_bp"),
    ("hypertension",          "heart_rate"),
    ("heart_failure",         "heart_rate"),
    ("heart_failure",         "spo2"),
    ("heart_failure",         "creatinine"),
    ("chronic_kidney_disease","creatinine"),
    ("chronic_kidney_disease","potassium"),
    ("chronic_kidney_disease","sodium"),
    ("copd",                  "spo2"),
    ("copd",                  "heart_rate"),

    # Medications cause changes
    ("furosemide",    "creatinine"),
    ("furosemide",    "potassium"),
    ("furosemide",    "sodium"),
    ("metformin",     "glucose"),
    ("lisinopril",    "systolic_bp"),
    ("lisinopril",    "creatinine"),
    ("lisinopril",    "potassium"),
    ("atorvastatin",  "total_cholesterol"),
    ("atorvastatin",  "ldl_cholesterol"),
    ("aspirin",       "heart_rate"),

    # Demographics are confounders
    ("age",            "creatinine"),
    ("age",            "systolic_bp"),
    ("age",            "glucose"),
    ("gender_encoded", "hemoglobin"),
    ("gender_encoded", "creatinine"),
]

# Outcome nodes — what we want to predict/control
OUTCOME_NODES = [
    "glucose",
    "creatinine",
    "heart_rate",
    "systolic_bp",
    "spo2",
    "potassium",
    "sodium",
    "hemoglobin",
]

# Confounder nodes — demographics
CONFOUNDER_NODES = [
    "age",
    "gender_encoded",
]

# Treatment nodes — interventions a doctor can make
TREATMENT_NODES = [
    "furosemide",
    "metformin",
    "lisinopril",
    "atorvastatin",
    "aspirin",
    "diabetes",
    "hypertension",
    "heart_failure",
    "chronic_kidney_disease",
    "copd",
]

# Minimum observations needed to build a graph
MIN_OBSERVATIONS = 5

# Maximum causal effect magnitude (for normalisation)
MAX_EFFECT = 100.0


def get_prior_edges_for_nodes(
    available_nodes: set,
) -> list:
    """
    Return only prior edges where both source
    and target are in available_nodes.
    """
    return [
        (src, dst)
        for src, dst in CLINICAL_PRIOR_EDGES
        if src in available_nodes
        and dst in available_nodes
    ]


def get_treatments_in_data(
    available_nodes: set,
) -> list:
    return [
        t for t in TREATMENT_NODES
        if t in available_nodes
    ]


def get_outcomes_in_data(
    available_nodes: set,
) -> list:
    return [
        o for o in OUTCOME_NODES
        if o in available_nodes
    ]