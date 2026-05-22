content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "r", encoding="utf-8"
).read()

old = '    return entity_clean.replace(" ", "_")'

new = '''    # Try partial match on first word
    first_word = entity_clean.split()[0] if entity_clean else ""
    if first_word in ENTITY_TO_FEATURE:
        return ENTITY_TO_FEATURE[first_word]
    for drug in list(DRUGS.keys()):
        if drug in entity_clean:
            canonical = DRUGS.get(drug, drug)
            return ENTITY_TO_FEATURE.get(canonical, canonical)
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
    idx = content.find("return entity_clean")
    print(repr(content[idx-5:idx+50]))