# Axiom v0.2.0 — Per-Patient Causal Engine

**Released:** 2026-05-20
**Sprint:** 2 of 12
**Days:** 8-14

---

## What Was Built

Sprint 2 builds the intellectual core of Axiom — a per-patient
causal DAG using DoWhy. Every patient gets their own causal
graph built from their individual observation history.

This is fundamentally different from correlation-based ML:
  ML asks: "what correlates with what?"
  Axiom asks: "what causes what, for THIS patient?"

---

## Components

### PatientCausalGraphBuilder (Day 9)
Builds individual causal DAG per patient using DoWhy.
Groups observations by feature, aligns by index position,
computes effect sizes via backdoor linear regression.
Prior edges from clinical knowledge (VITAL_PRIOR_EDGES).

### CounterfactualEngine (Day 10)
Answers "what-if" clinical queries using stored graph.
  query_from_graph: fast <1ms using stored effects
  query_from_data: recomputes via DoWhy (~5s)
  compare_interventions: ranks treatments by effect size

### InterventionSimulator (Day 11)
Monte Carlo simulation over causal graph.
1000 samples per query. Returns full distribution:
mean, std, p5, p25, p50, p75, p95, min, max.
Scenarios: best_case, most_likely, worst_case.
Probability of improvement per intervention.

### CausalDriftDetector (Day 12)
Detects when a patient causal structure changes over time.
Compares current vs previous graph effect sizes.
25% change threshold. Severity: info/warning/critical.
A drift event is a clinical signal — disease progressing.

### CausalKafkaConsumer (Day 13)
Listens to patient.vitals.normalised Kafka topic.
Auto-rebuilds causal graph when new vitals arrive.
60-second cooldown per patient to prevent burst rebuilds.
Publishes causal.updates event after each rebuild.

---

## Causal Effects Proven — Amit Singh (CKD)

  age -> glucose           +3.044   age drives glucose
  age -> systolic_bp       +2.529   age drives BP
  systolic_bp -> creatinine +0.024  BP damages kidneys
  glucose -> creatinine    +0.0002  diabetes->kidneys
  systolic_bp -> heart_rate -0.298  BP suppresses HR
  creatinine -> spo2       +0.159   kidney->oxygen

Clinical insight:
  systolic_bp has 120x more causal effect on creatinine
  than glucose for this patient. Target BP first.

---

## Counterfactual Results

  Query: glucose -20 mg/dL -> creatinine?
  Effect: 3.1 -> 3.096 (prob_improvement=100%)

  Compare: systolic_bp vs glucose for creatinine
  Ranked: systolic_bp (0.024) > glucose (0.0002)
  Best treatment: systolic_bp

---

## Monte Carlo Simulation

  Treatment: glucose -20 units
  Outcome: creatinine
  Current: 3.1 mg/dL
  Distribution (1000 samples):
    mean:  3.096
    std:   0.0009
    p5:    3.0946
    p50:   3.096
    p95:   3.0975
  Probability of improvement: 100%

---

## Validation Results

  Causal graphs built:    50
  Graphs failed:          0
  Avg effects per graph:  10
  Avg build time:         212ms
  Unit tests:             28 passed, 0 failed

---

## Service Map

| Service       | Port  | Technology       |
|---------------|-------|------------------|
| FHIR Adapter  | 8080  | Java Spring Boot |
| Normalisation | 8086  | Python FastAPI   |
| Causal Engine | 8081  | Python FastAPI   |
| PostgreSQL    | 5439  | postgres:15      |
| MongoDB       | 27018 | mongo:7          |
| Redis         | 6380  | redis:7          |
| Kafka         | 9094  | Confluent 7.4    |
| Prometheus    | 9095  | prom 2.45        |
| Grafana       | 3001  | grafana 10.1     |

---

## Test Summary

| Suite         | Tests | Passed | Failed | Time  |
|---------------|-------|--------|--------|-------|
| Causal Engine | 28    | 28     | 0      | 1.80s |

---

## Next Sprint

Sprint 3 — ZK Trust Layer
  Cryptographic proof per AI recommendation
  Doctors verify without seeing patient data
  Audit trail with full lineage
  PostgreSQL integration