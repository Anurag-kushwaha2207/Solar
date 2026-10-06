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
