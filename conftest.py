import sys
import os

root = os.path.dirname(os.path.abspath(__file__))

paths = [
    os.path.join(root, "services", "causal-engine"),
    os.path.join(root, "services", "zk-service"),
    os.path.join(root, "services", "federated-service"),
    os.path.join(root, "services", "survival-service"),
    os.path.join(root, "services", "nlp-service"),
]

for p in paths:
    if p not in sys.path:
        sys.path.append(p)