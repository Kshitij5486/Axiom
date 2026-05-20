import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.zk")

app = FastAPI(
    title="Axiom ZK Service",
    description=(
        "Zero-knowledge proof layer for clinical "
        "AI recommendations."
    ),
    version="0.3.0",
)

_start_time = time.time()
_proofs_generated = 0
_proofs_verified = 0
_proofs_failed = 0


class RecommendationProofRequest(BaseModel):
    patient_id: str
    recommendation: str
    causal_effect: float
    graph_id: str
    treatment: str
    outcome: str


class RecommendationVerifyRequest(BaseModel):
    proof_hash: str
    patient_id: str
    recommendation: str
    causal_effect: float
    graph_id: str
    treatment: str
    outcome: str
    timestamp_date: str


class GraphIntegrityRequest(BaseModel):
    graph_id: str
    patient_id: str
    edges: list
    effect_sizes: dict
    built_at: str


class GraphVerifyRequest(BaseModel):
    integrity_proof: str
    graph_id: str
    patient_id: str
    edges: list
    effect_sizes: dict
    built_at: str


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-zk-service",
        "version": "0.3.0",
        "proofs_generated": _proofs_generated,
        "proofs_verified": _proofs_verified,
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.post("/zk/proof/recommendation")
def generate_recommendation_proof(
    request: RecommendationProofRequest,
):
    """
    Generate ZK proof for a clinical recommendation.
    Store proof hash in recommendations table.
    """
    global _proofs_generated
    from zk_proof import ClinicalRecommendationProof

    proof = ClinicalRecommendationProof.generate(
        patient_id=request.patient_id,
        recommendation=request.recommendation,
        causal_effect=request.causal_effect,
        graph_id=request.graph_id,
        treatment=request.treatment,
        outcome=request.outcome,
    )
    _proofs_generated += 1
    return proof


@app.post("/zk/verify/recommendation")
def verify_recommendation_proof(
    request: RecommendationVerifyRequest,
):
    """
    Verify a clinical recommendation proof.
    Doctor can verify without seeing patient data.
    """
    global _proofs_verified, _proofs_failed
    from zk_proof import ClinicalRecommendationProof

    result = ClinicalRecommendationProof.verify(
        proof_hash=request.proof_hash,
        patient_id=request.patient_id,
        recommendation=request.recommendation,
        causal_effect=request.causal_effect,
        graph_id=request.graph_id,
        treatment=request.treatment,
        outcome=request.outcome,
        timestamp_date=request.timestamp_date,
    )

    if result["valid"]:
        _proofs_verified += 1
    else:
        _proofs_failed += 1

    return result


@app.post("/zk/proof/graph")
def generate_graph_proof(
    request: GraphIntegrityRequest,
):
    """
    Generate integrity proof for a causal graph.
    Proves graph was not tampered with.
    """
    global _proofs_generated
    from zk_proof import CausalGraphIntegrityProof

    proof = CausalGraphIntegrityProof.generate(
        graph_id=request.graph_id,
        patient_id=request.patient_id,
        edges=request.edges,
        effect_sizes=request.effect_sizes,
        built_at=request.built_at,
    )
    _proofs_generated += 1
    return proof


@app.post("/zk/verify/graph")
def verify_graph_proof(
    request: GraphVerifyRequest,
):
    """Verify causal graph integrity proof."""
    global _proofs_verified, _proofs_failed
    from zk_proof import CausalGraphIntegrityProof

    result = CausalGraphIntegrityProof.verify(
        integrity_proof=request.integrity_proof,
        graph_id=request.graph_id,
        patient_id=request.patient_id,
        edges=request.edges,
        effect_sizes=request.effect_sizes,
        built_at=request.built_at,
    )

    if result["valid"]:
        _proofs_verified += 1
    else:
        _proofs_failed += 1

    return result


@app.get("/zk/stats")
def stats():
    return {
        "proofs_generated": _proofs_generated,
        "proofs_verified": _proofs_verified,
        "proofs_failed": _proofs_failed,
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
    }



    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)

class RecommendationLogRequest(BaseModel):
    patient_id: str
    doctor_id: str
    treatment: str
    outcome: str
    causal_effect: float
    confidence_low: float = 0.0
    confidence_high: float = 0.0
    zk_proof_hash: str
    evidence: dict = {}
    rec_type: str = "treatment"


class DoctorActionRequest(BaseModel):
    rec_id: str
    doctor_id: str
    action: str
    notes: str = None


@app.post("/audit/recommendation")
def log_recommendation(
    request: RecommendationLogRequest,
):
    """Log a recommendation with ZK proof to audit trail."""
    from audit_trail import AuditTrail
    trail = AuditTrail()
    return trail.log_recommendation(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        treatment=request.treatment,
        outcome=request.outcome,
        causal_effect=request.causal_effect,
        confidence_low=request.confidence_low,
        confidence_high=request.confidence_high,
        zk_proof_hash=request.zk_proof_hash,
        evidence=request.evidence,
        rec_type=request.rec_type,
    )


@app.post("/audit/action")
def log_doctor_action(request: DoctorActionRequest):
    """Log doctor action on a recommendation."""
    from audit_trail import AuditTrail
    trail = AuditTrail()
    return trail.log_doctor_action(
        rec_id=request.rec_id,
        doctor_id=request.doctor_id,
        action=request.action,
        notes=request.notes,
    )


@app.get("/audit/patient/{patient_id}")
def get_patient_audit(patient_id: str):
    """Get full audit trail for a patient."""
    from audit_trail import AuditTrail
    trail = AuditTrail()
    events = trail.get_patient_audit_trail(
        patient_id
    )
    return {"patient_id": patient_id, "events": events}


@app.get("/audit/recent")
def get_recent_audit():
    """Get recent audit events."""
    from audit_trail import AuditTrail
    trail = AuditTrail()
    return {"events": trail.get_recent_audit_events()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)