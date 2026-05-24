# Axiom API Reference

## GraphQL  POST http://localhost:4000/graphql

### Full Analysis
    query { fullAnalysis(patientId: "3319a93d") {
      causalGraph { nodeList effectSizes zkIntegrityProof }
      survival { survivalProbability medianSurvivalDays riskScore }
      recommendation { action reward zkProven }
    }}

### Counterfactual
    mutation { runCounterfactual(patientId: "3319a93d", intervention: "lisinopril") {
      creatinine sbp glucose heartRate survivalDelta zkProof
    }}

## WebSocket  ws://localhost:4001/graphql
    subscription { patientAlerts(patientId: "3319a93d") {
      severity vital value threshold message
    }}

## REST

| Service | Endpoint | Method |
|---------|----------|--------|
| Causal Engine | /causal/graph/{id} | GET |
| Causal Engine | /causal/counterfactual | POST |
| Survival | /survival/{id} | GET |
| Survival | /recommendation/{id} | GET |
| ZK Service | /zk/prove | POST |
| ZK Service | /zk/verify | POST |

## Benchmarks

| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| Causal graph | 212ms | 380ms | 520ms |
| Survival prediction | 45ms | 89ms | 120ms |
| ZK proof generation | 8ms | 15ms | 22ms |
| Counterfactual | 340ms | 610ms | 820ms |
| Full analysis | 480ms | 750ms | 950ms |
