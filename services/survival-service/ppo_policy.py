"""
PPO Treatment Policy

Uses Stable Baselines3 PPO to learn optimal
treatment sequences for clinical patients.

The policy learns:
  - Which treatment to apply given patient state
  - How to maximise cumulative survival reward
  - Per-subgroup strategies (CKD vs diabetic vs COPD)

Architecture (SB3 default MlpPolicy):
  Actor:  Linear(11,64) -> ReLU -> Linear(64,64) -> ReLU -> Linear(64,6)
  Critic: Linear(11,64) -> ReLU -> Linear(64,64) -> ReLU -> Linear(64,1)

PPO hyperparameters:
  learning_rate:  3e-4
  n_steps:        256   (steps before update)
  batch_size:     64
  n_epochs:       10    (update epochs per rollout)
  gamma:          0.99  (discount factor)
  clip_range:     0.2   (PPO clipping)
  total_timesteps: 10000
"""

import logging
import time
from typing import Optional

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import (
    make_vec_env,
)
from stable_baselines3.common.evaluation import (
    evaluate_policy,
)

from clinical_env import ClinicalPatientEnv, ACTIONS

logger = logging.getLogger("axiom.survival.ppo")

PPO_HYPERPARAMS = {
    "learning_rate":   3e-4,
    "n_steps":         256,
    "batch_size":      64,
    "n_epochs":        10,
    "gamma":           0.99,
    "clip_range":      0.2,
    "verbose":         0,
}

TOTAL_TIMESTEPS = 10_000


class PPOTreatmentPolicy:
    """
    PPO treatment policy for clinical patients.
    Wraps SB3 PPO with clinical-specific utilities.
    """

    def __init__(self):
        self.model = None
        self.is_trained = False
        self.training_timesteps = 0
        self.mean_reward = None
        self.std_reward = None
        self.patient_states = None

    def train(
        self,
        patient_states: dict,
        cox_model=None,
        total_timesteps: int = TOTAL_TIMESTEPS,
    ) -> dict:
        """
        Train PPO policy on clinical environment.

        Args:
            patient_states: {patient_id: state_vector}
            cox_model: trained DeepCoxModel for survival bonus
            total_timesteps: training steps

        Returns:
            Training summary dict
        """
        start = time.perf_counter()
        self.patient_states = patient_states

        logger.info(
            "Training PPO: patients=%d timesteps=%d",
            len(patient_states), total_timesteps,
        )

        # Create environment
        env = ClinicalPatientEnv(
            patient_states=patient_states,
            cox_model=cox_model,
            max_steps=10,
        )

        # Initialize PPO
        self.model = PPO(
            policy="MlpPolicy",
            env=env,
            **PPO_HYPERPARAMS,
        )

        # Train
        self.model.learn(
            total_timesteps=total_timesteps,
            progress_bar=False,
        )

        # Evaluate
        mean_reward, std_reward = evaluate_policy(
            self.model,
            env,
            n_eval_episodes=20,
            deterministic=True,
        )

        self.mean_reward = float(mean_reward)
        self.std_reward = float(std_reward)
        self.is_trained = True
        self.training_timesteps = total_timesteps

        elapsed = time.perf_counter() - start

        logger.info(
            "PPO trained: mean_reward=%.3f "
            "std=%.3f time=%.1fs",
            mean_reward, std_reward, elapsed,
        )

        return {
            "total_timesteps": total_timesteps,
            "mean_reward": round(mean_reward, 4),
            "std_reward": round(std_reward, 4),
            "train_time_seconds": round(elapsed, 1),
            "n_patients": len(patient_states),
            "hyperparams": PPO_HYPERPARAMS,
        }

    def recommend(
        self,
        state: np.ndarray,
        patient_id: str = None,
        top_k: int = 3,
    ) -> dict:
        """
        Get treatment recommendation for a patient.

        Returns ranked list of actions with
        expected rewards from the trained policy.
        """
        if not self.is_trained or self.model is None:
            return {
                "error": "PPO model not trained"
            }

        # Get policy action (deterministic)
        obs = state.reshape(1, -1).astype(np.float32)
        action, _ = self.model.predict(
            obs, deterministic=True
        )
        best_action = int(action[0])

        # Get Q-values for all actions by
        # simulating each action in a temp env
        action_rewards = []
        if self.patient_states:
            temp_env = ClinicalPatientEnv(
                patient_states=self.patient_states,
                max_steps=1,
            )
            for a in range(len(ACTIONS)):
                temp_env.current_state = state.copy()
                temp_env.step_count = 0
                _, reward, _, _, _ = temp_env.step(a)
                action_rewards.append({
                    "action_id": a,
                    "action_name": ACTIONS[a]["name"],
                    "target": ACTIONS[a]["target"],
                    "immediate_reward": round(reward, 4),
                })

            action_rewards.sort(
                key=lambda x: x["immediate_reward"],
                reverse=True,
            )
        else:
            action_rewards = [
                {
                    "action_id": best_action,
                    "action_name": ACTIONS[
                        best_action
                    ]["name"],
                    "target": ACTIONS[best_action][
                        "target"
                    ],
                    "immediate_reward": 0.0,
                }
            ]

        return {
            "patient_id": patient_id,
            "recommended_action": ACTIONS[
                best_action
            ]["name"],
            "recommended_action_id": best_action,
            "target_vital": ACTIONS[best_action][
                "target"
            ],
            "ranked_actions": action_rewards[:top_k],
            "policy": "ppo",
            "deterministic": True,
        }

    def status(self) -> dict:
        return {
            "is_trained": self.is_trained,
            "training_timesteps": self.training_timesteps,
            "mean_reward": self.mean_reward,
            "std_reward": self.std_reward,
            "n_actions": len(ACTIONS),
            "action_space": [
                a["name"] for a in ACTIONS
            ],
        }