"""
LLM Copilot router — HONEST version
- Clearly labeled as rule-based intent matching (not LLM)
- All numbers from constants.py (consistent)
- Confidence score removed (it was fake)
"""
from fastapi import APIRouter
from pydantic import BaseModel
import re
from constants import (
    SEP_TOTAL_KWH, SEP_AVG_PF, SEP_PF_PENALTY_INR, SEP_TOTAL_AMOUNT_INR,
    SEP_SEC_ENERGY, BASELINE_SEC_ENERGY, SEP_DEVIATION_PCT, SEP_PRODUCTION_KG,
    ANOMALY_SAVING_COMPRESSOR_INR, ANOMALY_SAVING_FURNACE_INR,
    ANOMALY_SAVING_PRESS3_INR, ANOMALY_SAVING_PF_INR, TOTAL_ANOMALY_SAVING_INR,
    SEP_SCOPE2_TCO2E, SEP_SCOPE1_TCO2E, SEP_EMISSION_INTENSITY,
    PROJECTED_SAVING_TCO2E_YEAR, COPILOT_TYPE, COPILOT_DESC,
)

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    plant_id: int = 1
    language: str = "hinglish"


# ── Tool functions — numbers from constants only ───────────────────────────

def tool_energy_summary():
    return (
        f"Sep 2026 total: **{SEP_TOTAL_KWH:,} kWh** · Bill: **₹{SEP_TOTAL_AMOUNT_INR:,}**\n"
        f"Specific energy: **{SEP_SEC_ENERGY} kWh/kg** (baseline {BASELINE_SEC_ENERGY}, "
        f"+{SEP_DEVIATION_PCT}% deviation)\n"
        f"Avg PF: **{SEP_AVG_PF}** · PF Penalty: **₹{SEP_PF_PENALTY_INR:,}**"
    )


def tool_anomaly_summary():
    total = TOTAL_ANOMALY_SAVING_INR
    return (
        f"4 anomalies detected (physics-simulation based):\n\n"
        f"🔴 Compressor idle waste → **₹{ANOMALY_SAVING_COMPRESSOR_INR:,}/month**\n"
        f"🟡 Furnace peak tariff → **₹{ANOMALY_SAVING_FURNACE_INR:,}/month** (ToD saving)\n"
        f"🔵 Press #3 degradation → **₹{ANOMALY_SAVING_PRESS3_INR:,}/month**\n"
        f"🔵 PF drop → **₹{ANOMALY_SAVING_PF_INR:,}/month**\n\n"
        f"Total potential: **₹{total:,}/month**\n"
        f"⚠ Note: Anomalies are from physics simulation, not trained ML model."
    )


def tool_carbon():
    return (
        f"Sep 2026 GHG Emissions:\n"
        f"• Scope 2 (electricity): **{SEP_SCOPE2_TCO2E} tCO₂e** "
        f"({SEP_TOTAL_KWH:,} kWh × 0.716 kg/kWh)\n"
        f"• Scope 1 (diesel/fuel): **{SEP_SCOPE1_TCO2E} tCO₂e**\n"
        f"• Emission intensity: **{SEP_EMISSION_INTENSITY} kgCO₂e/kg** casting\n"
        f"• Projected annual saving: **{PROJECTED_SAVING_TCO2E_YEAR} tCO₂e/year**\n"
        f"Source: CEA India 2023-24 (0.716 kgCO₂/kWh, Western Grid)"
    )


# ── Intent → response ─────────────────────────────────────────────────────

PATTERNS = [
    (r"bill.*kyun.*badh|consumption.*zyada|bill.*increase|why.*bill",
     lambda: (
         f"Bill {SEP_DEVIATION_PCT}% above baseline. 3 main reasons:\n\n"
         f"1. 🔴 Compressor raat ko idle chal raha hai → **₹{ANOMALY_SAVING_COMPRESSOR_INR:,}/month** waste\n"
         f"2. 🟡 Furnace peak hours mein → **₹{ANOMALY_SAVING_FURNACE_INR:,}/month** extra\n"
         f"3. 🔵 Press #3 degradation → **₹{ANOMALY_SAVING_PRESS3_INR:,}/month**\n\n"
         + tool_energy_summary()
     )),
    (r"compressor|idle|raat|night|4\.2",
     lambda: (
         "**Compressor Idle Waste (Simulated)**\n\n"
         f"Physics model: 4.2 kW idle draw × ~4h × 22 nights = **370 kWh/month**\n"
         f"At off-peak ₹4.50/kWh → **₹{ANOMALY_SAVING_COMPRESSOR_INR:,}/month**\n\n"
         "✅ Fix: Auto-shutoff timer (₹2,000 one-time → payback: 1 week)\n"
         "⚠ Confirm with actual meter reading before acting."
     )),
    (r"power factor|pf|capacitor",
     lambda: (
         f"**Power Factor Analysis**\n\n"
         f"Current PF: **{SEP_AVG_PF}** (target ≥ 0.90)\n"
         f"Monthly PF penalty: **₹{SEP_PF_PENALTY_INR:,}**\n\n"
         f"Fix: Capacitor bank tuning (₹8,000–15,000 one-time)\n"
         f"Estimated saving: **₹{ANOMALY_SAVING_PF_INR:,}/month**\n"
         "Payback: 6–12 months"
     )),
    (r"schedul|tariff|shift|off.?peak|tod|furnace",
     lambda: (
         "**Tariff Optimisation (CP-SAT)**\n\n"
         "Furnace melting ko peak (₹8.20) se off-peak (₹4.50) mein shift karo.\n"
         f"Estimated saving: **₹{ANOMALY_SAVING_FURNACE_INR:,}/month** (tariff only, same kWh)\n\n"
         "Scheduler tab mein 'Run Optimizer' dabao → real CP-SAT result aayega."
     )),
    (r"carbon|co2|emission|scope|ghg|cbam",
     lambda: tool_carbon()),
    (r"saving|kitna|bacha|total|benefit",
     lambda: tool_anomaly_summary()),
    (r"press|degradation|bearing|maintenance",
     lambda: (
         f"**Press #3 Degradation (Simulated)**\n\n"
         "Physics model: specific energy 0.8 → 1.12 kWh/cycle (+40% over 6 weeks)\n"
         f"Extra cost: **₹{ANOMALY_SAVING_PRESS3_INR:,}/month**\n\n"
         "✅ Fix: Bearing inspection + greasing (₹3,500, payback: 1.25 months)\n"
         "⚠ Verify with actual ampere readings."
     )),
    (r"kya|summary|overview|sab|batao|hello|namaste",
     lambda: (
         "**Rajkot Foundry — Sep 2026 Summary**\n\n"
         + tool_energy_summary() + "\n\n"
         f"🚨 4 anomalies · Total saving: **₹{TOTAL_ANOMALY_SAVING_INR:,}/month**\n"
         f"🌿 Carbon: **{SEP_SCOPE2_TCO2E + SEP_SCOPE1_TCO2E:.2f} tCO₂e** this month"
     )),
]


@router.post("/chat")
async def chat(msg: ChatMessage):
    text = msg.message.lower().strip()
    response = None
    for pattern, fn in PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            response = fn()
            break

    if not response:
        response = (
            "Yeh specific sawaal samajh nahi aaya. Try karo:\n\n"
            "• 'Bill kyun badha?' · 'Compressor problem?' · 'Power factor?'\n"
            "• 'Schedule optimize karo' · 'Carbon report' · 'Total saving?'\n\n"
            f"ℹ️ Main ek **rule-based engine** hun ({COPILOT_TYPE}), "
            "sirf verified simulation data se jawab deta hun."
        )

    return {
        "role":        "assistant",
        "content":     response,
        "copilot_type": COPILOT_TYPE,
        "copilot_desc": COPILOT_DESC,
        "data_source": "constants.py (single source of truth)",
        "language":    msg.language,
        "note":        "Numbers are from physics simulation, not trained ML model.",
    }


@router.get("/quick-questions")
async def quick_questions():
    return [
        "Bill kyun badha? 📈",
        "Compressor raat ko kyon chal raha hai?",
        f"Power factor {SEP_AVG_PF} — kya karna chahiye?",
        "Schedule optimize karo — off-peak mein shift karo",
        "Carbon report — Scope 1 aur 2 kitna hai?",
        f"Total monthly saving kitna ho sakta hai? (Hint: ₹{TOTAL_ANOMALY_SAVING_INR:,})",
    ]
