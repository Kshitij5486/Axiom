content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "r", encoding="utf-8"
).read()

# Add SIMPLE_PATTERNS after DIRECTION_TO_SIGN dict
insert_after = '    "non_compliant": 0,\n}'

simple = """
    "non_compliant": 0,
}

# Simpler direct patterns (added Day 38)
SIMPLE_PATTERNS = [
    (r"(\\w+)\\s+(?:rose|increased|elevated)\\s+after\\s+([\\w\\s]+?)(?:\\.|,)", 2, 1, "causes", 0.75),
    (r"([\\w]+)\\s+(?:improved|reduced|lowered|controlled|decreased)\\s+([\\w\\s]+?)(?:\\.|,|to\\s)", 1, 2, "improves", 0.75),
    (r"(\\w+)\\s+worsening\\s+with\\s+([\\w\\s]+?)(?:\\.|,)", 2, 1, "worsens", 0.65),
    (r"([\\w]+)\\s+(?:caused|induced|triggered)\\s+([\\w\\s]+?)(?:\\.|,)", 1, 2, "causes", 0.80),
]"""

content = content.replace(
    '    "non_compliant": 0,\n}',
    simple
)

# Add SIMPLE_PATTERNS to the loop
content = content.replace(
    "    for pattern, cause_grp, effect_grp, direction, confidence in CAUSAL_PATTERNS:",
    "    for pattern, cause_grp, effect_grp, direction, confidence in SIMPLE_PATTERNS + CAUSAL_PATTERNS:"
)

open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "w", encoding="utf-8"
).write(content)
print("Done")