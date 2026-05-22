content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/relation_extractor.py",
    "r", encoding="utf-8"
).read()

# Find and show the current _entity_to_feature function
start = content.find("def _entity_to_feature")
end = content.find("\ndef ", start + 1)
print("Current function:")
print(repr(content[start:end]))