"""
UrjaMind — Single Source of Truth for all numbers
Sabhi hardcoded values yahan se aate hain.
Ek jagah badlo, poora system consistent ho jaata hai.
"""

# ── Plant Info ────────────────────────────────────────────────────────────────
PLANT_NAME     = "Rajkot Precision Foundry Pvt. Ltd."
PLANT_INDUSTRY = "Foundry"
PLANT_LOCATION = "Rajkot, Gujarat"
PLANT_STATE    = "Gujarat"
PLANT_DISCOM   = "PGVCL"
CONTRACT_KVA   = 250.0

# ── Reporting Period ──────────────────────────────────────────────────────────
REPORT_MONTH   = "Sep 2026"
REPORT_PERIOD  = "Apr 2026 – Sep 2026"

# ── Grid / Carbon ─────────────────────────────────────────────────────────────
# Source: CEA CO2 Baseline Database v18, Western Regional Grid (2023-24)
CEA_EMISSION_FACTOR_KG_PER_KWH = 0.716
GRID_REGION    = "Western Regional Grid (Gujarat)"
EF_SOURCE      = "CEA India 2023-24 — Western Regional Grid"

DIESEL_EF_KG_PER_LITRE = 2.68   # IPCC Tier 1

# ── ToD Tariff — PGVCL Gujarat (₹/kWh) ───────────────────────────────────────
TOD_OFF_PEAK_RATE  = 4.50   # 22:00–06:00
TOD_NORMAL_RATE    = 6.20   # 06:00–18:00
TOD_PEAK_RATE      = 8.20   # 18:00–22:00
TOD_BLENDED_RATE   = 6.08   # weighted average (Sep actuals)

# ── Sep 2026 Energy — consistent across bill, dashboard, carbon ───────────────
SEP_TOTAL_KWH        = 48_240     # from DISCOM meter (30-day interval data)
SEP_TOTAL_KVAH       = 55_448
SEP_MAX_DEMAND_KVA   = 187.4
SEP_AVG_PF           = 0.870
SEP_TOD_PEAK_KWH     = 12_860
SEP_TOD_NORMAL_KWH   = 16_740
SEP_TOD_OFFPEAK_KWH  = 18_640

SEP_TOTAL_BILL_INR   = 293_300    # before penalty
SEP_PF_PENALTY_INR   =   3_200
SEP_MD_PENALTY_INR   =       0    # MD within contract
SEP_TOTAL_AMOUNT_INR = 296_500    # ≈ ₹2.97L

# ── Production ────────────────────────────────────────────────────────────────
SEP_PRODUCTION_KG    = 12_580     # tonnes cast Sep 2026
BASELINE_SEC_ENERGY  = 3.420      # kWh/kg (Apr–Aug average)
SEP_SEC_ENERGY       = round(SEP_TOTAL_KWH / SEP_PRODUCTION_KG, 3)  # 3.834
SEP_DEVIATION_PCT    = round((SEP_SEC_ENERGY - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)

# ── Machine Breakdown (must sum to SEP_TOTAL_KWH) ────────────────────────────
MACHINE_KWH = {
    "Induction Furnace (500 kg)":   21_400,
    "Air Compressor (75 kW)":        8_900,
    "Hydraulic Press ×3":            6_200,
    "Fettling Machine ×6":           4_800,
    "Lighting & HVAC":               6_940,
}
assert sum(MACHINE_KWH.values()) == SEP_TOTAL_KWH, "Machine breakdown must sum to SEP_TOTAL_KWH"

# ── Anomaly Savings (used in alerts, copilot, and summary) ───────────────────
ANOMALY_SAVING_COMPRESSOR_INR   =  8_400
ANOMALY_SAVING_FURNACE_INR      = 10_200
ANOMALY_SAVING_PRESS3_INR       =  2_800
ANOMALY_SAVING_PF_INR           =  1_200   # conservative
TOTAL_ANOMALY_SAVING_INR        = (
    ANOMALY_SAVING_COMPRESSOR_INR +
    ANOMALY_SAVING_FURNACE_INR +
    ANOMALY_SAVING_PRESS3_INR +
    ANOMALY_SAVING_PF_INR
)   # = 22_600

# ── Scheduler Savings ─────────────────────────────────────────────────────────
SCHEDULER_SAVING_INR_MONTH = 18_400  # CP-SAT result (ToD shift)

# ── Carbon Sep 2026 ───────────────────────────────────────────────────────────
SEP_SCOPE2_TCO2E = round(SEP_TOTAL_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2)  # 34.54
SEP_SCOPE1_TCO2E = 3.20    # diesel + furnace oil
SEP_TOTAL_TCO2E  = round(SEP_SCOPE2_TCO2E + SEP_SCOPE1_TCO2E, 2)

SEP_EMISSION_INTENSITY = round((SEP_SCOPE2_TCO2E + SEP_SCOPE1_TCO2E) * 1000 / SEP_PRODUCTION_KG, 3)
# = (34.54 + 3.20) * 1000 / 12580 = 2.999 kgCO2e/kg

# 6-month history (Apr–Sep)
MONTHLY_KWH      = [36_200, 37_800, 41_600, 44_900, 46_200, SEP_TOTAL_KWH]
MONTHLY_SCOPE1   = [2.80,   3.00,   3.20,   3.40,   3.00,   SEP_SCOPE1_TCO2E]
MONTHLY_SCOPE2   = [round(k * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2) for k in MONTHLY_KWH]
MONTHS_6         = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]

# Verified M&V savings
COMPRESSOR_SAVING_KWH = 370    # 4.2 kW × ~4h × 22 nights
COMPRESSOR_CO2_T      = round(COMPRESSOR_SAVING_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 3)
COMPRESSOR_SAVING_INR = round(COMPRESSOR_SAVING_KWH * TOD_OFF_PEAK_RATE, 0)   # off-peak rate

PF_SAVING_KWH         = 380
PF_CO2_T              = round(PF_SAVING_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 3)
PF_SAVING_INR         = ANOMALY_SAVING_PF_INR

PROJECTED_SAVING_TCO2E_YEAR = round(
    (COMPRESSOR_CO2_T + PF_CO2_T) * 12 +
    (ANOMALY_SAVING_FURNACE_INR / (TOD_PEAK_RATE - TOD_OFF_PEAK_RATE) * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000),
    1
)  # ≈ 13.4 tCO2e

# ── NILM Model (HONEST: simulation-based, not trained on IMDELD) ─────────────
# These are TARGET metrics from literature; actual model results TBD in Phase 2
NILM_STATUS = "SIMULATED"   # "SIMULATED" | "TRAINED"
NILM_MODEL_DESC = (
    "Rule-based physics simulation (Phase 1 prototype). "
    "Target: Transformer/Seq2Point trained on IMDELD (Phase 2). "
    "Resolution ablation planned on HIPE dataset."
)
# Ablation numbers are TARGETS from literature, not our own experiment
NILM_TARGET_R2_1SEC   = 0.94
NILM_TARGET_R2_15MIN  = 0.87
NILM_TARGET_R2_30MIN  = 0.79

# ── Copilot ───────────────────────────────────────────────────────────────────
COPILOT_TYPE = "rule-based"   # "rule-based" | "llm"
COPILOT_DESC = (
    "Intent-matching rule engine with tool-grounded responses. "
    "LLM integration (Gemini/Claude) planned for Phase 2."
)
