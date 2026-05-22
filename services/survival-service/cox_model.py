"""
Deep Cox Proportional Hazards Model

Architecture:
  Input:  11-dim patient state vector
          (5 vitals + 6 causal effects)
  Hidden: Linear(11,64) -> BN -> ReLU -> Dropout(0.2)
          Linear(64,32)  -> BN -> ReLU -> Dropout(0.2)
  Output: Linear(32,1) -> scalar risk score theta(x)

Survival function:
  S(t|x) = S0(t)^exp(theta(x))
  S0(t)  = baseline survival (Breslow estimator)

Loss: Cox partial likelihood (negative log)
  L = -sum_i [theta(x_i) - log sum_{j in R(t_i)} exp(theta(x_j))]
  where R(t_i) = risk set at time t_i

Synthetic survival labels:
  risk_raw = 0.4*creatinine_norm
           + 0.3*(1 - spo2_norm)
           + 0.2*glucose_norm
           + 0.1*systolic_bp_norm
  T ~ Exponential(lambda = 0.5 + risk_raw * 2)
  C ~ Uniform(60, 365) days
  observed_time = min(T, C)
  event = 1 if T <= C else 0
"""

import logging
import time
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

logger = logging.getLogger("axiom.survival.cox")

HIDDEN1   = 64
HIDDEN2   = 32
DROPOUT   = 0.2
LR        = 1e-3
EPOCHS    = 100
SEED      = 42


class CoxPHNetwork(nn.Module):
    """Deep Cox risk network."""

    def __init__(self, input_dim: int = 11):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, HIDDEN1),
            nn.BatchNorm1d(HIDDEN1),
            nn.ReLU(),
            nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN1, HIDDEN2),
            nn.BatchNorm1d(HIDDEN2),
            nn.ReLU(),
            nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def cox_partial_likelihood_loss(
    risk_scores: torch.Tensor,
    times: torch.Tensor,
    events: torch.Tensor,
) -> torch.Tensor:
    """
    Cox partial likelihood loss.

    For each event i:
      L_i = risk_score_i - log(sum_{j: t_j >= t_i} exp(risk_score_j))

    Total loss = -mean(L_i for all events)
    """
    # Sort by descending time
    sort_idx = torch.argsort(times, descending=True)
    risk_scores = risk_scores[sort_idx]
    events = events[sort_idx]

    # Log-sum-exp of risk scores for risk sets
    log_cumsum_exp = torch.logcumsumexp(
        risk_scores, dim=0
    )

    # Loss only for uncensored events
    event_mask = events.bool()
    if event_mask.sum() == 0:
        return torch.tensor(0.0, requires_grad=True)

    loss = -(
        risk_scores[event_mask]
        - log_cumsum_exp[event_mask]
    ).mean()

    return loss


class BreslowEstimator:
    """
    Breslow estimator for baseline survival S0(t).
    Non-parametric estimate from training data.
    """

    def __init__(self):
        self.baseline_times = []
        self.baseline_hazard = []
        self.baseline_survival = []

    def fit(
        self,
        risk_scores: np.ndarray,
        times: np.ndarray,
        events: np.ndarray,
    ):
        """Compute baseline cumulative hazard."""
        # Sort by time
        sort_idx = np.argsort(times)
        times_sorted = times[sort_idx]
        events_sorted = events[sort_idx]
        risk_sorted = risk_scores[sort_idx]

        n = len(times_sorted)
        unique_event_times = times_sorted[
            events_sorted == 1
        ]
        unique_event_times = np.unique(unique_event_times)

        baseline_hazard = []
        for t in unique_event_times:
            # Number of events at time t
            d_t = np.sum(
                (times_sorted == t) & (events_sorted == 1)
            )
            # Sum of exp(risk) for all at risk at time t
            risk_set = np.exp(risk_sorted[times_sorted >= t])
            h_t = d_t / (risk_set.sum() + 1e-8)
            baseline_hazard.append(h_t)

        self.baseline_times = unique_event_times
        self.baseline_hazard = np.array(baseline_hazard)
        self.baseline_survival = np.exp(
            -np.cumsum(self.baseline_hazard)
        )

    def predict_survival(
        self,
        risk_score: float,
        eval_times: list,
    ) -> list:
        """
        S(t|x) = S0(t)^exp(risk_score)
        Returns survival probabilities at eval_times.
        """
        if len(self.baseline_times) == 0:
            return [1.0] * len(eval_times)

        exp_risk = np.exp(risk_score)
        survival_probs = []

        for t in eval_times:
            # Find latest baseline time <= t
            idx = np.searchsorted(
                self.baseline_times, t, side="right"
            ) - 1

            if idx < 0:
                s0 = 1.0
            elif idx >= len(self.baseline_survival):
                s0 = self.baseline_survival[-1]
            else:
                s0 = self.baseline_survival[idx]

            s_t = s0 ** exp_risk
            survival_probs.append(float(s_t))

        return survival_probs


def generate_synthetic_survival_labels(
    states: np.ndarray,
    seed: int = SEED,
) -> tuple:
    """
    Generate synthetic survival labels from state vectors.

    Risk is driven by:
      - High creatinine (dim 1) → shorter survival
      - Low spo2 (dim 4) → shorter survival
      - High glucose (dim 0) → shorter survival
      - High systolic_bp (dim 3) → shorter survival

    Returns (times, events) arrays.
    """
    np.random.seed(seed)
    n = len(states)

    # Clinical risk score from normalized vitals
    creatinine_norm = states[:, 1]
    spo2_norm       = states[:, 4]
    glucose_norm    = states[:, 0]
    sbp_norm        = states[:, 3]

    risk_raw = (
        0.4 * creatinine_norm
        + 0.3 * (1.0 - spo2_norm)
        + 0.2 * glucose_norm
        + 0.1 * sbp_norm
    )

    # Survival time from exponential distribution
    # Higher risk → shorter expected survival
    lambda_rate = 0.5 + risk_raw * 3.0
    survival_times = np.random.exponential(
        1.0 / lambda_rate
    ) * 365  # scale to days

    # Censoring time (administrative censoring at 1 year)
    censoring_times = np.random.uniform(90, 365, n)

    # Observed time and event indicator
    observed_times = np.minimum(
        survival_times, censoring_times
    )
    events = (survival_times <= censoring_times).astype(
        np.float32
    )

    logger.info(
        "Synthetic labels: n=%d events=%d (%.0f%%) "
        "median_time=%.0f days",
        n,
        int(events.sum()),
        100 * events.mean(),
        np.median(observed_times),
    )

    return (
        observed_times.astype(np.float32),
        events.astype(np.float32),
    )


class DeepCoxModel:
    """
    Full Deep Cox model with training + prediction.
    """

    def __init__(self, input_dim: int = 11):
        torch.manual_seed(SEED)
        self.network = CoxPHNetwork(input_dim)
        self.breslow = BreslowEstimator()
        self.optimizer = optim.Adam(
            self.network.parameters(), lr=LR
        )
        self.is_trained = False
        self.train_loss_history = []
        self.concordance_index = None

    def train(
        self,
        states: np.ndarray,
        times: np.ndarray,
        events: np.ndarray,
        epochs: int = EPOCHS,
    ) -> dict:
        """Train the Cox network."""
        start = time.perf_counter()

        X = torch.tensor(states, dtype=torch.float32)
        T = torch.tensor(times, dtype=torch.float32)
        E = torch.tensor(events, dtype=torch.float32)

        self.network.train()
        losses = []

        for epoch in range(epochs):
            self.optimizer.zero_grad()
            risk_scores = self.network(X)
            loss = cox_partial_likelihood_loss(
                risk_scores, T, E
            )
            loss.backward()
            self.optimizer.step()
            losses.append(float(loss.item()))

            if (epoch + 1) % 20 == 0:
                logger.info(
                    "Cox epoch %d/%d loss=%.4f",
                    epoch + 1, epochs, loss.item(),
                )

        # Fit Breslow estimator on training data
        self.network.eval()
        with torch.no_grad():
            risk_np = self.network(X).numpy()

        self.breslow.fit(risk_np, times, events)

        # Concordance index (C-index)
        self.concordance_index = self._compute_cindex(
            risk_np, times, events
        )

        elapsed = time.perf_counter() - start
        self.train_loss_history = losses
        self.is_trained = True

        logger.info(
            "Cox trained: epochs=%d "
            "final_loss=%.4f c_index=%.3f "
            "time=%.1fs",
            epochs,
            losses[-1],
            self.concordance_index,
            elapsed,
        )

        return {
            "epochs": epochs,
            "final_loss": round(losses[-1], 4),
            "initial_loss": round(losses[0], 4),
            "c_index": round(
                self.concordance_index, 3
            ),
            "train_time_seconds": round(elapsed, 1),
            "n_patients": len(states),
            "n_events": int(events.sum()),
        }

    def predict_risk(
        self, state: np.ndarray
    ) -> float:
        """Predict risk score for a single patient."""
        self.network.eval()
        with torch.no_grad():
            x = torch.tensor(
                state, dtype=torch.float32
            ).unsqueeze(0)
            risk = self.network(x).item()
        return float(risk)

    def predict_survival_curve(
        self,
        state: np.ndarray,
        eval_times: list = None,
    ) -> dict:
        """
        Predict survival curve S(t) for a patient.
        Returns probabilities at standard time points.
        """
        if eval_times is None:
            eval_times = [30, 60, 90, 180, 365]

        risk_score = self.predict_risk(state)
        survival_probs = self.breslow.predict_survival(
            risk_score, eval_times
        )

        # Median survival (time at S(t) = 0.5)
        median_survival = self._estimate_median_survival(
            risk_score
        )

        # Confidence bands (±1 std approximation)
        ci_width = 0.05 * (1 - np.array(survival_probs))
        lower = np.clip(
            np.array(survival_probs) - ci_width, 0, 1
        )
        upper = np.clip(
            np.array(survival_probs) + ci_width, 0, 1
        )

        return {
            "risk_score": round(risk_score, 4),
            "survival_probabilities": {
                str(t): round(p, 4)
                for t, p in zip(eval_times, survival_probs)
            },
            "confidence_bands": {
                str(t): {
                    "lower": round(float(lower[i]), 4),
                    "upper": round(float(upper[i]), 4),
                }
                for i, t in enumerate(eval_times)
            },
            "median_survival_days": median_survival,
            "eval_times": eval_times,
        }

    def _estimate_median_survival(
        self, risk_score: float
    ) -> Optional[int]:
        """Estimate median survival time."""
        times_dense = list(range(1, 366))
        probs = self.breslow.predict_survival(
            risk_score, times_dense
        )
        for t, p in zip(times_dense, probs):
            if p <= 0.5:
                return t
        return None

    def _compute_cindex(
        self,
        risk_scores: np.ndarray,
        times: np.ndarray,
        events: np.ndarray,
    ) -> float:
        """Compute Harrell's concordance index."""
        concordant = 0
        discordant = 0
        tied = 0

        n = len(times)
        for i in range(n):
            if events[i] == 0:
                continue
            for j in range(n):
                if times[j] <= times[i]:
                    continue
                if risk_scores[i] > risk_scores[j]:
                    concordant += 1
                elif risk_scores[i] < risk_scores[j]:
                    discordant += 1
                else:
                    tied += 1

        total = concordant + discordant + tied
        if total == 0:
            return 0.5
        return (concordant + 0.5 * tied) / total