# Axiom v0.5.0 — Survival Model + RL Treatment Optimiser

**Released:** 2026-05-22
**Sprint:** 5 of 12
**Days:** 29-35

---

## What Was Built

Sprint 5 adds the intelligence layer to Axiom.
Two models answer questions no correlation-based
system can answer:

  "How long will this patient survive?"
  "What is the optimal treatment sequence?"

---

## Model 1: Deep Cox Proportional Hazards (PyTorch)

Architecture: Linear(11,64)->BN->ReLU->Dropout
              Linear(64,32)->BN->ReLU->Dropout
              Linear(32,1) -> risk score

Input: 11-dim patient state vector
  [glucose, creatinine, heart_rate, systolic_bp, spo2]
  + [6 causal effect sizes from Sprint 2 graph]

Output: survival curve S(t) with confidence bands

Baseline hazard: Breslow non-parametric estimator
Synthetic labels: risk from creatinine(0.4) + spo2(0.3)
                  + glucose(0.2) + sbp(0.1)

Results for Amit Singh (CKD):
  risk_score:      0.9919 (HIGH)
  S(30 days):      82.2%
  S(90 days):      43.1%
  S(180 days):     19.2%
  median survival: 72 days
  C-index:         0.792

---

## Model 2: PPO Treatment Policy (Stable Baselines3)

Environment: ClinicalPatientEnv (Gymnasium)
  State:   11-dim patient vector
  Actions: 6 treatment choices
    0: increase_lisinopril   (targets systolic_bp)
    1: increase_furosemide   (targets creatinine)
    2: increase_metformin    (targets glucose)
    3: add_aspirin           (targets heart_rate)
    4: lifestyle_counselling (mild all vitals)
    5: no_action             (baseline)
  Reward: primary_benefit - side_effect_cost
          + survival_improvement_bonus

PPO hyperparameters:
  learning_rate: 3e-4
  n_steps:       256
  batch_size:    64
  n_epochs:      10
  gamma:         0.99
  timesteps:     10,000

Results for Amit Singh (CKD):
  Recommended: increase_lisinopril
  Reward:      0.152
  Ranked:
    1. lisinopril   0.152
    2. metformin    0.119
    3. furosemide   0.072
    4. aspirin      0.058
    5. lifestyle    0.037
    6. no_action    0.000

Clinically correct: lisinopril is first-line for CKD+HTN.
The RL agent learned this from causal graph effects,
not from hardcoded clinical rules.

---

## Integration Pipeline

Single API call returns everything:
  GET /causal/full/{patient_id}

  Returns:
    causal_graph:     Sprint 2 (7 nodes, 10 edges)
    survival:         Sprint 5 Cox (risk=0.992, median=72d)
    recommendation:   Sprint 5 PPO (lisinopril, reward=0.152)
    zk_proof_hash:    Sprint 3 (proven, tamper-evident)
    audit_logged:     Sprint 3 (full lineage stored)

---

## ZK Proof per Recommendation

Every PPO recommendation automatically:
  1. Generates ZK proof via Sprint 3 ZK service
  2. Logs to audit trail in PostgreSQL
  3. Returns proof_hash in API response

  zk_proven:    true
  audit_logged: true

---

## Patient Encoder (11-dim state vector)

  [0]  glucose_norm       (70-400 mg/dL)
  [1]  creatinine_norm    (0.5-5.0 mg/dL)
  [2]  heart_rate_norm    (40-150 bpm)
  [3]  systolic_bp_norm   (80-200 mmHg)
  [4]  spo2_norm          (80-100%)
  [5]  glucose->creatinine effect
  [6]  systolic_bp->creatinine effect
  [7]  systolic_bp->heart_rate effect
  [8]  heart_rate->spo2 effect
  [9]  creatinine->spo2 effect
  [10] glucose->heart_rate effect

The causal graph IS the feature engineering.

---

## Test Summary

| Suite            | Tests | Passed | Failed | Time  |
|------------------|-------|--------|--------|-------|
| Causal Engine    | 28    | 28     | 0      | —     |
| ZK Trust Layer   | 15    | 15     | 0      | —     |
| Federated        | 23    | 23     | 0      | —     |
| Survival + RL    | 25    | 25     | 0      | —     |
| Total            | 91    | 91     | 0      | 4.34s |

---

## Service Map

| Service        | Port  | Technology        | Sprint |
|----------------|-------|-------------------|--------|
| FHIR Adapter   | 8080  | Java Spring Boot  | 1      |
| Normalisation  | 8086  | Python FastAPI    | 1      |
| Causal Engine  | 8081  | Python FastAPI    | 2      |
| ZK Service     | 8084  | Python FastAPI    | 3      |
| Federated      | 8085  | Python FastAPI    | 4      |
| Survival       | 8082  | Python FastAPI    | 5      |
| PostgreSQL     | 5439  | postgres:15       | 1      |
| MongoDB        | 27018 | mongo:7           | 1      |
| Redis          | 6380  | redis:7           | 1      |
| Kafka          | 9094  | Confluent 7.4     | 1      |
| Prometheus     | 9095  | prom 2.45         | 1      |
| Grafana        | 3001  | grafana 10.1      | 1      |

---

## Next Sprint

Sprint 6 — NLP + Anomaly Detection
  BioBERT clinical note processing
  Named entity recognition (conditions, drugs)
  Vital sign anomaly detection
  Alert generation pipeline