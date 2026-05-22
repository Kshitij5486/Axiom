import sys
sys.path.insert(0, ".")
from relation_extractor import extract_relations

text = (
    "Patient creatinine rose after furosemide dose increase. "
    "Lisinopril improved blood pressure significantly. "
    "Creatinine 3.1 mg/dL, worsening with poor fluid intake. "
    "Metformin reduced glucose to 180 mg/dL. "
    "Poorly compliant with furosemide last week."
)

relations = extract_relations(text)
print(f"Relations found: {len(relations)}")
for r in relations:
    print(f"  {r}")