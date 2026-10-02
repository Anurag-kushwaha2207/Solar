"""
UrjaMind Active Data State Manager
==================================
Allows uploaded interval CSV data to dynamically update the live dashboard,
KPIs, and machine breakdown, with clean fallback to the Rajkot Foundry baseline.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from constants import (
    PLANT_NAME, REPORT_PERIOD,
    SEP_TOTAL_KWH, SEP_TOTAL_AMOUNT_INR, SEP_SEC_ENERGY, BASELINE_SEC_ENERGY,
    SEP_DEVIATION_PCT, SEP_AVG_PF, SEP_PF_PENALTY_INR, CONTRACT_KVA,
    MACHINE_KWH, CEA_EMISSION_FACTOR_KG_PER_KWH,
)


class ActivePlantData:
    def __init__(self):
        self.reset_to_demo()

    def reset_to_demo(self):
        self.source = "demo_baseline"
        self.filename = "demo_rajkot_sep2026.csv"
        self.total_kwh = float(SEP_TOTAL_KWH)
        self.total_bill_inr = float(SEP_TOTAL_AMOUNT_INR)
        self.avg_pf = float(SEP_AVG_PF)
        self.specific_energy = float(SEP_SEC_ENERGY)
        self.deviation_pct = float(SEP_DEVIATION_PCT)
        self.peak_kw = float(round(187.4 * SEP_AVG_PF, 1))
        self.machines = dict(MACHINE_KWH)
        self.raw_df: Optional[pd.DataFrame] = None
        self.rows_count = 2880  # 30 days * 96 slots

    def ingest_csv(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse uploaded interval CSV and compute real analytical metrics."""
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception as e:
            return {
                "success": False,
                "mode": "demo_values_used",
                "reason": f"CSV parse error: {str(e)}",
            }

        # Normalize column names
        cols_lower = {c: str(c).strip().lower().replace(" ", "_") for c in df.columns}
        df = df.rename(columns=cols_lower)

        # Check for numeric energy / power columns
        kwh_col = next((c for c in ["total_kwh", "kwh", "energy_kwh", "consumption_kwh"] if c in df.columns), None)
        kw_col = next((c for c in ["total_kw", "kw", "load_kw", "power_kw"] if c in df.columns), None)
        pf_col = next((c for c in ["power_factor", "pf", "avg_pf"] if c in df.columns), None)

        if not kwh_col and not kw_col:
            return {
                "success": False,
                "mode": "demo_values_used",
                "reason": "No recognizable 'total_kwh' or 'total_kw' column found in file. Demo baseline retained.",
            }

        # Extract values
        if kwh_col:
            df[kwh_col] = pd.to_numeric(df[kwh_col], errors="coerce").fillna(0)
            total_kwh = float(df[kwh_col].sum())
        else:
            df[kw_col] = pd.to_numeric(df[kw_col], errors="coerce").fillna(0)
            # Assuming 15-minute intervals if not specified
            total_kwh = float((df[kw_col] * 0.25).sum())

        if kw_col:
            df[kw_col] = pd.to_numeric(df[kw_col], errors="coerce").fillna(0)
            peak_kw = float(df[kw_col].max())
        else:
            peak_kw = float(total_kwh / max(1, len(df)) * 4)

        if pf_col:
            df[pf_col] = pd.to_numeric(df[pf_col], errors="coerce").fillna(0.90)
            avg_pf = float(df[pf_col].mean())
        else:
            avg_pf = 0.88

        # Production column if present
        prod_col = next((c for c in ["production_units", "production_kg", "production", "units"] if c in df.columns), None)
        if prod_col:
            df[prod_col] = pd.to_numeric(df[prod_col], errors="coerce").fillna(1)
            prod_total = float(df[prod_col].sum())
            sec_energy = round(total_kwh / max(1.0, prod_total), 3)
        else:
            sec_energy = round(total_kwh / 12_580, 3)

        # Update active state
        self.source = "user_uploaded_csv"
        self.filename = filename
        self.total_kwh = round(total_kwh, 1)
        self.total_bill_inr = round(total_kwh * 6.08, 0)
        self.avg_pf = round(avg_pf, 3)
        self.peak_kw = round(peak_kw, 1)
        self.specific_energy = sec_energy
        self.deviation_pct = round((sec_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)
        self.rows_count = len(df)
        self.raw_df = df

        # Scale machine breakdown proportionally to new total_kwh
        factor = total_kwh / max(1.0, float(SEP_TOTAL_KWH))
        self.machines = {m: round(k * factor, 1) for m, k in MACHINE_KWH.items()}

        return {
            "success": True,
            "mode": "data_parsed",
            "rows": len(df),
            "total_kwh": self.total_kwh,
            "peak_kw": self.peak_kw,
            "avg_pf": self.avg_pf,
            "specific_energy": self.specific_energy,
            "message": f"Successfully parsed {len(df)} interval rows from {filename}. Live dashboard updated.",
        }

    def ingest_bill(self, extracted: dict, filename: str) -> Dict[str, Any]:
        """Update active plant state using metrics extracted from an electricity bill."""
        total_kwh = extracted.get("total_kwh", self.total_kwh)
        total_amount = extracted.get("total_amount_inr", self.total_bill_inr)
        avg_pf = extracted.get("power_factor", self.avg_pf)
        max_demand_kva = extracted.get("max_demand_kva", self.peak_kw / max(0.01, self.avg_pf))

        self.source = "user_uploaded_bill_ocr"
        self.filename = filename
        self.total_kwh = round(float(total_kwh), 1)
        self.total_bill_inr = round(float(total_amount), 0)
        self.avg_pf = round(float(avg_pf), 3)
        self.peak_kw = round(float(max_demand_kva * self.avg_pf), 1)
        self.specific_energy = round(self.total_kwh / 12_580, 3)
        self.deviation_pct = round((self.specific_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)

        # Scale machine breakdown proportionally
        factor = self.total_kwh / max(1.0, float(SEP_TOTAL_KWH))
        self.machines = {m: round(k * factor, 1) for m, k in MACHINE_KWH.items()}

        return {
            "success": True,
            "mode": "bill_ocr_parsed",
            "total_kwh": self.total_kwh,
            "total_bill_inr": self.total_bill_inr,
            "peak_kw": self.peak_kw,
            "avg_pf": self.avg_pf,
            "message": f"Successfully extracted bill data from {filename}. Live dashboard updated.",
        }


# Singleton active data store
active_plant = ActivePlantData()

