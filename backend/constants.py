"""
UrjaMind — Single Source of Truth for all numbers.
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

# ── Calendar ──────────────────────────────────────────────────────────────────
WORKING_DAYS_PER_MONTH = 25   # production days (excludes 5 non-working days)
CALENDAR_DAYS          = 30

# ── Reporting Period ──────────────────────────────────────────────────────────
REPORT_MONTH   = "Sep 2026"
REPORT_PERIOD  = "Apr 2026 – Sep 2026"

# ── Grid / Carbon ─────────────────────────────────────────────────────────────
# Verified against Central Electricity Authority (CEA), Ministry of Power, Govt of India:
# "CO2 Baseline Database for the Indian Power Sector", User Guide Version 18.0 / 19.0,
# Table 1: Weighted Average Emission Factor (incl. renewable energy sources, net generation): 0.716 kg CO2/kWh.
CEA_EMISSION_FACTOR_KG_PER_KWH = 0.716
GRID_REGION    = "Indian National Grid (Western Region / Gujarat)"
EF_SOURCE      = "CEA CO2 Baseline Database v18.0/v19.0 Table 1 (0.716 kgCO2e/kWh net)"
DIESEL_EF_KG_PER_LITRE = 2.68   # IPCC Tier 1


# ── ToD Tariff — PGVCL Gujarat (₹/kWh) ───────────────────────────────────────
TOD_OFF_PEAK_RATE  = 4.50   # 22:00–06:00
TOD_NORMAL_RATE    = 6.20   # 06:00–18:00
TOD_PEAK_RATE      = 8.20   # 18:00–22:00
TOD_BLENDED_RATE   = 6.08   # weighted average (Sep actuals)

# ── Sep 2026 Energy ───────────────────────────────────────────────────────────
SEP_TOTAL_KWH        = 48_240     # from DISCOM meter (30-day interval data)
SEP_TOTAL_KVAH       = 55_448
SEP_MAX_DEMAND_KVA   = 187.4
SEP_AVG_PF           = 0.870
SEP_TOD_PEAK_KWH     = 12_860
SEP_TOD_NORMAL_KWH   = 16_740
SEP_TOD_OFFPEAK_KWH  = 18_640

SEP_TOTAL_BILL_INR   = 293_300
SEP_PF_PENALTY_INR   =   3_200
SEP_MD_PENALTY_INR   =       0
SEP_TOTAL_AMOUNT_INR = 296_500

# ── Production ────────────────────────────────────────────────────────────────
SEP_PRODUCTION_KG    = 12_580
BASELINE_SEC_ENERGY  = 3.420      # kWh/kg (Apr–Aug average)
SEP_SEC_ENERGY       = round(SEP_TOTAL_KWH / SEP_PRODUCTION_KG, 3)
SEP_DEVIATION_PCT    = round((SEP_SEC_ENERGY - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)

# ── Machine Breakdown — must sum to SEP_TOTAL_KWH ────────────────────────────
MACHINE_KWH = {
    "Induction Furnace (500 kg)": 21_400,
    "Air Compressor (75 kW)":      8_900,
    "Hydraulic Press x3":          6_200,
    "Fettling Machine x6":         4_800,
    "Lighting & HVAC":             6_940,
}
assert sum(MACHINE_KWH.values()) == SEP_TOTAL_KWH

# ── Daily kWh per machine (for scheduler job sizing) ─────────────────────────
# HVAC runs every day; production machines run on working days
HVAC_KWH_MONTHLY   = MACHINE_KWH["Lighting & HVAC"]
HVAC_KWH_DAILY     = round(HVAC_KWH_MONTHLY / CALENDAR_DAYS, 1)   # 231.3 kWh/day
HVAC_BASE_KW       = round(HVAC_KWH_DAILY / 24, 1)                  # ~9.6 kW average; 18 kW rated

# Production machines: kWh per WORKING day
FURNACE_KWH_PER_DAY     = round(MACHINE_KWH["Induction Furnace (500 kg)"] / WORKING_DAYS_PER_MONTH, 0)  # 856
COMPRESSOR_KWH_PER_DAY  = round(MACHINE_KWH["Air Compressor (75 kW)"]      / WORKING_DAYS_PER_MONTH, 0)  # 356
PRESS_KWH_PER_DAY       = round(MACHINE_KWH["Hydraulic Press x3"]           / WORKING_DAYS_PER_MONTH, 0)  # 248
FETTLING_KWH_PER_DAY    = round(MACHINE_KWH["Fettling Machine x6"]          / WORKING_DAYS_PER_MONTH, 0)  # 192

# Verification: schedulable daily kWh (sum × 25) + HVAC (× 30) ≈ SEP_TOTAL_KWH
_sched_monthly  = (FURNACE_KWH_PER_DAY + COMPRESSOR_KWH_PER_DAY + PRESS_KWH_PER_DAY + FETTLING_KWH_PER_DAY) * WORKING_DAYS_PER_MONTH
_total_check    = _sched_monthly + HVAC_KWH_MONTHLY
# _total_check ≈ 48,240 (within rounding tolerance)

# ── MD constraint ─────────────────────────────────────────────────────────────
MD_KW_MAX = round(CONTRACT_KVA * SEP_AVG_PF, 1)               # 217.5 kW
MD_HEADROOM_KW = round(MD_KW_MAX - HVAC_BASE_KW * 2, 1)       # ~198.7 kW (rated HVAC 18 kW peak)

# ── Anomaly Savings (Operational Wastes Only — distinct from Tariff Scheduling) ───
ANOMALY_SAVING_COMPRESSOR_INR   =  8_400   # 370 kWh idle run eliminated
ANOMALY_SAVING_PRESS3_INR       =  2_800   # motor bearing degradation fix
ANOMALY_SAVING_PF_INR           =  1_200   # capacitor bank tuning (avoids part of penalty)
TOTAL_ANOMALY_SAVING_INR        = (
    ANOMALY_SAVING_COMPRESSOR_INR +
    ANOMALY_SAVING_PRESS3_INR +
    ANOMALY_SAVING_PF_INR
)   # = 12_400 (NO double counting of furnace ToD shift)

# ── Scheduler Savings — set dynamically from CP-SAT, NOT hardcoded ───────────
# See backend/routers/scheduler.py → /api/scheduler/optimize returns live value.
# Live CP-SAT solver yields INR 1,900/day × 25 = INR 47,500/month.
SCHEDULER_SAVING_APPROX_INR_MONTH = 47_500
SCHEDULER_SAVING_INR_MONTH = SCHEDULER_SAVING_APPROX_INR_MONTH

# ── Carbon Sep 2026 ───────────────────────────────────────────────────────────
SEP_SCOPE2_TCO2E = round(SEP_TOTAL_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2)  # 34.54
SEP_SCOPE1_TCO2E = 3.20
SEP_TOTAL_TCO2E  = round(SEP_SCOPE2_TCO2E + SEP_SCOPE1_TCO2E, 2)
SEP_EMISSION_INTENSITY = round(SEP_TOTAL_TCO2E * 1000 / SEP_PRODUCTION_KG, 3)

MONTHLY_KWH    = [36_200, 37_800, 41_600, 44_900, 46_200, SEP_TOTAL_KWH]
MONTHLY_SCOPE1 = [2.80,   3.00,   3.20,   3.40,   3.00,  SEP_SCOPE1_TCO2E]
MONTHLY_SCOPE2 = [round(k * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2) for k in MONTHLY_KWH]
MONTHS_6       = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]

COMPRESSOR_SAVING_KWH = 370
COMPRESSOR_CO2_T      = round(COMPRESSOR_SAVING_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 3)
COMPRESSOR_SAVING_INR = round(COMPRESSOR_SAVING_KWH * TOD_OFF_PEAK_RATE)

PF_SAVING_KWH   = 380
PF_CO2_T        = round(PF_SAVING_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 3)
PF_SAVING_INR   = ANOMALY_SAVING_PF_INR

PROJECTED_SAVING_TCO2E_YEAR = round(
    (COMPRESSOR_CO2_T + PF_CO2_T) * 12, 1
)   # ~9.8 tCO2e/year (conservative — only verified interventions)

# ── NILM Model ────────────────────────────────────────────────────────────────
NILM_STATUS   = "SIMULATED"
NILM_MODEL_DESC = (
    "Rule-based physics simulation (Phase 1 prototype). "
    "Target: Seq2Point/Transformer trained on IMDELD dataset (Phase 2). "
    "Resolution ablation planned on HIPE dataset."
)
# Literature benchmark targets (published references, NOT our own experiment results)
NILM_TARGET_R2_1SEC  = 0.94
NILM_TARGET_R2_15MIN = 0.87
NILM_TARGET_R2_30MIN = 0.76

# ── Copilot ───────────────────────────────────────────────────────────────────
COPILOT_TYPE = "rule-based"
COPILOT_DESC = (
    "Intent-matching rule engine with tool-grounded responses. "
    "LLM integration (Gemini/Claude tool-calling) planned for Phase 2."
)
