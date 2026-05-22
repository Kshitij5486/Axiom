content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "r", encoding="utf-8"
).read()

old = """    # Filter: only keep relations where both
    # cause and effect are known clinical features
    known_features = set(ENTITY_TO_FEATURE.values())
    filtered = []
    for rel in relations:
        cause = rel.get("cause")
        effect = rel.get("effect")
        if (
            (cause is None or cause in known_features)
            and effect in known_features
            and cause != effect
        ):
            filtered.append(rel)"""

new = """    # Filter: keep relations where effect is a known
    # clinical feature and cause != effect
    known_features = set(ENTITY_TO_FEATURE.values())
    known_drugs = set(DRUGS.values())
    all_known = known_features | known_drugs
    filtered = []
    for rel in relations:
        cause = rel.get("cause")
        effect = rel.get("effect")
        if (
            effect in known_features
            and cause != effect
            and (cause is None or cause in all_known
                 or len(cause) > 2)
        ):
            filtered.append(rel)"""

if old in content:
    content = content.replace(old, new)
    open(
        "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
        "w", encoding="utf-8"
    ).write(content)
    print("Fixed")
else:
    print("Not found - searching...")
    idx = content.find("Filter: only keep")
    print(repr(content[idx:idx+200]))