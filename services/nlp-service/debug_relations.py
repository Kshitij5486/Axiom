import sys, re
sys.path.insert(0, "C:/Users/KSHITIJ/axiom/services/nlp-service")
from relation_extractor import SIMPLE_PATTERNS, CAUSAL_PATTERNS, _entity_to_feature, ENTITY_TO_FEATURE

text = "patient creatinine rose after furosemide dose increase."
known_features = set(ENTITY_TO_FEATURE.values())
print("Known features sample:", list(known_features)[:10])

for pattern, cause_grp, effect_grp, direction, confidence in SIMPLE_PATTERNS:
    for match in re.finditer(pattern, text, re.IGNORECASE):
        cause_text = match.group(cause_grp).strip() if cause_grp else None
        effect_text = match.group(effect_grp).strip()
        cause_feat = _entity_to_feature(cause_text) if cause_text else None
        effect_feat = _entity_to_feature(effect_text)
        print(f"Match: cause_text={cause_text!r} effect_text={effect_text!r}")
        print(f"  cause_feat={cause_feat!r} effect_feat={effect_feat!r}")
        print(f"  cause in known: {cause_feat in known_features}")
        print(f"  effect in known: {effect_feat in known_features}")