import numpy as np
import sys
sys.path.insert(0, '.')
from patient_encoder import encode_all_patients
from clinical_env import ClinicalPatientEnv, ACTIONS

encoded = encode_all_patients()
print(f"Patients encoded: {len(encoded)}")

env = ClinicalPatientEnv(patient_states=encoded)
obs, _ = env.reset(seed=42)
print(f"Initial state (first 5 vitals): {obs[:5].round(3)}")

total_reward = 0
for step in range(10):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, _ = env.step(action)
    total_reward += reward
    action_name = ACTIONS[action]["name"]
    print(f"Step {step+1}: action={action_name} reward={reward:.3f}")
    if terminated or truncated:
        break

print(f"Episode total reward: {total_reward:.3f}")
print("Environment test PASSED")