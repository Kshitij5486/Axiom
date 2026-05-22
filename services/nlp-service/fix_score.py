content = open(
    "C:/Users/KSHITIJ/axiom/services/nlp-service/main.py",
    "r", encoding="utf-8"
).read()

old = "    score_result[\"predictive_alerts\"] = predictive_alerts\n    score_result[\"current_vitals\"] = latest\n    return score_result"

new = """    score_result["predictive_alerts"] = predictive_alerts
    score_result["current_vitals"] = latest

    # Convert numpy types to Python native for JSON
    import json, numpy as np
    def convert(obj):
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list): return [convert(i) for i in obj]
        return obj

    return convert(score_result)"""

if old in content:
    content = content.replace(old, new)
    open("C:/Users/KSHITIJ/axiom/services/nlp-service/main.py", "w", encoding="utf-8").write(content)
    print("Fixed")
else:
    print("Not found")