"""
UrjaMind Active Data State Manager
==================================
Allows uploaded documents (electricity bills, interval CSVs, production logs,
and equipment registers) to dynamically update the live dashboard, KPIs,
machine disaggregation, and Copilot grounding with clean fallback to baseline.
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
from equipment_parser import process_equipment_file
from production_parser import process_production_file


class ActivePlantData:
    def __init__(self, tenant_id: str = "demo"):
        self.tenant_id = tenant_id
        self.reset_to_demo()

    def reset_to_demo(self):
        self.source = "demo_baseline"
        self.filename = "demo_rajkot_sep2026.csv"
        self.plant_name = PLANT_NAME
        self.discom = "PGVCL"
        self.billing_period = "Sep 2026"
        self.total_kwh = float(SEP_TOTAL_KWH)
        self.total_bill_inr = float(SEP_TOTAL_AMOUNT_INR)
        self.avg_pf = float(SEP_AVG_PF)
        self.production_kg = 12580.0
        self.specific_energy = float(SEP_SEC_ENERGY)
        self.deviation_pct = float(SEP_DEVIATION_PCT)
        self.peak_kw = float(round(187.4 * SEP_AVG_PF, 1))
        self.equipment_list: List[Dict[str, Any]] = []
        self.machines = dict(MACHINE_KWH)
        self.raw_df: Optional[pd.DataFrame] = None
        self.rows_count = 2880  # 30 days * 96 slots

    def recalculate_machine_energy(self):
        """Allocate total energy consumption across machines based on installed equipment or baseline."""
        if self.equipment_list:
            total_weight = sum(m["total_kw"] * m.get("duty_factor", 0.6) for m in self.equipment_list)
            if total_weight > 0:
                self.machines = {}
                allocated_so_far = 0.0
                for i, m in enumerate(self.equipment_list):
                    w = m["total_kw"] * m.get("duty_factor", 0.6)
                    share = w / total_weight
                    if i == len(self.equipment_list) - 1:
                        # Ensure sum equals total_kwh exactly
                        m_kwh = round(self.total_kwh - allocated_so_far, 1)
                    else:
                        m_kwh = round(self.total_kwh * share, 1)
                        allocated_so_far += m_kwh
                    self.machines[m["name"]] = max(0.0, m_kwh)
                return

        # Fallback to standard 5-machine profile scaled to active total_kwh
        factor = self.total_kwh / max(1.0, float(SEP_TOTAL_KWH))
        self.machines = {m: round(k * factor, 1) for m, k in MACHINE_KWH.items()}

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
            self.production_kg = float(df[prod_col].sum())

        # Update active state
        self.source = "user_uploaded_csv"
        self.filename = filename
        self.total_kwh = round(total_kwh, 1)
        self.total_bill_inr = round(total_kwh * 6.08, 0)
        self.avg_pf = round(avg_pf, 3)
        self.peak_kw = round(peak_kw, 1)
        self.specific_energy = round(self.total_kwh / max(1.0, self.production_kg), 3)
        self.deviation_pct = round((self.specific_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)
        self.rows_count = len(df)
        self.raw_df = df

        self.recalculate_machine_energy()

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
        from bill_ocr import validate_bill_telemetry
        is_valid, reason = validate_bill_telemetry(extracted)
        if not is_valid:
            return {
                "success": False,
                "status": "demo_fallback",
                "mode": "demo_values_used",
                "reason": reason,
                "message": f"Sanity check failed: {reason}. Demo baseline retained.",
            }

        total_kwh = extracted.get("total_kwh", self.total_kwh)
        total_amount = extracted.get("total_amount_inr", self.total_bill_inr)
        avg_pf = extracted.get("power_factor", self.avg_pf)
        max_demand_kva = extracted.get("max_demand_kva", self.peak_kw / max(0.01, self.avg_pf))

        # Dynamic Company Name & Billing Period
        if extracted.get("consumer_name"):
            self.plant_name = extracted["consumer_name"]
        elif not self.plant_name or self.plant_name == PLANT_NAME:
            # Derive clean company name from filename if consumer_name was omitted
            clean_name = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
            if len(clean_name) > 3 and not clean_name.lower().startswith("bill"):
                self.plant_name = f"{clean_name} Plant"

        if extracted.get("discom"):
            self.discom = extracted["discom"]
        if extracted.get("month"):
            self.billing_period = extracted["month"]

        self.source = "user_uploaded_bill_ocr"
        self.filename = filename
        self.total_kwh = round(float(total_kwh), 1)
        self.total_bill_inr = round(float(total_amount), 0)
        self.avg_pf = round(float(avg_pf), 3)
        self.peak_kw = round(float(max_demand_kva * self.avg_pf), 1)
        self.specific_energy = round(self.total_kwh / max(1.0, self.production_kg), 3)
        self.deviation_pct = round((self.specific_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)

        self.recalculate_machine_energy()

        return {
            "success": True,
            "status": "processed",
            "mode": "bill_ocr_parsed",
            "plant_name": self.plant_name,
            "total_kwh": self.total_kwh,
            "total_bill_inr": self.total_bill_inr,
            "peak_kw": self.peak_kw,
            "avg_pf": self.avg_pf,
            "message": f"Successfully extracted bill data for '{self.plant_name}' from {filename}. Live dashboard updated.",
        }

    def ingest_equipment(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse equipment register (PDF, CSV, Excel, Text) and dynamically update machine inventory."""
        res = process_equipment_file(file_bytes, filename)
        if res.get("success") and res.get("machines"):
            self.equipment_list = res["machines"]
            self.recalculate_machine_energy()
            return {
                "success": True,
                "status": "processed",
                "mode": "equipment_parsed",
                "file": filename,
                "machines_count": len(self.equipment_list),
                "total_installed_kw": res["total_installed_kw"],
                "machines": [m["name"] for m in self.equipment_list],
                "message": f"✅ Parsed {len(self.equipment_list)} machines ({res['total_installed_kw']} kW load) from equipment register. Machine disaggregation updated live!",
            }
        return {
            "success": False,
            "status": "demo_fallback",
            "mode": "demo_values_used",
            "file": filename,
            "machines_count": len(self.machines),
            "total_installed_kw": 355.0,
            "message": "Equipment register received — standard 5-machine profile active.",
        }

    def ingest_production(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse production log (PDF, CSV, Excel, Text) and dynamically recalculate Specific Energy Consumption (SEC)."""
        res = process_production_file(file_bytes, filename)
        if res.get("success") and res.get("total_production_kg", 0) > 0:
            self.production_kg = res["total_production_kg"]
            self.specific_energy = round(self.total_kwh / max(1.0, self.production_kg), 3)
            self.deviation_pct = round((self.specific_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)
            return {
                "success": True,
                "status": "processed",
                "mode": "production_parsed",
                "file": filename,
                "days_detected": res["days_detected"],
                "total_production_kg": self.production_kg,
                "specific_energy": self.specific_energy,
                "deviation_pct": self.deviation_pct,
                "message": f"✅ Parsed {self.production_kg:,.0f} kg production output from {filename}. Specific Energy updated to {self.specific_energy} kWh/kg!",
            }
        return {
            "success": False,
            "status": "demo_fallback",
            "mode": "demo_values_used",
            "file": filename,
            "days_detected": 30,
            "total_production_kg": 12580.0,
            "message": "Production log received (using standard 12,580 kg manufacturing benchmark).",
        }


class MultiTenantPlantStore:
    """Manages isolated active plant stores for each authenticated tenant / plantId."""
    def __init__(self):
        self._tenants: Dict[str, ActivePlantData] = {}
        self.default_plant = ActivePlantData("demo")

    def get_plant(self, tenant_id: Optional[str] = None) -> ActivePlantData:
        if not tenant_id or tenant_id in ("demo", "plant_demo", "1", "plant_1"):
            return self.default_plant
        if tenant_id not in self._tenants:
            self._tenants[tenant_id] = ActivePlantData(tenant_id)
        return self._tenants[tenant_id]

    def reset_to_demo(self):
        self.default_plant.reset_to_demo()
        self._tenants.clear()

    def __getattr__(self, name):
        return getattr(self.default_plant, name)


# Singleton active data store supporting both global baseline and multi-tenant isolation
active_plant_store = MultiTenantPlantStore()
active_plant = active_plant_store
get_plant_data = active_plant_store.get_plant
