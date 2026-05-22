"""
ClinicalPatientEnv — Gymnasium Environment

State space (11 dims, continuous Box):
  Same as patient_encoder output
  [glucose_norm, creatinine_norm, hr_norm,
   sbp_norm, spo2_norm,
   g->cr, sbp->cr, sbp->hr, hr->spo2,
   cr->spo2, g->hr]

Action space (discrete, 6 actions):
  0: increase_lisinopril   targets systolic_bp (-10mmHg)
  1: increase_furosemide   targets creatinine (-0.2 mg/dL)
  2: increase_metformin    targets glucose (-20 mg/dL)
  3: add_aspirin           targets heart_rate (-3 bpm)
  4: lifestyle_counselling mild effect all vitals
  5: no_action             baseline

Reward:
  primary_benefit  = causal_effect(action->target) * magnitude
  side_effect_cost = sum(causal_effect(action->other) * sensitivity)
  survival_bonus   = improvement in risk score * 2.0
  reward = primary_benefit - side_effect_cost + survival_bonus

Episode:
  Length: 10 steps
  Reset: random patient from pool
  Termination: 10 steps OR risk_score > 2.0 (crisis)
"""

import logging
from typing import Optional

import numpy as np
import gymnasium as gym
from gymnasium import spaces

logger = logging.getLogger("axiom.survival.env")

# Treatment actions
ACTIONS = [
    {
        "name": "increase_lisinopril",
        "target": "systolic_bp",
        "target_idx": 3,
        "magnitude": -0.08,   # -10mmHg normalized
        "side_effects": {
            "creatinine": 0.02,   # slight rise
            "heart_rate": -0.02,
        },
    },
    {
        "name": "increase_furosemide",
        "target": "creatinine",
        "target_idx": 1,
        "magnitude": -0.04,   # -0.2 mg/dL normalized
        "side_effects": {
            "systolic_bp": -0.03,
            "heart_rate": 0.02,
        },
    },
    {
        "name": "increase_metformin",
        "target": "glucose",
        "target_idx": 0,
        "magnitude": -0.06,   # -20 mg/dL normalized
        "side_effects": {
            "heart_rate": -0.01,
        },
    },
    {
        "name": "add_aspirin",
        "target": "heart_rate",
        "target_idx": 2,
        "magnitude": -0.03,   # -3 bpm normalized
        "side_effects": {
            "systolic_bp": -0.01,
        },
    },
    {
        "name": "lifestyle_counselling",
        "target": "glucose",
        "target_idx": 0,
        "magnitude": -0.02,
        "side_effects": {
            "heart_rate": -0.01,
            "systolic_bp": -0.01,
        },
    },
    {
        "name": "no_action",
        "target": None,
        "target_idx": None,
        "magnitude": 0.0,
        "side_effects": {},
    },
]

N_ACTIONS = len(ACTIONS)
STATE_DIM = 11

# Organ sensitivity weights for side effect costs
SENSITIVITY = {
    "glucose":     0.15,
    "creatinine":  0.30,  # kidneys most sensitive
    "heart_rate":  0.10,
    "systolic_bp": 0.20,
    "spo2":        0.25,  # oxygen critical
}

VITAL_NAMES = [
    "glucose", "creatinine", "heart_rate",
    "systolic_bp", "spo2",
]


class ClinicalPatientEnv(gym.Env):
    """
    Gymnasium environment for clinical treatment
    policy learning.

    The RL agent learns to select treatments that
    improve patient survival by maximising causal
    effect on target outcomes while minimising
    side effect costs.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        patient_states: dict,
        cox_model=None,
        max_steps: int = 10,
    ):
        super().__init__()

        self.patient_states = patient_states
        self.cox_model = cox_model
        self.max_steps = max_steps

        self.observation_space = spaces.Box(
            low=-1.0,
            high=2.0,
            shape=(STATE_DIM,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(N_ACTIONS)

        self.current_state = None
        self.current_patient_id = None
        self.step_count = 0
        self.episode_reward = 0.0
        self.patient_ids = list(patient_states.keys())

        logger.info(
            "ClinicalPatientEnv initialized: "
            "%d patients %d actions",
            len(patient_states), N_ACTIONS,
        )

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ):
        super().reset(seed=seed)

        # Random patient each episode
        idx = self.np_random.integers(
            0, len(self.patient_ids)
        )
        self.current_patient_id = self.patient_ids[idx]
        self.current_state = self.patient_states[
            self.current_patient_id
        ].copy()

        self.step_count = 0
        self.episode_reward = 0.0

        return self.current_state, {}

    def step(self, action: int):
        action_def = ACTIONS[action]
        old_state = self.current_state.copy()

        # Apply treatment effect to state
        new_state = self.current_state.copy()

        if action_def["target_idx"] is not None:
            new_state[action_def["target_idx"]] += (
                action_def["magnitude"]
            )
            new_state[action_def["target_idx"]] = float(
                np.clip(
                    new_state[action_def["target_idx"]],
                    0.0, 1.0,
                )
            )

        # Apply side effects
        for vital, delta in action_def[
            "side_effects"
        ].items():
            vital_idx = VITAL_NAMES.index(vital)
            new_state[vital_idx] = float(
                np.clip(
                    new_state[vital_idx] + delta,
                    0.0, 1.0,
                )
            )

        # Compute reward
        reward = self._compute_reward(
            old_state, new_state, action_def
        )

        self.current_state = new_state
        self.step_count += 1
        self.episode_reward += reward

        # Termination conditions
        terminated = False
        truncated = self.step_count >= self.max_steps

        # Crisis: creatinine or risk too high
        if new_state[1] > 0.9:  # creatinine very high
            terminated = True
            reward -= 1.0  # crisis penalty

        return new_state, reward, terminated, truncated, {}

    def _compute_reward(
        self,
        old_state: np.ndarray,
        new_state: np.ndarray,
        action_def: dict,
    ) -> float:
        """
        reward = primary_benefit
               - side_effect_cost
               + survival_improvement_bonus
        """
        # Primary benefit: improvement in target vital
        if action_def["target_idx"] is not None:
            target_idx = action_def["target_idx"]
            # Improvement = old - new (lower is better
            # for creatinine, glucose, sbp, hr)
            # Higher is better for spo2
            if action_def["target"] == "spo2":
                benefit = (
                    new_state[target_idx]
                    - old_state[target_idx]
                ) * 2.0
            else:
                benefit = (
                    old_state[target_idx]
                    - new_state[target_idx]
                ) * 2.0
        else:
            benefit = 0.0

        # Side effect cost
        side_cost = 0.0
        for vital, delta in action_def[
            "side_effects"
        ].items():
            sensitivity = SENSITIVITY.get(vital, 0.1)
            side_cost += abs(delta) * sensitivity

        # Survival improvement bonus
        survival_bonus = 0.0
        if self.cox_model is not None:
            old_risk = self.cox_model.predict_risk(
                old_state
            )
            new_risk = self.cox_model.predict_risk(
                new_state
            )
            survival_bonus = (old_risk - new_risk) * 2.0

        reward = benefit - side_cost + survival_bonus
        return float(reward)

    def get_action_meanings(self) -> list:
        return [a["name"] for a in ACTIONS]