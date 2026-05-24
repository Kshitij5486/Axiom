# Axiom Deployment Guide

## Local Development

Prerequisites: Docker Desktop, Python 3.11+, Node.js 20+, Java 21

    git clone https://github.com/Kshitij5486/Axiom.git
    cd Axiom/infrastructure
    docker compose up -d
    cd ..
    python -m pytest tests/unit/ -v --tb=short
    python -m http.server 3000 --directory services/dashboard

## Production

### Kubernetes

    kubectl apply -f infrastructure/kubernetes/manifests/namespace.yaml
    kubectl apply -f infrastructure/kubernetes/manifests/secrets.yaml
    kubectl apply -f infrastructure/kubernetes/manifests/
    kubectl get pods -n axiom-clinical

### Helm

    helm install axiom ./infrastructure/kubernetes/helm/axiom --namespace axiom-clinical

### Monitoring

    Prometheus: http://localhost:9090
    Grafana:    http://localhost:3001 (import dashboards from infrastructure/monitoring/grafana/dashboards/)

## Environment Variables

| Variable | Description |
|----------|-------------|
| POSTGRES_USER | PostgreSQL username |
| POSTGRES_PASSWORD | PostgreSQL password |
| MONGO_USER | MongoDB username |
| MONGO_PASSWORD | MongoDB password |
| JWT_SECRET | 256-bit JWT secret |
| JAVA_HOME | JDK 21 path |

## Encryption at Rest

PostgreSQL: pgcrypto extension, AES-256 column-level encryption
MongoDB: enableEncryption: true in mongod.conf with keyfile
Key rotation: openssl rand -base64 32 > new_keyfile, update k8s secret, rollout restart
