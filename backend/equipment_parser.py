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

def parse_equipment_from_kv_table(text: str) -> List[Dict[str, Any]]:
    """
    Parse equipment PDFs with key-value format.
    Handles both:
    - Two-column format: 'Machine Name   CNC Production Machine'
    - Alternating line format (PyMuPDF output): key on line N, value on line N+1
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    kv_map = {}

    # Try two-column format first (tab or 2+ spaces)
    for line in lines:
        parts = re.split(r'\t|  +', line)
        if len(parts) >= 2:
            key = parts[0].strip().lower()
            val = parts[-1].strip()
            if key and val and key != val.lower():
                kv_map[key] = val

    # If no KV pairs found, try alternating-line format
    if not kv_map:
        known_field_names = {
            "company", "equipment id", "machine name", "equipment name",
            "equipment type", "rated power", "quantity", "motor type",
            "installation year", "operating hours/day", "estimated efficiency",
            "status", "maintenance cycle", "field", "dummy value"
        }
        i = 0
        while i < len(lines) - 1:
            key_candidate = lines[i].strip().lower()
            val_candidate = lines[i + 1].strip()
            # Accept if the key matches a known field name
            if key_candidate in known_field_names:
                kv_map[key_candidate] = val_candidate
                i += 2
            else:
                i += 1

    # Detect if this looks like an equipment form
    kv_indicator_keys = {"machine name", "equipment name", "rated power", "quantity",
                         "equipment type", "motor type", "equipment id"}
    if not set(kv_map.keys()).intersection(kv_indicator_keys):
        return []  # Not a key-value equipment form

    # --- Extract fields ---
    machine_name = None
    for k in ["machine name", "equipment name", "item name", "description"]:
        if k in kv_map:
            machine_name = re.sub(r'\s*\(dummy\)\s*', '', kv_map[k], flags=re.IGNORECASE).strip()
            break

    # Rating in kW
    rating_kw = 0.0
    for k in ["rated power", "rating", "power rating", "capacity", "rated kw", "kw rating"]:
        if k in kv_map:
            kw_m = re.search(r'([\d.]+)\s*(?:kw|k\.w\.)', kv_map[k], re.IGNORECASE)
            hp_m = re.search(r'([\d.]+)\s*(?:hp|h\.p\.)', kv_map[k], re.IGNORECASE)
            if kw_m:
                rating_kw = float(kw_m.group(1))
            elif hp_m:
                rating_kw = round(float(hp_m.group(1)) * 0.746, 1)
            else:
                nums = re.findall(r'[\d.]+', kv_map[k])
                if nums:
                    rating_kw = float(nums[0])
            break

    # Quantity
    qty = 1
    for k in ["quantity", "qty", "count", "nos", "units", "number"]:
        if k in kv_map:
            nums = re.findall(r'\d+', kv_map[k])
            if nums:
                qty = int(nums[0])
            break

    # Operating hours → duty factor
    duty_factor = 0.60
    for k in ["operating hours/day", "operating hours per day", "hours/day", "duty cycle"]:
        if k in kv_map:
            nums = re.findall(r'[\d.]+', kv_map[k])
            if nums:
                hours = float(nums[0])
                duty_factor = round(min(hours / 24.0, 0.95), 2)
            break

    # Efficiency
    efficiency = 0.88
    for k in ["estimated efficiency", "efficiency", "rated efficiency"]:
        if k in kv_map:
            nums = re.findall(r'[\d.]+', kv_map[k])
            if nums:
                eff = float(nums[0])
                efficiency = eff / 100.0 if eff > 1 else eff
            break

    # Machine type from Equipment Type field or name keywords
    machine_type = "industrial_equipment"
    type_str = kv_map.get("equipment type", kv_map.get("motor type", machine_name or "")).lower()
    for kw, meta in DEFAULT_EQUIPMENT_KEYWORDS.items():
        if kw in type_str:
            machine_type = meta["type"]
            duty_factor = meta.get("duty_factor", duty_factor)
            break

    if not machine_name:
        machine_name = kv_map.get("equipment type", "Unknown Equipment")
        machine_name = re.sub(r'\s*\(dummy\)\s*', '', machine_name, flags=re.IGNORECASE).strip()

    if rating_kw <= 0:
        rating_kw = 22.0  # Sensible default

    # If quantity > 1 (e.g. 4 CNC machines), expand into individual physical machine units
    if 1 < qty <= 8:
        machines = []
        for unit_idx in range(1, qty + 1):
            machines.append({
                "name": f"{machine_name} #{unit_idx} ({rating_kw:.0f} kW)",
                "raw_name": f"{machine_name} #{unit_idx}",
                "rating_kw": rating_kw,
                "quantity": 1,
                "total_kw": rating_kw,
                "duty_factor": duty_factor,
                "type": machine_type,
                "efficiency": efficiency,
            })
        # Account for common plant auxiliary & lighting load
        aux_kw = round(rating_kw * 0.15, 1)
        machines.append({
            "name": "Plant Lighting & Auxiliaries",
            "raw_name": "Lighting & Aux",
            "rating_kw": aux_kw,
            "quantity": 1,
            "total_kw": aux_kw,
            "duty_factor": 0.40,
            "type": "utilities",
            "efficiency": 0.95,
        })
        return machines

    formatted_name = machine_name
    if qty > 1 and f"x{qty}" not in formatted_name.lower() and f"*{qty}" not in formatted_name:
        formatted_name = f"{formatted_name} (x{qty})"
    if f"{int(rating_kw)} kW" not in formatted_name and f"{rating_kw} kW" not in formatted_name:
        formatted_name = f"{formatted_name} ({rating_kw:.0f} kW)" if rating_kw == int(rating_kw) else f"{formatted_name} ({rating_kw:.1f} kW)"

    aux_kw = round(rating_kw * 0.15, 1)
    return [
        {
            "name": formatted_name,
            "raw_name": machine_name,
            "rating_kw": rating_kw,
            "quantity": qty,
            "total_kw": round(rating_kw * qty, 1),
            "duty_factor": duty_factor,
            "type": machine_type,
            "efficiency": efficiency,
        },
        {
            "name": "Plant Lighting & Auxiliaries",
            "raw_name": "Lighting & Aux",
            "rating_kw": aux_kw,
            "quantity": 1,
            "total_kw": aux_kw,
            "duty_factor": 0.40,
            "type": "utilities",
            "efficiency": 0.95,
        }
    ]




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
            # First try key-value table format (handles dummy/structured single-machine PDFs)
            machines = parse_equipment_from_kv_table(pdf_text)
            if not machines:
                # Fall through to general text parser
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
