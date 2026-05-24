from prometheus_client import Histogram, Counter, Gauge, start_http_server
import time

# Histograms
causal_graph_build_seconds = Histogram(
    "axiom_causal_graph_build_seconds",
    "Time to build causal graph per patient",
    ["patient_id"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

inference_latency_seconds = Histogram(
    "axiom_inference_latency_seconds",
    "Inference latency per endpoint",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

zk_proof_generation_seconds = Histogram(
    "axiom_zk_proof_generation_seconds",
    "Time to generate ZK proof",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

federated_round_duration_seconds = Histogram(
    "axiom_federated_round_duration_seconds",
    "Duration of federated learning round",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# Counters
byzantine_violations_total = Counter(
    "axiom_byzantine_violations_total",
    "Total Byzantine violations detected",
    ["hospital_node"]
)

anomaly_detections_total = Counter(
    "axiom_anomaly_detections_total",
    "Total anomalies detected",
    ["severity"]
)

recommendations_total = Counter(
    "axiom_recommendations_total",
    "Total recommendations generated"
)

zk_proof_verify_total = Counter(
    "axiom_zk_proof_verify_total",
    "Total ZK proofs verified",
    ["status"]
)

# Gauges
websocket_connections_active = Gauge(
    "axiom_websocket_connections_active",
    "Active WebSocket connections"
)

active_patients_total = Gauge(
    "axiom_active_patients_total",
    "Total active patients in system"
)

active_alerts_total = Gauge(
    "axiom_active_alerts_total",
    "Total active clinical alerts"
)

survival_cindex = Gauge(
    "axiom_survival_cindex",
    "Deep Cox survival model concordance index"
)

rl_policy_reward = Gauge(
    "axiom_rl_policy_reward",
    "PPO policy mean reward"
)

# Context manager for timing
class timer:
    def __init__(self, histogram, **labels):
        self.histogram = histogram
        self.labels = labels

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start
        if self.labels:
            self.histogram.labels(**self.labels).observe(elapsed)
        else:
            self.histogram.observe(elapsed)

# Initialize gauges with known values
survival_cindex.set(0.792)
rl_policy_reward.set(3.16)
active_patients_total.set(50)

