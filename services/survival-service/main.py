"""
Axiom Survival Service
Port 8082

Deep Cox survival prediction +
PPO treatment policy optimisation.
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("axiom.survival")

app = FastAPI(
    title="Axiom Survival Service",
    description=(
        "Deep Cox survival prediction and "
        "PPO treatment policy optimisation."
    ),
    version="0.5.0",
)

_start_time = time.time()
_cox_model = None
_ppo_model = None


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-survival",
        "version": "0.5.0",
        "cox_model_trained": _cox_model is not None,
        "ppo_model_trained": _ppo_model is not None,
        "uptime_seconds": round(
            time.time() - _start_time, 1
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/survival/encode/{patient_id}")
def encode_patient(patient_id: str):
    """
    Encode patient into 11-dimensional state vector.
    Shows raw vitals + causal effects + normalized state.
    """
    from patient_encoder import (
        encode_patient_with_metadata,
    )
    result = encode_patient_with_metadata(patient_id)
    if result.get("error"):
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )
    return result


@app.get("/survival/encode-all")
def encode_all():
    """Encode all patients and return summary."""
    from patient_encoder import encode_all_patients
    encoded = encode_all_patients()
    return {
        "encoded": len(encoded),
        "state_dim": 11,
        "sample_patient": next(
            iter(encoded.keys()), None
        ),
        "sample_state": (
            encoded[next(iter(encoded.keys()))].tolist()
            if encoded else None
        ),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)