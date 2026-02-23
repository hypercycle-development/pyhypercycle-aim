from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from collections import deque
import time
import uuid


APP_VERSION = "0.1.0"
STARTED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

from aims.support_core.support import handle_message
from aims.telemetry.logger import log_event

# --- Telemetry buffer (in-memory, best-effort) ---
TELEMETRY_MAX = 200
telemetry_buffer = deque(maxlen=TELEMETRY_MAX)

app= FastAPI(title="Hypercycle AIM")

@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION, "started_at": STARTED_AT}


from enum import Enum

class Issue(str, Enum):
    login = "login"
    billing = "billing"
    shipping = "shipping"
    refund = "refund"
    other = "other"


class MessageIn(BaseModel):
    message: str


class MetaOut(BaseModel):
    ts: str
    elapsed_ms: float
    request_id: str
    decision_trace: Optional[Dict[str, Any]] = None

# ! PUBLIC API CONTRACT
# Any change to HandleOut (or /handle response shape) MUST update tests/test_handle_contract.py
# Breaking changes require a version bump
class HandleOut(BaseModel):
    route: str
    issue: Issue
    confidence: float
    reply: str
    escalate: bool
    meta: MetaOut
    

@app.post(
    "/v1/handle",
    response_model=HandleOut,
    response_model_exclude_none=True,
)
def handle(msg: MessageIn) -> HandleOut:
    request_id = uuid.uuid4().hex
    t0 = time.perf_counter()
    decision_trace = None
  
    # Run classifier / router
    result = handle_message(msg.message)

    # Normalize missing keys + types
    route = str(result.get("route") or "language_en")
    raw_issue = result.get("issue")
    reply = str(result.get("reply") or "")

    try:
        issue = Issue(str(raw_issue))
    except (ValueError, TypeError):
        log_event({
            "type": "invalid_issue_value",
            "raw_issue": raw_issue,
            "route": result.get("route"),
        }) 
        issue = Issue.other

    # Confidence heuristic (deterministic, explainable)
    if issue == Issue.billing:
        confidence = 0.90
    elif route == "container_startup_errors":
        confidence = 0.75
    elif route.startswith("language_"):
        confidence = 0.80
    else:
        confidence = 0.60


    # Esculation policy (single source of truth)
    escalate = (issue ==Issue.billing)
    if escalate:
        route = "human_billing"

    # Decision trace (explanability, no side effects)
    decision_trace = {
        "router_result": result.get("route"),
        "normalized_route": route,
        "raw_issue": raw_issue,
        "final_issue": issue.value,
        "confidence_rule": (
            "billing"
            if issue == Issue.billing
            else "language"
            if route.startswith("language_")
            else "default"
        )

}
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    log_event({
        "type": "handle_complete",
        "route": route,
        "issue": issue.value,
        "confidence": confidence,
        "escalate": escalate,
        "elapsed_ms": elapsed_ms,
        "request_id": request_id,
    })


    out = HandleOut(
        route=route,
        issue=issue,
        confidence=confidence,
        reply=reply,
        escalate=escalate,
        meta=MetaOut(
            ts=ts,
            elapsed_ms=elapsed_ms,
            request_id=request_id,
            decision_trace=decision_trace,
        ),
)   


    # Telemetry (stable fields too)
    payload = {
        "type": "handle_complete",
        "request_id": request_id,
        "route": out.route,
        "issue": out.issue.value,
        "confidence": out.confidence,
        "escalate": out.escalate,
    }

    log_event(payload)
    telemetry_buffer.append(payload)
       

    return out

# ============================
# v1 API CONTRACT (STABLE)
# Any breaking change requires /v2
# ============================

# Base health (unversioned)
def health_payload():
    return {
        "status": "ok",
        "service": "aims",
        "version": "v1",
        "started_at": STARTED_AT,
    }

@app.get("/health")
def health():
    return health_payload()
 
@app.get("/v1/health")
def health_v1():
    return health_payload()

@app.get("/v1/telemetry")
def telemetry_v1():
    # newest first
    return list(reversed(telemetry_buffer))
 

@app.post("/v1/handle", response_model=HandleOut, response_model_exclude_none=True)
def handle_v1(msg: MessageIn) -> HandleOut:
    return handle(msg)
