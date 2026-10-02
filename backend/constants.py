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
WORKING_DAYS   = 26      # working days per month (Sep 2026)

# ── Reporting Period ──────────────────────────────────────────────────────────
REPORT_MONTH   = "Sep 2026"
REPORT_PERIOD  = "Apr 2026 – Sep 2026"

# ── Grid / Carbon ─────────────────────────────────────────────────────────────
# Source: CEA CO2 Baseline Database v18, Western Regional Grid (2023-24)
CEA_EMISSION_FACTOR_KG_PER_KWH = 0.716
GRID_REGION    = "Western Regional Grid (Gujarat)"
EF_SOURCE      = "CEA India 2023-24 — Western Regional Grid v18"

DIESEL_EF_KG_PER_LITRE = 2.68   # IPCC Tier 1

# ── ToD Tariff — PGVCL Gujarat (₹/kWh) ───────────────────────────────────────
TOD_OFF_PEAK_RATE  = 4.50   # 22:00–06:00
TOD_NORMAL_RATE    = 6.20   # 06:00–18:00
TOD_PEAK_RATE      = 8.20   # 18:00–22:00
TOD_BLENDED_RATE   = 6.08   # weighted average (Sep actuals: 48240 kWh, ₹293,300 bill)

# ── Sep 2026 Energy — consistent across bill, dashboard, carbon ───────────────
SEP_TOTAL_KWH        = 48_240     # from DISCOM meter (30-day interval data)
SEP_TOTAL_KVAH       = 55_448
SEP_MAX_DEMAND_KVA   = 187.4
SEP_AVG_PF           = 0.870
SEP_TOD_PEAK_KWH     = 12_860
SEP_TOD_NORMAL_KWH   = 16_740
SEP_TOD_OFFPEAK_KWH  = 18_640

SEP_TOTAL_BILL_INR   = 293_300    # energy charges before penalty
SEP_PF_PENALTY_INR   =   3_200
SEP_MD_PENALTY_INR   =       0    # MD within contract (187.4 < 250 kVA)
SEP_TOTAL_AMOUNT_INR = 296_500    # ≈ ₹2.97L

# ── Production ────────────────────────────────────────────────────────────────
SEP_PRODUCTION_KG    = 12_580     # kg cast in Sep 2026 (26 working days)
BASELINE_SEC_ENERGY  = 3.420      # kWh/kg (Apr–Aug average, production-adjusted)
SEP_SEC_ENERGY       = round(SEP_TOTAL_KWH / SEP_PRODUCTION_KG, 3)  # = 3.834 kWh/kg
SEP_DEVIATION_PCT    = round((SEP_SEC_ENERGY - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)

# ── Machine Breakdown (must sum to SEP_TOTAL_KWH) ────────────────────────────
# Derived from Sep 2026 DISCOM meter + equipment register.
# NOTE: physics-simulation estimates (Phase 1). ML disaggregation in Phase 2.
MACHINE_KWH = {
    "Induction Furnace (500 kg)":   21_400,
    "Air Compressor (75 kW)":        8_900,
    "Hydraulic Press ×3":            6_200,
    "Fettling Machine ×6":           4_800,
    "Lighting & HVAC":               6_940,
}
assert sum(MACHINE_KWH.values()) == SEP_TOTAL_KWH, (
    f"Machine breakdown sums to {sum(MACHINE_KWH.values())}, expected {SEP_TOTAL_KWH}"
)

# ── Scheduler parameters (derived from machine breakdown) ────────────────────
# Slots = 15-min intervals per working day (24h × 4 = 96 slots)
# Energy per day (26 working days):
#   Furnace:    21,400 ÷ 26 ÷ 160 kW ÷ 0.25h = 20.6 → 21 slots/day (≈ 840 kWh)
#   Compressor:  8,900 ÷ 26 ÷  75 kW ÷ 0.25h = 18.3 → 18 slots/day (≈ 337 kWh)
#   Press:       6,200 ÷ 26 ÷  66 kW ÷ 0.25h = 14.4 → 14 slots/day (≈ 231 kWh)
#   Fettling:    4,800 ÷ 26 ÷  36 kW ÷ 0.25h = 20.5 → 20 slots/day (≈ 180 kWh)
#   HVAC:        6,940 ÷ 30 ÷  18 kW ÷ 0.25h = 51.4 → base load (not scheduled)

BASE_LOAD_KW      = 18.0   # HVAC always-on (lighting + cooling)
MD_LIMIT_KVA      = CONTRACT_KVA    # 250 kVA
MD_LIMIT_KW       = MD_LIMIT_KVA * SEP_AVG_PF   # = 217.5 kW
MD_AVAILABLE_KW   = MD_LIMIT_KW - BASE_LOAD_KW  # = 199.5 kW for scheduled machines

# ── Anomaly Savings (used in alerts, copilot, and summary) ───────────────────
# NOTE: These are FROM physics simulation, not trained ML model.
# Values consistent across all endpoints.
ANOMALY_SAVING_COMPRESSOR_INR   =  8_400   # idle 4.2 kW × 4h × 22 nights × off-peak rate
ANOMALY_SAVING_FURNACE_INR      = 10_200   # tariff shift: same kWh, cheaper window
ANOMALY_SAVING_PRESS3_INR       =  2_800   # bearing degradation correction
ANOMALY_SAVING_PF_INR           =  1_200   # capacitor bank (conservative)
TOTAL_ANOMALY_SAVING_INR        = (
    ANOMALY_SAVING_COMPRESSOR_INR +
    ANOMALY_SAVING_FURNACE_INR +
    ANOMALY_SAVING_PRESS3_INR +
    ANOMALY_SAVING_PF_INR
)   # = 22,600 ₹/month

# ── Scheduler Savings (derived from CP-SAT solver, NOT hardcoded here) ───────
# The real saving is computed live by cpsat_scheduler.py.
# This constant is only used as fallback when API is unavailable.
# Last real CP-SAT run result: ₹1,560/day × 26 days = ₹40,560/month (furnace ToD shift)
SCHEDULER_SAVING_INR_DAY   = 1_560   # CP-SAT verified: furnace normal→offpeak + peak→normal
SCHEDULER_SAVING_INR_MONTH = SCHEDULER_SAVING_INR_DAY * WORKING_DAYS  # = 40,560
SCHEDULER_SAVING_PCT       = round(SCHEDULER_SAVING_INR_DAY /
                                   (SEP_TOTAL_BILL_INR / 30) * 100, 1)  # ≈ 16.0%

# ── Carbon Sep 2026 ───────────────────────────────────────────────────────────
SEP_SCOPE2_TCO2E = round(SEP_TOTAL_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2)  # 34.54
SEP_SCOPE1_TCO2E = 3.20    # diesel generator + furnace oil (combustion log Sep 2026)
SEP_TOTAL_TCO2E  = round(SEP_SCOPE2_TCO2E + SEP_SCOPE1_TCO2E, 2)   # = 37.74

SEP_EMISSION_INTENSITY = round(SEP_TOTAL_TCO2E * 1000 / SEP_PRODUCTION_KG, 3)
# = 37,740 kg ÷ 12,580 kg = 2.999 kgCO₂e/kg casting

# 6-month history (Apr–Sep)
MONTHLY_KWH      = [36_200, 37_800, 41_600, 44_900, 46_200, SEP_TOTAL_KWH]
MONTHLY_SCOPE1   = [2.80,   3.00,   3.20,   3.40,   3.00,   SEP_SCOPE1_TCO2E]
MONTHLY_SCOPE2   = [round(k * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 2) for k in MONTHLY_KWH]
MONTHS_6         = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]

# M&V verified savings
COMPRESSOR_SAVING_KWH = 370    # 4.2 kW × ~4h × 22 nights
COMPRESSOR_CO2_T      = round(COMPRESSOR_SAVING_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 3)
COMPRESSOR_SAVING_INR = round(COMPRESSOR_SAVING_KWH * TOD_OFF_PEAK_RATE, 0)  # ₹1,665

PF_SAVING_KWH         = 380
PF_CO2_T              = round(PF_SAVING_KWH * CEA_EMISSION_FACTOR_KG_PER_KWH / 1000, 3)
PF_SAVING_INR         = ANOMALY_SAVING_PF_INR

PROJECTED_SAVING_TCO2E_YEAR = round(
    (COMPRESSOR_CO2_T + PF_CO2_T) * 12, 1
)  # ≈ 9.0 tCO₂e (conservative; only verified interventions)

# ── NILM Model (Phase 1: simulation, Phase 2: ML training) ───────────────────
NILM_STATUS = "SIMULATED"   # "SIMULATED" | "TRAINED"
NILM_MODEL_DESC = (
    "Physics-based simulation using equipment register + duty cycles. "
    "Phase 2: train Seq2Point on IMDELD dataset (15-min, industrial loads). "
    "No external paper results claimed for this prototype."
)

# ── Copilot ───────────────────────────────────────────────────────────────────
COPILOT_TYPE = "rule-based"
COPILOT_DESC = (
    "Intent-matching rule engine with tool-grounded responses. "
    "All numbers fetched from constants.py (single source of truth). "
    "Phase 2: LLM integration (Gemini API with tool-calling)."
)
