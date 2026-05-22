import re

files = [
    "tests/unit/test_causal_engine.py",
    "tests/unit/test_zk_layer.py",
    "tests/unit/test_federated.py",
    "tests/unit/test_survival.py",
]

for filepath in files:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    clean = []
    for line in lines:
        stripped = line.strip()
        # Skip leftover path fragments
        if stripped in [
            '"..", "..",',
            '"..", "services", "causal-engine"',
            '"..", "services", "zk-service"',
            '"..", "services", "federated-service"',
            '"..", "services", "survival-service"',
            "services/causal-engine",
            "))",
            "# path managed by conftest.py",
        ]:
            continue
        if stripped.startswith("os.path.dirname(__file__)"):
            continue
        if stripped.startswith('"services"'):
            continue
        if stripped.startswith('"..", ".."'):
            continue
        clean.append(line)

    result = "\n".join(clean)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Fixed: {filepath}")

print("All fixed")