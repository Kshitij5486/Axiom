# Axiom Architecture

## System Overview

    EHR --> FHIR Adapter (8080) --> Kafka --> Data Normaliser
                                                   |
                              +--------------------+--------------------+
                              |                                         |
                        Causal Engine (8081)               Survival + RL (8082)
                        DoWhy + DoCalc                     Deep Cox + PPO
                        212ms per graph                    C-index 0.792
                              |                                         |
                        ZK Service (8084)                  NLP + Anomaly (8083)
                        Integrity proofs                   BioBERT + IsoForest
                              |                                         |
                              +--------------------+--------------------+
                                                   |
                                        GraphQL Gateway (4000)
                                        WebSocket      (4001)
                                        gRPC           (50051)
                                                   |
                                        Dashboard (3000)
                                        Screen 1: Command Centre
                                        Screen 2: 3D Causal Graph
                                        Screen 3: Counterfactual
                                        Screen 4: Population Atlas

## Service Map

| Service | Port | Technology | Sprint |
|---------|------|-----------|--------|
| FHIR Adapter | 8080 | Java Spring Boot | 1 |
| Causal Engine | 8081 | Python FastAPI + DoWhy | 2 |
| Survival + RL | 8082 | Python FastAPI + PyTorch | 5 |
| NLP + Anomaly | 8083 | Python FastAPI + BioBERT | 6 |
| ZK Service | 8084 | Python FastAPI | 3 |
| Federated | 8085 | Python FastAPI | 4 |
| GraphQL Gateway | 4000 | Node.js Apollo | 7 |
| WebSocket | 4001 | Node.js graphql-ws | 7 |
| gRPC | 50051 | Python grpcio | 7 |
| Dashboard | 3000 | HTML + D3 + Three.js | 8-10 |
| PostgreSQL | 5439 | postgres:15 | 1 |
| MongoDB | 27018 | mongo:7 | 1 |
| Kafka | 9094 | Confluent 7.4 | 1 |

## Data Flow

1. Patient vitals arrive via FHIR R4 to Kafka topic vitals.raw
2. Normaliser consumes and stores in PostgreSQL + MongoDB
3. Causal Engine builds per-patient DAG using DoWhy in 212ms avg
4. ZK Service generates SHA-256 integrity proof
5. Survival model scores 30-day survival probability
6. PPO policy selects optimal treatment recommendation
7. NLP pipeline enriches DAG with clinical note edges
8. Anomaly detector flags vital breaches via WebSocket alert
9. GraphQL gateway exposes unified API to dashboard
10. Doctor views 3D graph, runs counterfactual, reviews population atlas
