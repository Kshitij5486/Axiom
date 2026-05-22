"""
Claude Judgment Service
Embedded in the API Gateway layer

n8n calls this endpoint when it encounters
situations requiring clinical reasoning:

  1. Causal drift significance
     "Is this 31% change in effect clinically meaningful?"

  2. Conflicting recommendation resolution
     "PPO says lisinopril, NLP says furosemide risky"

  3. Alert triage priority
     "3 alerts firing — which is most urgent?"

  4. Treatment coherence check
     "Does this treatment sequence make sense?"

Returns structured JSON with:
  decision:   the judgment call
  reasoning:  explanation
  confidence: 0.0-1.0
  action:     what n8n should do next
"""

import json
import logging
import os
from datetime import datetime, timezone

import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("axiom.claude_judgment")

app = FastAPI(
    title="Axiom Claude Judgment Service",
    version="0.7.0",
)

# Anthropic API
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-opus-4-5"


class DriftJudgmentRequest(BaseModel):
    patient_id: str
    edge: str
    old_effect: float
    new_effect: float
    drift_pct: float
    patient_context: Optional[dict] = None


class ConflictJudgmentRequest(BaseModel):
    patient_id: str
    ppo_recommendation: str
    nlp_recommendation: str
    ppo_reward: float
    nlp_confidence: float
    patient_context: Optional[dict] = None


class AlertTriageRequest(BaseModel):
    patient_id: str
    alerts: list
    patient_context: Optional[dict] = None


class CoherenceRequest(BaseModel):
    patient_id: str
    treatment_sequence: list
    causal_graph: Optional[dict] = None


def call_claude(prompt: str, system: str) -> dict:
    """Call Claude API and return structured response."""
    if not ANTHROPIC_KEY:
        # Mock response when no API key
        return {
            "decision": "proceed",
            "reasoning": (
                "Claude API key not configured. "
                "Using default decision."
            ),
            "confidence": 0.5,
            "action": "proceed_with_caution",
        }

    try:
        response = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 500,
                "system": system,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["content"][0]["text"]

        # Parse JSON from Claude response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {
            "decision": "proceed",
            "reasoning": content[:200],
            "confidence": 0.7,
            "action": "proceed",
        }
    except Exception as e:
        logger.error("Claude API error: %s", e)
        return {
            "decision": "proceed",
            "reasoning": f"API error: {str(e)[:100]}",
            "confidence": 0.5,
            "action": "proceed_with_caution",
        }


SYSTEM_CLINICAL = """You are a clinical AI assistant
analyzing causal graph changes and treatment decisions.
Always respond with valid JSON only, no other text.
JSON must have: decision, reasoning, confidence, action.
Be concise. confidence is 0.0-1.0."""


@app.post("/judge/causal-drift")
def judge_causal_drift(req: DriftJudgmentRequest):
    """
    Assess if a causal effect drift is clinically
    significant enough to alert the doctor.
    """
    prompt = f"""
Causal graph drift detected for patient {req.patient_id[:8]}:
  Edge: {req.edge}
  Old effect: {req.old_effect:.4f}
  New effect: {req.new_effect:.4f}
  Drift: {req.drift_pct:.1f}%

Is this drift clinically significant?
Should the doctor be alerted?

Respond with JSON:
{{
  "decision": "alert_doctor" or "monitor" or "ignore",
  "reasoning": "brief clinical reason",
  "confidence": 0.0-1.0,
  "action": "send_alert" or "log_only" or "ignore"
}}"""

    result = call_claude(prompt, SYSTEM_CLINICAL)
    result["patient_id"] = req.patient_id
    result["edge"] = req.edge
    result["drift_pct"] = req.drift_pct
    result["timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()
    return result


@app.post("/judge/conflicting-recommendations")
def judge_conflict(req: ConflictJudgmentRequest):
    """
    Resolve conflict between PPO and NLP recommendations.
    """
    prompt = f"""
Conflicting treatment recommendations for patient {req.patient_id[:8]}:
  PPO recommends: {req.ppo_recommendation} (reward={req.ppo_reward:.3f})
  NLP extracted:  {req.nlp_recommendation} (confidence={req.nlp_confidence:.2f})

Which should take priority for this patient?

Respond with JSON:
{{
  "decision": "{req.ppo_recommendation}" or "{req.nlp_recommendation}" or "escalate",
  "reasoning": "brief clinical reason",
  "confidence": 0.0-1.0,
  "action": "use_ppo" or "use_nlp" or "escalate_to_doctor"
}}"""

    result = call_claude(prompt, SYSTEM_CLINICAL)
    result["patient_id"] = req.patient_id
    result["timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()
    return result


@app.post("/judge/alert-triage")
def judge_alert_triage(req: AlertTriageRequest):
    """
    Triage multiple simultaneous alerts by priority.
    """
    alert_summary = "\n".join([
        f"  - {a.get('feature','?')}: "
        f"{a.get('alert_type','?')} "
        f"severity={a.get('severity','?')}"
        for a in req.alerts[:5]
    ])

    prompt = f"""
Multiple alerts for patient {req.patient_id[:8]}:
{alert_summary}

Which alert is most urgent? What order to address them?

Respond with JSON:
{{
  "decision": "most urgent alert feature name",
  "reasoning": "brief triage rationale",
  "confidence": 0.0-1.0,
  "action": "immediate_escalation" or "urgent_review" or "routine_review",
  "priority_order": ["feature1", "feature2", ...]
}}"""

    result = call_claude(prompt, SYSTEM_CLINICAL)
    result["patient_id"] = req.patient_id
    result["n_alerts"] = len(req.alerts)
    result["timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()
    return result


@app.post("/judge/treatment-coherence")
def judge_coherence(req: CoherenceRequest):
    """
    Check if a treatment sequence is clinically coherent.
    """
    seq_str = " → ".join(req.treatment_sequence)
    prompt = f"""
Treatment sequence for patient {req.patient_id[:8]}:
  {seq_str}

Is this sequence clinically coherent?
Any dangerous interactions or contraindications?

Respond with JSON:
{{
  "decision": "coherent" or "review_needed" or "contraindicated",
  "reasoning": "brief clinical assessment",
  "confidence": 0.0-1.0,
  "action": "approve" or "flag_for_review" or "block"
}}"""

    result = call_claude(prompt, SYSTEM_CLINICAL)
    result["patient_id"] = req.patient_id
    result["sequence"] = req.treatment_sequence
    result["timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()
    return result


@app.get("/judge/health")
def health():
    return {
        "status": "healthy",
        "service": "axiom-claude-judgment",
        "version": "0.7.0",
        "claude_configured": bool(ANTHROPIC_KEY),
        "model": MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)