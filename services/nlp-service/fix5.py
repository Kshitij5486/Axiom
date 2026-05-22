content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "r", encoding="utf-8"
).read()

old_func = '''def _entity_to_feature(entity: str) -> str:
    """Map entity text to causal graph feature."""
    entity_clean = _normalize_entity(entity)

    # Direct lookup
    if entity_clean in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[entity_clean]

    # Check drug dictionary
    for drug, canonical in DRUGS.items():
        if drug in entity_clean:
            return ENTITY_TO_FEATURE.get(
                canonical, canonical
            )

    # Check condition dictionary
    for cond, canonical in CONDITIONS.items():
        if cond in entity_clean:
            return ENTITY_TO_FEATURE.get(
                canonical, canonical
            )

    # Try partial match on first word
    first_word = entity_clean.split()[0] if entity_clean else ""
    # For drugs: return the drug canonical name as cause
    # (not its target feature)
    for drug, canonical in DRUGS.items():
        if drug in entity_clean:
            return canonical  # e.g. "furosemide" not "creatinine"
    if first_word in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[first_word]
    return entity_clean.replace(" ", "_")'''

new_func = '''def _entity_to_feature(entity: str) -> str:
    """Map entity text to causal graph feature.
    
    For CAUSE entities: return drug/condition name
    For EFFECT entities: return the feature name
    Context-free: caller must interpret.
    """
    entity_clean = _normalize_entity(entity)

    # Direct lookup in feature map
    if entity_clean in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[entity_clean]

    # Drug match: return the drug canonical name
    # (NOT its target feature - caller decides context)
    for drug, canonical in DRUGS.items():
        if drug in entity_clean:
            return canonical

    # Condition match: return feature
    for cond, canonical in CONDITIONS.items():
        if cond in entity_clean:
            return ENTITY_TO_FEATURE.get(canonical, canonical)

    # First word match
    first_word = entity_clean.split()[0] if entity_clean else ""
    if first_word in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[first_word]

    return entity_clean.replace(" ", "_")'''

if old_func in content:
    content = content.replace(old_func, new_func)
    open(
        "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
        "w", encoding="utf-8"
    ).write(content)
    print("Fixed")
else:
    print("Not found - length mismatch")
    print(f"Looking for length: {len(old_func)}")