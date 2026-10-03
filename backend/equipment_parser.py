"""
UrjaMind Equipment Register Parser
==================================
Parses industrial equipment lists / machine registers from:
- Tabular CSV & Excel files
- Digital PDFs (text & tables via PyMuPDF)
- Plain text / Form submissions

Extracts:
- Machine / Equipment Name
- Rated Power (kW / HP)
- Quantity
- Operating Duty Cycle / Category
Computes total connected load (kW) and dynamic NILM energy breakdown weights.
"""
from __future__ import annotations

import io
import re
import logging
from typing import Any, Dict, List, Tuple
import pandas as pd
import fitz  # PyMuPDF

logger = logging.getLogger("urjamind.equipment_parser")

# Default machine physics profiles & duty cycles
DEFAULT_EQUIPMENT_KEYWORDS = {
    "furnace": {"type": "heating", "duty_factor": 0.85, "default_pf": 0.92},
    "oven": {"type": "heating", "duty_factor": 0.75, "default_pf": 0.95},
    "boiler": {"type": "heating", "duty_factor": 0.80, "default_pf": 0.90},
    "compressor": {"type": "compressed_air", "duty_factor": 0.65, "default_pf": 0.85},
    "press": {"type": "motor_heavy", "duty_factor": 0.60, "default_pf": 0.88},
    "cnc": {"type": "precision_machining", "duty_factor": 0.70, "default_pf": 0.90},
    "lathe": {"type": "machining", "duty_factor": 0.55, "default_pf": 0.86},
    "milling": {"type": "machining", "duty_factor": 0.55, "default_pf": 0.86},
    "grinder": {"type": "machining", "duty_factor": 0.50, "default_pf": 0.85},
    "fettling": {"type": "machining", "duty_factor": 0.50, "default_pf": 0.84},
    "extruder": {"type": "heavy_process", "duty_factor": 0.75, "default_pf": 0.88},
    "molding": {"type": "heavy_process", "duty_factor": 0.70, "default_pf": 0.88},
    "conveyor": {"type": "motor_continuous", "duty_factor": 0.60, "default_pf": 0.85},
    "pump": {"type": "fluid_handling", "duty_factor": 0.60, "default_pf": 0.85},
    "chiller": {"type": "cooling", "duty_factor": 0.65, "default_pf": 0.86},
    "cooling": {"type": "cooling", "duty_factor": 0.55, "default_pf": 0.85},
    "hvac": {"type": "utilities", "duty_factor": 0.45, "default_pf": 0.82},
    "lighting": {"type": "utilities", "duty_factor": 0.40, "default_pf": 0.95},
    "transformer": {"type": "distribution", "duty_factor": 0.10, "default_pf": 0.90},
    "motor": {"type": "motor_general", "duty_factor": 0.55, "default_pf": 0.86},
}


def parse_equipment_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Extract equipment items from a pandas DataFrame (CSV/Excel)."""
    cols_lower = {c: str(c).strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=cols_lower)

    name_col = next((c for c in ["machine", "equipment", "equipment_name", "machine_name", "item", "description", "name"] if c in df.columns), None)
    kw_col = next((c for c in ["rating_kw", "kw", "power_kw", "kw_rating", "rating", "capacity_kw", "capacity"] if c in df.columns), None)
    hp_col = next((c for c in ["rating_hp", "hp", "power_hp", "hp_rating", "capacity_hp"] if c in df.columns), None)
    qty_col = next((c for c in ["qty", "quantity", "count", "nos", "units"] if c in df.columns), None)

    if not name_col and len(df.columns) > 0:
        # Fall back to first text column
        name_col = df.columns[0]

    machines: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        raw_name = str(row.get(name_col, "")).strip()
        if not raw_name or raw_name.lower() in ("nan", "none", "total", "sum"):
            continue

        # Determine kW rating
        rating_kw = 0.0
        if kw_col and pd.notna(row.get(kw_col)):
            try:
                rating_kw = float(re.findall(r"[-+]?\d*\.\d+|\d+", str(row[kw_col]))[0])
            except Exception:
                pass
        elif hp_col and pd.notna(row.get(hp_col)):
            try:
                hp_val = float(re.findall(r"[-+]?\d*\.\d+|\d+", str(row[hp_col]))[0])
                rating_kw = round(hp_val * 0.746, 1)
            except Exception:
                pass

        # If kW not in dedicated column, search inside name string (e.g. "Compressor 75 kW")
        if rating_kw <= 0:
            kw_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kw|k\.w\.)", raw_name, re.IGNORECASE)
            hp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hp|h\.p\.)", raw_name, re.IGNORECASE)
            if kw_match:
                rating_kw = float(kw_match.group(1))
            elif hp_match:
                rating_kw = round(float(hp_match.group(1)) * 0.746, 1)
            else:
                rating_kw = 15.0  # sensible default industrial rating

        # Determine Quantity
        qty = 1
        if qty_col and pd.notna(row.get(qty_col)):
            try:
                qty = int(re.findall(r"\d+", str(row[qty_col]))[0])
            except Exception:
                qty = 1
        else:
            qty_match = re.search(r"(?:x|×|qty:?|quantity:?)\s*(\d+)", raw_name, re.IGNORECASE)
            if qty_match:
                qty = int(qty_match.group(1))

        # Classify machine type and duty factor
        lower_name = raw_name.lower()
        duty_factor = 0.60
        machine_type = "industrial_equipment"
        for kw, meta in DEFAULT_EQUIPMENT_KEYWORDS.items():
            if kw in lower_name:
                duty_factor = meta["duty_factor"]
                machine_type = meta["type"]
                break

        formatted_name = raw_name
        if qty > 1 and f"×{qty}" not in formatted_name and f"x{qty}" not in formatted_name and f"(Qty: {qty})" not in formatted_name:
            formatted_name = f"{formatted_name} ×{qty}"
        if f"{int(rating_kw)} kW" not in formatted_name and f"{rating_kw} kW" not in formatted_name:
            formatted_name = f"{formatted_name} ({rating_kw:.0f} kW)" if rating_kw.is_integer() else f"{formatted_name} ({rating_kw:.1f} kW)"

        machines.append({
            "name": formatted_name,
            "raw_name": raw_name,
            "rating_kw": rating_kw,
            "quantity": qty,
            "total_kw": round(rating_kw * qty, 1),
            "duty_factor": duty_factor,
            "type": machine_type,
        })

    return machines


def parse_equipment_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse text lines from PDF or plain text to extract machine inventory."""
    lines = text.splitlines()
    machines: List[Dict[str, Any]] = []

    # Pattern for machine lines: e.g. "1. Air Compressor 75 kW x 2" or "Hydraulic Press - 45 kW"
    for line in lines:
        clean_line = line.strip()
        if len(clean_line) < 4:
            continue
        # Skip headers / footers
        if any(h in clean_line.lower() for h in ["page ", "total", "equipment list", "sr no", "sl no", "serial number"]):
            continue

        # Look for machine keywords
        has_machine_kw = any(kw in clean_line.lower() for kw in DEFAULT_EQUIPMENT_KEYWORDS.keys())
        # Or lines with explicit kW/HP ratings
        has_power_rating = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:kw|hp|k\.w\.|h\.p\.|kva)\b", clean_line, re.IGNORECASE))

        if has_machine_kw or has_power_rating:
            # Extract power rating
            kw_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kw|k\.w\.)", clean_line, re.IGNORECASE)
            hp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hp|h\.p\.)", clean_line, re.IGNORECASE)
            if kw_match:
                rating_kw = float(kw_match.group(1))
            elif hp_match:
                rating_kw = round(float(hp_match.group(1)) * 0.746, 1)
            else:
                rating_kw = 20.0

            # Extract quantity
            qty_match = re.search(r"(?:x|×|qty:?|quantity:?|nos:?)\s*(\d+)", clean_line, re.IGNORECASE)
            qty = int(qty_match.group(1)) if qty_match else 1

            # Clean name
            name_part = re.sub(r"^\d+[\.\)\-]\s*", "", clean_line)  # remove leading numbers "1. "
            name_part = re.sub(r"\s*[-–—:]\s*\d+.*$", "", name_part).strip()  # remove trailing details
            if len(name_part) < 3:
                name_part = clean_line

            # Determine duty factor
            duty_factor = 0.60
            machine_type = "industrial_equipment"
            for kw, meta in DEFAULT_EQUIPMENT_KEYWORDS.items():
                if kw in clean_line.lower():
                    duty_factor = meta["duty_factor"]
                    machine_type = meta["type"]
                    break

            formatted_name = name_part
            if qty > 1 and f"×{qty}" not in formatted_name and f"x{qty}" not in formatted_name:
                formatted_name = f"{formatted_name} ×{qty}"
            if f"{rating_kw} kW" not in formatted_name and f"{int(rating_kw)} kW" not in formatted_name:
                formatted_name = f"{formatted_name} ({rating_kw:.0f} kW)" if rating_kw.is_integer() else f"{formatted_name} ({rating_kw:.1f} kW)"

            machines.append({
                "name": formatted_name,
                "raw_name": name_part,
                "rating_kw": rating_kw,
                "quantity": qty,
                "total_kw": round(rating_kw * qty, 1),
                "duty_factor": duty_factor,
                "type": machine_type,
            })

    return machines


def process_equipment_file(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Main entry point to parse equipment register file."""
    lower_fn = filename.lower()
    machines: List[Dict[str, Any]] = []

    try:
        # A. CSV File
        if lower_fn.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content_bytes))
            machines = parse_equipment_from_df(df)

        # B. Excel File (.xlsx, .xls)
        elif lower_fn.endswith(".xlsx") or lower_fn.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content_bytes))
            machines = parse_equipment_from_df(df)

        # C. PDF File
        elif lower_fn.endswith(".pdf"):
            text_chunks = []
            with fitz.open(stream=content_bytes, filetype="pdf") as doc:
                for page in doc:
                    text_chunks.append(page.get_text())
            pdf_text = "\n".join(text_chunks)
            machines = parse_equipment_from_text(pdf_text)

        # D. Plain Text
        else:
            text = content_bytes.decode("utf-8", errors="ignore")
            machines = parse_equipment_from_text(text)

    except Exception as e:
        logger.warning("Equipment register parsing error: %s", e)

    # Fallback to standard industrial equipment mix if file could not be parsed into rows
    if not machines:
        return {
            "success": False,
            "mode": "demo_fallback",
            "message": "Equipment file received but machine rows could not be recognized. Default profile active.",
            "machines": [],
            "total_installed_kw": 355.0,
        }

    total_installed_kw = round(sum(m["total_kw"] for m in machines), 1)
    return {
        "success": True,
        "mode": "equipment_parsed",
        "file": filename,
        "machines_count": len(machines),
        "total_installed_kw": total_installed_kw,
        "machines": machines,
        "message": f"Successfully extracted {len(machines)} machines ({total_installed_kw} kW total installed load) from {filename}.",
    }
