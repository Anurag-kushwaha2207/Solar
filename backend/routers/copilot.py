"""
Copilot Router — Agentic tool-calling architecture over plant analytical endpoints.
Powered by agentic_copilot.py (Claude tool-use or grounded deterministic tool execution).
"""
from fastapi import APIRouter
from pydantic import BaseModel
from agentic_copilot import ask_agentic_copilot, CLAUDE_TOOLS, TOOL_REGISTRY
from constants import TOTAL_ANOMALY_SAVING_INR, SEP_AVG_PF

router = APIRouter()


class ChatMessage(BaseModel):
    message: str = ""
    question: str = ""
    plant_id: int = 1
    language: str = "hinglish"


@router.post("/chat")
@router.post("/ask")
async def chat(msg: ChatMessage):
    """
    Agentic copilot endpoint: executes verified tools (get_kpis, get_alerts, run_optimizer, get_carbon)
    and returns a grounded vernacular explanation.
    """
    user_query = msg.message if msg.message else msg.question
    result = ask_agentic_copilot(user_query)
    return {
        "role": "assistant",
        "answer": result["content"],
        "content": result["content"],
        "engine": result.get("engine", "agentic-tool-engine"),
        "tool_called": result.get("tool_called"),
        "tool_used": result.get("tool_called"),
        "tools_available": list(TOOL_REGISTRY.keys()),
        "language": msg.language,
        "note": "Answers are grounded in tool outputs.",
    }



@router.get("/quick-questions")
async def quick_questions():
    return [
        "Bill kyun badha? 📈",
        "Compressor raat ko kyon chal raha hai?",
        f"Power factor {SEP_AVG_PF} — kya penalty hai?",
        "Schedule optimize karo — ToD shift saving kitna hai?",
        "What operational anomalies were detected?",
        "Carbon report — Scope 1 aur 2 kitna hai?",
    ]


@router.get("/tools")
async def list_tools():
    """List tool definitions available to the agentic copilot."""
    return {"tools": CLAUDE_TOOLS}
