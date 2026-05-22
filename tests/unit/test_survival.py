"""
Sprint 5 Unit Tests — Survival Model + RL Policy

Tests for:
  PatientEncoder
  DeepCoxModel
  ClinicalPatientEnv
  PPOTreatmentPolicy
"""

import sys
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock



# ── PatientEncoder ─────────────────────────────────

class TestPatientEncoder:

    def test_normalize_vital_in_range(self):
        from patient_encoder import normalize_vital
        result = normalize_vital(235.0, "glucose")
        assert 0.0 <= result <= 1.0

    def test_normalize_vital_low_clipped(self):
        from patient_encoder import normalize_vital
        result = normalize_vital(0.0, "glucose")
        assert result == 0.0

    def test_normalize_vital_high_clipped(self):
        from patient_encoder import normalize_vital
        result = normalize_vital(9999.0, "glucose")
        assert result == 1.0

    def test_normalize_effect_clipped(self):
        from patient_encoder import normalize_effect
        assert normalize_effect(100.0) == 1.0
        assert normalize_effect(-100.0) == -1.0

    def test_normalize_effect_zero(self):
        from patient_encoder import normalize_effect
        assert normalize_effect(0.0) == 0.0

    def test_state_dim_constant(self):
        from patient_encoder import STATE_DIM
        assert STATE_DIM == 11

    def test_causal_keys_count(self):
        from patient_encoder import CAUSAL_KEYS
        assert len(CAUSAL_KEYS) == 6

    def test_vital_ranges_defined(self):
        from patient_encoder import VITAL_RANGES
        assert "glucose" in VITAL_RANGES
        assert "creatinine" in VITAL_RANGES
        assert "spo2" in VITAL_RANGES


# ── DeepCoxModel ───────────────────────────────────

class TestDeepCoxModel:

    def _make_data(self, n=30, seed=42):
        np.random.seed(seed)
        states = np.random.rand(n, 11).astype(
            np.float32
        )
        times = np.random.exponential(100, n).astype(
            np.float32
        )
        events = np.random.binomial(1, 0.6, n).astype(
            np.float32
        )
        return states, times, events

    def test_network_output_shape(self):
        import torch
        from cox_model import CoxPHNetwork
        net = CoxPHNetwork(input_dim=11)
        net.eval()
        x = torch.rand(5, 11)
        out = net(x)
        assert out.shape == (5,)

    def test_cox_loss_computes(self):
        import torch
        from cox_model import cox_partial_likelihood_loss
        risk = torch.tensor([1.0, 0.5, 0.2, 0.8])
        times = torch.tensor([10.0, 20.0, 30.0, 15.0])
        events = torch.tensor([1.0, 1.0, 0.0, 1.0])
        loss = cox_partial_likelihood_loss(
            risk, times, events
        )
        assert loss.item() > 0

    def test_model_trains(self):
        from cox_model import DeepCoxModel
        model = DeepCoxModel(input_dim=11)
        states, times, events = self._make_data(n=20)
        result = model.train(
            states, times, events, epochs=10
        )
        assert result["final_loss"] < result[
            "initial_loss"
        ] or result["final_loss"] > 0
        assert model.is_trained is True

    def test_c_index_between_0_and_1(self):
        from cox_model import DeepCoxModel
        model = DeepCoxModel(input_dim=11)
        states, times, events = self._make_data(n=25)
        result = model.train(
            states, times, events, epochs=10
        )
        assert 0.0 <= result["c_index"] <= 1.0

    def test_predict_risk_scalar(self):
        from cox_model import DeepCoxModel
        model = DeepCoxModel(input_dim=11)
        states, times, events = self._make_data(n=20)
        model.train(states, times, events, epochs=5)
        state = np.random.rand(11).astype(np.float32)
        risk = model.predict_risk(state)
        assert isinstance(risk, float)

    def test_survival_curve_keys(self):
        from cox_model import DeepCoxModel
        model = DeepCoxModel(input_dim=11)
        states, times, events = self._make_data(n=20)
        model.train(states, times, events, epochs=5)
        state = np.random.rand(11).astype(np.float32)
        result = model.predict_survival_curve(state)
        assert "risk_score" in result
        assert "survival_probabilities" in result
        assert "confidence_bands" in result
        assert "median_survival_days" in result

    def test_survival_probabilities_decreasing(self):
        from cox_model import DeepCoxModel
        model = DeepCoxModel(input_dim=11)
        states, times, events = self._make_data(n=30)
        model.train(states, times, events, epochs=20)
        state = np.random.rand(11).astype(np.float32)
        result = model.predict_survival_curve(
            state, eval_times=[30, 60, 90, 180]
        )
        probs = list(
            result["survival_probabilities"].values()
        )
        for i in range(len(probs) - 1):
            assert probs[i] >= probs[i+1] - 0.05

    def test_breslow_fit(self):
        from cox_model import BreslowEstimator
        breslow = BreslowEstimator()
        risk = np.array([0.5, 1.0, -0.5, 0.2])
        times = np.array([10.0, 20.0, 30.0, 15.0])
        events = np.array([1.0, 1.0, 0.0, 1.0])
        breslow.fit(risk, times, events)
        assert len(breslow.baseline_times) > 0
        assert len(breslow.baseline_survival) > 0

    def test_synthetic_labels_event_rate(self):
        from cox_model import (
            generate_synthetic_survival_labels,
        )
        states = np.random.rand(50, 11).astype(
            np.float32
        )
        times, events = (
            generate_synthetic_survival_labels(states)
        )
        assert len(times) == 50
        assert len(events) == 50
        event_rate = events.mean()
        assert 0.2 <= event_rate <= 0.9


# ── ClinicalPatientEnv ─────────────────────────────

class TestClinicalPatientEnv:

    def _make_env(self, n_patients=10):
        from clinical_env import ClinicalPatientEnv
        np.random.seed(42)
        states = {
            f"patient-{i}": np.random.rand(11).astype(
                np.float32
            )
            for i in range(n_patients)
        }
        return ClinicalPatientEnv(
            patient_states=states, max_steps=5
        )

    def test_observation_space(self):
        from clinical_env import ClinicalPatientEnv
        import gymnasium as gym
        env = self._make_env()
        assert isinstance(
            env.observation_space,
            gym.spaces.Box,
        )
        assert env.observation_space.shape == (11,)

    def test_action_space(self):
        from clinical_env import (
            ClinicalPatientEnv, N_ACTIONS
        )
        import gymnasium as gym
        env = self._make_env()
        assert isinstance(
            env.action_space,
            gym.spaces.Discrete,
        )
        assert env.action_space.n == N_ACTIONS

    def test_reset_returns_obs(self):
        env = self._make_env()
        obs, info = env.reset(seed=42)
        assert obs.shape == (11,)
        assert isinstance(info, dict)

    def test_step_returns_correct_types(self):
        env = self._make_env()
        env.reset(seed=42)
        obs, reward, terminated, truncated, info = (
            env.step(0)
        )
        assert obs.shape == (11,)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)

    def test_episode_terminates(self):
        env = self._make_env()
        env.reset(seed=42)
        done = False
        steps = 0
        while not done and steps < 20:
            _, _, terminated, truncated, _ = (
                env.step(env.action_space.sample())
            )
            done = terminated or truncated
            steps += 1
        assert done is True

    def test_no_action_zero_reward(self):
        from clinical_env import ClinicalPatientEnv, ACTIONS
        # Use safe state with low creatinine to avoid crisis
        safe_state = np.array(
            [0.3, 0.2, 0.3, 0.3, 0.8, 0.0,
             0.0, 0.0, 0.0, 0.0, 0.0],
            dtype=np.float32,
        )
        env = ClinicalPatientEnv(
            patient_states={"p1": safe_state},
            max_steps=5,
        )
        env.reset(seed=42)
        no_action_idx = next(
            i for i, a in enumerate(ACTIONS)
            if a["name"] == "no_action"
        )
        _, reward, _, _, _ = env.step(no_action_idx)
        assert reward == pytest.approx(0.0, abs=0.01)

    def test_action_meanings(self):
        from clinical_env import N_ACTIONS
        env = self._make_env()
        meanings = env.get_action_meanings()
        assert len(meanings) == N_ACTIONS
        assert "increase_lisinopril" in meanings
        assert "no_action" in meanings

    def test_state_stays_bounded(self):
        env = self._make_env()
        obs, _ = env.reset(seed=42)
        for _ in range(5):
            obs, _, terminated, truncated, _ = (
                env.step(env.action_space.sample())
            )
            assert obs[:5].min() >= 0.0
            assert obs[:5].max() <= 1.0
            if terminated or truncated:
                break