content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "r", encoding="utf-8"
).read()

# Fix: drugs should map to themselves as cause nodes
# not to their target features
old = '''    # Try partial match on first word
    first_word = entity_clean.split()[0] if entity_clean else ""
    if first_word in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[first_word]
    for drug in list(DRUGS.keys()):
        if drug in entity_clean:
            canonical = DRUGS.get(drug, drug)
            return ENTITY_TO_FEATURE.get(canonical, canonical)
    return entity_clean.replace(" ", "_")'''

new = '''    # Try partial match on first word
    first_word = entity_clean.split()[0] if entity_clean else ""
    # For drugs: return the drug canonical name as cause
    # (not its target feature)
    for drug, canonical in DRUGS.items():
        if drug in entity_clean:
            return canonical  # e.g. "furosemide" not "creatinine"
    if first_word in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[first_word]
    return entity_clean.replace(" ", "_")'''

if old in content:
    content = content.replace(old, new)
    open(
        "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
        "w", encoding="utf-8"
    ).write(content)
    print("Fixed")
else:
    print("Pattern not found")