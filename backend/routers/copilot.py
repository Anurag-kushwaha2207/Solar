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

# ── 1. IP Extraction (Render Proxy & Cloudflare Aware) ──────────────────────────
def get_client_ip(request: Request) -> str:
    """Extract real client IP behind reverse proxies (Render, Cloudflare, Nginx)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


# ── 2. Guest Rate Limiter (Per IP, Max 60 queries/hour) ────────────────────────
_guest_rate_limits: Dict[str, List[float]] = {}
GUEST_HOURLY_LIMIT = 60


def check_guest_rate_limit(client_ip: str):
    if client_ip in ("unknown", "127.0.0.1", "localhost", "testclient"):
        return  # Do not block local tests or indeterminate addresses
    now = time.time()
    one_hour_ago = now - 3600
    timestamps = [t for t in _guest_rate_limits.get(client_ip, []) if t > one_hour_ago]
    if len(timestamps) >= GUEST_HOURLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Guest evaluation limit reached (60 queries/hour). Please sign in via Google/Firebase for full access.",
        )
    timestamps.append(now)
    _guest_rate_limits[client_ip] = timestamps


# ── 3. Authenticated User Spend Limiter (Max 20 Claude calls/hour per user) ──
_user_query_limits: Dict[str, List[float]] = {}
USER_HOURLY_LLM_LIMIT = 20


def can_user_use_llm(uid: str) -> bool:
    """Ensure no individual logged-in user can drain the Anthropic monthly spend."""
    now = time.time()
    one_hour_ago = now - 3600
    timestamps = [t for t in _user_query_limits.get(uid, []) if t > one_hour_ago]
    if len(timestamps) >= USER_HOURLY_LLM_LIMIT:
        return False
    timestamps.append(now)
    _user_query_limits[uid] = timestamps
    return True


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
    - Verified users (Firebase login): Served by genuine Claude tool-use up to 20/hr, with graceful tool fallback.
    """
    user_query = msg.message if msg.message else msg.question
    is_guest = current_user.get("is_guest", False) or current_user.get("source") == "demo_token"

    if is_guest:
        client_ip = get_client_ip(request)
        check_guest_rate_limit(client_ip)
        result = ask_agentic_copilot(user_query, allow_llm=False)
    else:
        uid = current_user.get("uid", "authenticated_user")
        if can_user_use_llm(uid):
            result = ask_agentic_copilot(user_query, allow_llm=True)
        else:
            # Revert smoothly to zero-cost deterministic tool runner without breaking the UI
            result = ask_agentic_copilot(user_query, allow_llm=False)
            result["content"] += "\n\n*(ℹ️ Note: User hourly AI limit reached. Reverted to grounded tool engine to protect API quota.)*"

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
