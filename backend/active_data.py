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
        self.pf_penalty_inr = float(SEP_PF_PENALTY_INR)
        self.production_kg = 12580.0
        self.specific_energy = float(SEP_SEC_ENERGY)
        self.deviation_pct = float(SEP_DEVIATION_PCT)
        self.peak_kw = float(round(187.4 * SEP_AVG_PF, 1))
        self.contract_kva = float(CONTRACT_KVA)
        self.max_demand_kva = 187.4
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
        """Parse uploaded interval CSV or PDF interval data and compute real analytical metrics."""
        lower_fn = filename.lower()

        # Handle PDF interval data (key-value summary format)
        if lower_fn.endswith(".pdf"):
            return self._ingest_interval_pdf(file_bytes, filename)

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

    def _ingest_interval_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse interval data PDF (key-value summary format like the dummy PDFs)."""
        import re
        import fitz
        try:
            text_chunks = []
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text_chunks.append(page.get_text())
            text = "\n".join(text_chunks)
        except Exception as e:
            return {"success": False, "mode": "demo_values_used", "reason": f"PDF read error: {e}"}

        # Build key-value map — try two-column first, then alternating lines
        kv_map = {}
        for line in text.splitlines():
            parts = re.split(r'\t|  +', line.strip())
            if len(parts) >= 2:
                key = parts[0].strip().lower()
                val = parts[-1].strip()
                if key and val and key != val.lower():
                    kv_map[key] = val

        # Fallback: alternating-line format (PyMuPDF output)
        if not kv_map:
            known_field_names = {
                "consumer id", "meter id", "date", "interval",
                "00:00 load", "06:00 load", "09:00 load", "12:00 load",
                "15:00 load", "18:00 load", "21:00 load", "daily energy",
                "field", "dummy value"
            }
            clean_lines = [l.strip() for l in text.splitlines() if l.strip()]
            i = 0
            while i < len(clean_lines) - 1:
                key_candidate = clean_lines[i].lower()
                val_candidate = clean_lines[i + 1]
                if key_candidate in known_field_names:
                    kv_map[key_candidate] = val_candidate
                    i += 2
                else:
                    i += 1

        # Detect if it's an interval-data PDF
        interval_keys = {"daily energy", "interval", "meter id", "consumer id"}
        if not set(kv_map.keys()).intersection(interval_keys):
            return {"success": False, "mode": "demo_values_used", "reason": "Not recognized as interval data PDF."}

        # Extract daily energy
        daily_kwh = 0.0
        for k in ["daily energy", "total daily energy", "energy (kwh)", "total kwh"]:
            if k in kv_map:
                nums = re.findall(r'[\d,]+(?:\.\d+)?', kv_map[k])
                if nums:
                    daily_kwh = float(nums[0].replace(',', ''))
                break

        # Extract peak load (maximum of the load readings)
        load_values = []
        for k, v in kv_map.items():
            if 'load' in k and ':' in k:
                nums = re.findall(r'[\d.]+', v)
                if nums:
                    load_values.append(float(nums[0]))

        peak_kw = max(load_values) if load_values else (daily_kwh / 16)  # assume 16h operating

        if daily_kwh > 0:
            if self.source == "user_uploaded_bill_ocr" and self.total_kwh > 0:
                # Retain verified monthly bill figure; sync peak load from interval measurements
                self.peak_kw = round(peak_kw, 1)
                return {
                    "success": True,
                    "mode": "interval_pdf_parsed",
                    "daily_kwh": daily_kwh,
                    "monthly_kwh_estimated": self.total_kwh,
                    "peak_kw": self.peak_kw,
                    "message": f"Interval data parsed: {daily_kwh:,.0f} kWh/day, peak {self.peak_kw} kW. Monthly bill ({self.total_kwh:,.0f} kWh) retained as source of truth.",
                    "note": "15-minute load profile synced with active monthly bill.",
                }

            # Extrapolate to 26 working days (note: this is one day's data)
            monthly_kwh = round(daily_kwh * 26, 1)
            self.source = "user_uploaded_interval_pdf"
            self.filename = filename
            self.total_kwh = monthly_kwh
            self.total_bill_inr = round(monthly_kwh * 6.08, 0)
            self.peak_kw = round(peak_kw, 1)
            self.specific_energy = round(self.total_kwh / max(1.0, self.production_kg), 3)
            self.deviation_pct = round((self.specific_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)
            self.recalculate_machine_energy()
            return {
                "success": True,
                "mode": "interval_pdf_parsed",
                "daily_kwh": daily_kwh,
                "monthly_kwh_estimated": monthly_kwh,
                "peak_kw": self.peak_kw,
                "message": f"Interval PDF parsed: {daily_kwh} kWh/day -> {monthly_kwh} kWh/month estimated (26 working days). Live dashboard updated.",
                "note": "This is a single-day snapshot. Monthly figure is an estimate.",
            }

        return {"success": False, "mode": "demo_values_used", "reason": "Could not extract daily energy from interval PDF."}

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
            clean_name = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
            if len(clean_name) > 3 and not clean_name.lower().startswith("bill"):
                self.plant_name = f"{clean_name} Plant"

        if extracted.get("discom"):
            self.discom = extracted["discom"]
        if extracted.get("month"):
            self.billing_period = extracted["month"]

        # Store pf_penalty from bill if present, else calculate
        if "pf_penalty_inr" in extracted:
            self.pf_penalty_inr = round(float(extracted["pf_penalty_inr"]), 0)
        else:
            # PF < 0.90 typically triggers penalty; use ToD charges as proxy if available
            self.pf_penalty_inr = round(self.pf_penalty_inr if hasattr(self, 'pf_penalty_inr') else 0.0, 0)

        self.source = "user_uploaded_bill_ocr"
        self.filename = filename
        self.total_kwh = round(float(total_kwh), 1)
        self.total_bill_inr = round(float(total_amount), 0)
        self.avg_pf = round(float(avg_pf), 3)
        self.max_demand_kva = round(float(max_demand_kva), 1)
        self.contract_kva = round(float(extracted.get("contract_demand_kva", max_demand_kva)), 1)
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
            days = res.get("days_detected", 30)
            raw_prod = res["total_production_kg"]
            epu = res.get("energy_per_unit", 0.0)

            if days == 1 and epu > 0:
                # Extrapolate monthly units matching the logged specific energy
                self.production_kg = round(self.total_kwh / max(0.01, epu), 1)
                self.specific_energy = epu
            elif days == 1:
                self.production_kg = round(raw_prod * 26, 1)
                self.specific_energy = round(self.total_kwh / max(1.0, self.production_kg), 3)
            else:
                self.production_kg = round(raw_prod, 1)
                self.specific_energy = round(self.total_kwh / max(1.0, self.production_kg), 3)

            self.deviation_pct = round((self.specific_energy - BASELINE_SEC_ENERGY) / BASELINE_SEC_ENERGY * 100, 1)
            return {
                "success": True,
                "status": "processed",
                "mode": "production_parsed",
                "file": filename,
                "days_detected": days,
                "total_production_kg": self.production_kg,
                "specific_energy": self.specific_energy,
                "deviation_pct": self.deviation_pct,
                "message": f"Successfully parsed {raw_prod:,.0f} units output from {filename}. Specific Energy updated to {self.specific_energy} kWh/unit!",
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
