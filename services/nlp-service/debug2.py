import sys, re
sys.path.insert(0, "C:/Users/KSHITIJ/axiom/services/nlp-service")
from clinical_dictionary import DRUGS
from relation_extractor import SIMPLE_PATTERNS, ENTITY_TO_FEATURE, _entity_to_feature

text = "patient creatinine rose after furosemide dose increase."
known_features = set(ENTITY_TO_FEATURE.values())
known_drugs = set(DRUGS.values())
all_known = known_features | known_drugs

for pattern, cause_grp, effect_grp, direction, confidence in SIMPLE_PATTERNS:
    for match in re.finditer(pattern, text, re.IGNORECASE):
        try:
            cause_text = match.group(cause_grp).strip() if cause_grp else None
            effect_text = match.group(effect_grp).strip()
            cause_feat = _entity_to_feature(cause_text) if cause_text else None
            effect_feat = _entity_to_feature(effect_text)
            print(f"cause_feat={cause_feat!r} effect_feat={effect_feat!r}")
            print(f"effect in known_features: {effect_feat in known_features}")
            print(f"cause != effect: {cause_feat != effect_feat}")
            print(f"cause in all_known: {cause_feat in all_known}")
            passes = (
                effect_feat in known_features
                and cause_feat != effect_feat
                and (cause_feat is None or cause_feat in all_known or len(cause_feat) > 2)
            )
            print(f"PASSES FILTER: {passes}")
        except Exception as e:
            print(f"Exception: {e}")