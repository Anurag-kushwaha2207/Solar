"""
Copilot Router — Agentic tool-calling architecture over plant analytical endpoints.
Powered by agentic_copilot.py (Claude tool-use or grounded deterministic tool execution).
"""
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from agentic_copilot import ask_agentic_copilot, CLAUDE_TOOLS, TOOL_REGISTRY
from constants import TOTAL_ANOMALY_SAVING_INR, SEP_AVG_PF
from auth_middleware import get_current_user

router = APIRouter()

# Guest rate limiter: IP -> list of query timestamps (max 30/hour)
_guest_rate_limits: Dict[str, List[float]] = {}
GUEST_HOURLY_LIMIT = 30


def check_guest_rate_limit(client_ip: str):
    now = time.time()
    one_hour_ago = now - 3600
    timestamps = [t for t in _guest_rate_limits.get(client_ip, []) if t > one_hour_ago]
    if len(timestamps) >= GUEST_HOURLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Guest evaluation limit reached (30 queries/hour). Please sign in via Firebase for unlimited access.",
        )
    timestamps.append(now)
    _guest_rate_limits[client_ip] = timestamps


class ChatMessage(BaseModel):
    message: str = ""
    question: str = ""
    plant_id: int = 1
    language: str = "hinglish"


@router.post("/chat")
@router.post("/ask")
async def chat(
    msg: ChatMessage,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Agentic copilot endpoint: executes verified tools (get_kpis, get_alerts, run_optimizer, get_carbon)
    and returns a grounded vernacular explanation.
    - Guest users (demo token): Served by deterministic tool-grounded engine at ZERO API cost.
    - Verified users (Firebase login): Served by genuine Claude tool-use when API key is set.
    """
    user_query = msg.message if msg.message else msg.question
    is_guest = current_user.get("is_guest", False) or current_user.get("source") == "demo_token"

    if is_guest:
        client_ip = request.client.host if request.client else "unknown"
        check_guest_rate_limit(client_ip)
        result = ask_agentic_copilot(user_query, allow_llm=False)
    else:
        result = ask_agentic_copilot(user_query, allow_llm=True)

    return {
        "role": "assistant",
        "answer": result["content"],
        "content": result["content"],
        "engine": result.get("engine", "agentic-tool-engine"),
        "tool_called": result.get("tool_called"),
        "tool_used": result.get("tool_called"),
        "tools_available": list(TOOL_REGISTRY.keys()),
        "language": msg.language,
        "is_guest": is_guest,
        "note": "Answers are grounded in tool outputs.",
    }



@router.get("/quick-questions")
async def quick_questions():
    from active_data import active_plant
    if active_plant.source == "demo_baseline":
        return [
            "Why did my bill increase? 📈",
            "Why is the compressor running at night?",
            f"Power factor {SEP_AVG_PF} — is there a penalty?",
            "Optimize schedule — what are the ToD savings?",
            "What operational anomalies were detected?",
            "Carbon report — what are Scope 1 & 2 emissions?",
        ]

    pf_txt = f"What is my power factor? ({active_plant.avg_pf}) 📊"
    return [
        "Why did my bill increase? 📈",
        pf_txt,
        "What is the machine load breakdown? ⚙️",
        "Optimize schedule — what are the ToD savings? 🚀",
        "What operational anomalies were detected? ⚠️",
        "Carbon report — what are Scope 2 emissions? 🌿",
    ]


@router.get("/tools")
async def list_tools():
    """List tool definitions available to the agentic copilot."""
    return {"tools": CLAUDE_TOOLS}
