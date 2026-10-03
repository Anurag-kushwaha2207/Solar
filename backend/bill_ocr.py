"""
Indian DISCOM Electricity Bill Parser & OCR Engine
===================================================
Extracts structured billing & technical telemetry from uploaded DISCOM bills:
- Total Units (kWh / kVAh)
- Contract Demand / Sanctioned Load (kVA / kW)
- Maximum Demand Recorded / Billed Demand (kVA)
- Average Power Factor (PF)
- Tariff Category (HT-1, LT-MD, etc.)
- ToD Consumption Breakdown (Peak, Normal, Off-Peak)
- Total Amount Payable (INR)
- Power Factor Penalty / Rebate

Supports:
1. Native Digital PDF bills (PGVCL, DGVCL, MSEDCL, BESCOM, TNEB, Tata Power) via PyMuPDF / PyPDF2
1. Scanned paper bills & photos (JPG, PNG, WEBP) via Claude Vision AI OCR
3. Text / CSV transcripts
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import io
from typing import Any, Dict, Optional, Tuple
import fitz  # PyMuPDF

logger = logging.getLogger("urjamind.bill_ocr")


def parse_key_value_table(text: str) -> Dict[str, Any]:
    """
    Parse PDFs with a two-column key-value table (Field | Value).
    Handles both two-column (tab/spaces) and alternating-line (PyMuPDF) formats.
    """
    extracted: Dict[str, Any] = {}
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

    # Fallback: alternating-line format (PyMuPDF output: key line, then value line)
    if not kv_map:
        known_bill_fields = {
            "consumer name", "customer name", "company", "billing name",
            "consumer no.", "consumer no", "account no", "meter no",
            "billing month", "bill month", "billing period", "period",
            "units consumed", "total units", "energy consumed",
            "maximum demand", "max demand",
            "power factor",
            "time-of-day charges", "tod charges",
            "energy charges", "demand charges",
            "total bill amount", "net payable", "amount payable", "total amount",
            "due date", "field", "dummy value"
        }
        i = 0
        while i < len(lines) - 1:
            key_candidate = lines[i].lower()
            val_candidate = lines[i + 1]
            if key_candidate in known_bill_fields:
                kv_map[key_candidate] = val_candidate
                i += 2
            else:
                i += 1

    # Consumer / Company Name
    for k in ["consumer name", "customer name", "company", "billing name", "name of consumer"]:
        if k in kv_map:
            name = re.sub(r'\s*\(dummy\)\s*', '', kv_map[k], flags=re.IGNORECASE).strip()
            if len(name) >= 3:
                extracted["consumer_name"] = name
            break

    # Billing Month
    for k in ["billing month", "bill month", "billing period", "bill period", "period"]:
        if k in kv_map:
            extracted["month"] = kv_map[k]
            break

    # Units / kWh
    for k in ["units consumed", "total units", "energy consumed", "total kwh", "units"]:
        if k in kv_map:
            nums = re.findall(r'[\d,]+(?:\.\d+)?', kv_map[k])
            if nums:
                extracted["total_kwh"] = float(nums[0].replace(',', ''))
            break

    # Maximum Demand
    for k in ["maximum demand", "max demand", "billed demand", "md kva", "recorded demand"]:
        if k in kv_map:
            nums = re.findall(r'[\d,]+(?:\.\d+)?', kv_map[k])
            if nums:
                extracted["max_demand_kva"] = float(nums[0].replace(',', ''))
            break

    # Power Factor
    for k in ["power factor", "avg pf", "p.f.", "pf"]:
        if k in kv_map:
            nums = re.findall(r'0\.\d+|\d+\.\d+', kv_map[k])
            if nums:
                pf = float(nums[0])
                if 0.5 <= pf <= 1.0:
                    extracted["power_factor"] = pf
            break

    # Total Bill Amount
    for k in ["total bill amount", "net payable", "amount payable", "total amount", "bill amount", "total payable", "gross amount"]:
        if k in kv_map:
            raw = kv_map[k]
            # Remove (dummy), all currency symbols (₹, I, n, N, Rs), spaces
            cleaned = re.sub(r'\(dummy\)', '', raw, flags=re.IGNORECASE)
            cleaned = re.sub(r'[^\d,.]', '', cleaned)  # keep only digits, commas, dots
            # Remove commas and parse (handles Indian format 1,76,450)
            cleaned = cleaned.replace(',', '')
            if cleaned:
                try:
                    extracted["total_amount_inr"] = float(cleaned)
                except ValueError:
                    pass
            break

    # PF Penalty / ToD charges
    for k in ["pf penalty", "power factor penalty", "time-of-day charges", "tod charges"]:
        if k in kv_map:
            raw = kv_map[k]
            cleaned = re.sub(r'\(dummy\)', '', raw, flags=re.IGNORECASE)
            cleaned = re.sub(r'[^\d,.]', '', cleaned)
            cleaned = cleaned.replace(',', '')
            if cleaned:
                try:
                    extracted["pf_penalty_inr"] = float(cleaned)
                except ValueError:
                    pass

    # DISCOM
    discom_match = re.search(
        r"(PGVCL|DGVCL|MGVCL|UGVCL|MSEDCL|BESCOM|TNEB|Tata Power|Torrent Power|Adani Electricity|BSES|CESC|JVVNL|AVVNL|DHBVN|UHBVN|UPPCL|WBSEDCL|APDCL|KSEB)",
        text, re.IGNORECASE
    )
    if discom_match:
        extracted["discom"] = discom_match.group(1).upper()

    return extracted


def parse_discom_bill_text(text: str) -> Dict[str, Any]:
    """
    Parse electricity bill text. First tries key-value table parsing,
    then supplements with regex for any missing fields.
    """
    # Step 1: key-value table parse (handles dummy PDFs and structured formats)
    extracted = parse_key_value_table(text)

    # Step 2: regex fallback for fields not found by key-value parser
    if "total_kwh" not in extracted:
        m = re.search(
            r"(?:total\s*(?:active\s*)?(?:consumption|units|kwh)|billed\s*units|units\s*consumed)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
            text, re.IGNORECASE
        )
        if m:
            extracted["total_kwh"] = float(m.group(1).replace(",", ""))

    if "total_kvah" not in extracted:
        m = re.search(
            r"(?:total\s*kvah|billed\s*kvah|apparent\s*energy)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
            text, re.IGNORECASE
        )
        if m:
            extracted["total_kvah"] = float(m.group(1).replace(",", ""))

    if "contract_demand_kva" not in extracted:
        m = re.search(
            r"(?:contract\s*demand|sanctioned\s*load|connected\s*load)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:kva|kw)?",
            text, re.IGNORECASE
        )
        if m:
            extracted["contract_demand_kva"] = float(m.group(1).replace(",", ""))

    if "max_demand_kva" not in extracted:
        m = re.search(
            r"(?:billing\s*demand|recorded\s*demand|max\s*demand|maximum\s*demand|m\.d\.)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:kva)?",
            text, re.IGNORECASE
        )
        if m:
            extracted["max_demand_kva"] = float(m.group(1).replace(",", ""))

    if "power_factor" not in extracted:
        m = re.search(
            r"(?:power\s*factor|avg\s*p\.?f\.?|p\.?f\.?)\s*[:=\-]?\s*([0-1]\.[0-9]+)",
            text, re.IGNORECASE
        )
        if m:
            extracted["power_factor"] = float(m.group(1))

    if "total_amount_inr" not in extracted:
        m = re.search(
            r"(?:net\s*payable|amount\s*payable|total\s*bill\s*amount|bill\s*amount|total\s*payable|gross\s*amount|total\s*amount)\s*[:=\-]*\s*(?:rs\.?|inr|[\u20b9n])?\s*([0-9,]+(?:\.[0-9]+)?)",
            text, re.IGNORECASE
        )
        if m:
            extracted["total_amount_inr"] = float(m.group(1).replace(",", ""))

    if "tod_peak_kwh" not in extracted:
        m = re.search(
            r"(?:tod\s*peak|peak\s*units|peak\s*consumption)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
            text, re.IGNORECASE
        )
        if m:
            extracted["tod_peak_kwh"] = float(m.group(1).replace(",", ""))

    if "tod_offpeak_kwh" not in extracted:
        m = re.search(
            r"(?:tod\s*off[- ]?peak|night\s*units|off[- ]?peak\s*(?:consumption|units)?)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
            text, re.IGNORECASE
        )
        if m:
            extracted["tod_offpeak_kwh"] = float(m.group(1).replace(",", ""))

    if "discom" not in extracted:
        m = re.search(
            r"(PGVCL|DGVCL|MGVCL|UGVCL|MSEDCL|BESCOM|TNEB|Tata Power|Torrent Power|Adani Electricity|BSES|CESC|JVVNL|AVVNL|DHBVN|UHBVN|UPPCL|WBSEDCL|APDCL|KSEB)",
            text, re.IGNORECASE
        )
        if m:
            extracted["discom"] = m.group(1).upper()

    if "consumer_name" not in extracted:
        m = re.search(
            r"(?:consumer\s*name|name\s*of\s*consumer|customer\s*name|company\s*name|m\/s\.?|billing\s*name)\s*[:=\-]?\s*([A-Za-z0-9\s\.\,\&\-\(\)\/]{3,60}?)(?:\n|\r|address|consumer|acc|tariff|bill|date|meter|pin|gstin)",
            text, re.IGNORECASE
        )
        if m:
            c_name = re.sub(r'\s*\(dummy\)\s*', '', m.group(1), flags=re.IGNORECASE).strip(" :,-\t\r\n")
            if len(c_name) >= 3 and not any(skip in c_name.lower() for skip in ["address", "meter", "tariff"]):
                extracted["consumer_name"] = c_name
        else:
            m2 = re.search(
                r"([A-Za-z0-9\s\.\,\&\-]{3,50}\s+(?:pvt\.?\s*ltd\.?|ltd\.?|limited|industries|enterprise[s]?|foundry|engineering|textiles|polymers|steel[s]?|casting[s]?|works|mills|forge|manufacturing))\b",
                text, re.IGNORECASE
            )
            if m2:
                name = re.sub(r'\s*\(dummy\)\s*', '', m2.group(1), flags=re.IGNORECASE).strip()
                extracted["consumer_name"] = name

    if "month" not in extracted:
        m = re.search(
            r"(?:bill\s*(?:month|period|for\s*month)|billing\s*(?:period|month))\s*[:=\-]?\s*([A-Za-z0-9\s\-\/\.]{3,30}?)(?:\n|\r|bill\s*date|due\s*date|reading)",
            text, re.IGNORECASE
        )
        if m:
            extracted["month"] = m.group(1).strip(" :,-\t\r\n")
        else:
            m2 = re.search(
                r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[ -_]?(\d{4})\b",
                text, re.IGNORECASE
            )
            if m2:
                extracted["month"] = f"{m2.group(1)} {m2.group(2)}"

    return extracted


def extract_text_from_pdf(content_bytes: bytes) -> str:
    """Extract plain text from an in-memory PDF buffer using PyMuPDF."""
    text_chunks = []
    with fitz.open(stream=content_bytes, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_chunks.append(page.get_text())
    return "\n".join(text_chunks)


def extract_bill_from_image_claude(
    image_bytes: bytes,
    media_type: str = "image/jpeg",
) -> Dict[str, Any]:
    """
    Extract structured telemetry from bill photos using Claude Vision API.
    Extracts total_kwh, total_kvah, max_demand_kva, power_factor, total_amount_inr, discom, and billing month.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_api_key_here":
        logger.info("Claude API key not set, using demo fallback for photo OCR")
        return {}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

        prompt = (
            "You are an expert OCR parser for Indian DISCOM industrial/commercial electricity bills (e.g. PGVCL, DGVCL, MSEDCL, BESCOM, TNEB, Tata Power).\n"
            "Examine this bill image carefully and extract all billing metrics.\n"
            "Return ONLY a valid JSON object with the following fields (use null if not visible):\n"
            "{\n"
            '  "total_kwh": <float or null>,\n'
            '  "total_kvah": <float or null>,\n'
            '  "max_demand_kva": <float or null>,\n'
            '  "contract_demand_kva": <float or null>,\n'
            '  "power_factor": <float or null>,\n'
            '  "total_amount_inr": <float or null>,\n'
            '  "tod_peak_kwh": <float or null>,\n'
            '  "tod_offpeak_kwh": <float or null>,\n'
            '  "discom": <string or null>,\n'
            '  "month": <string or null>\n'
            "}\n"
            "Strict JSON only without markdown code blocks."
        )

        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_img,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        content_text = resp.content[0].text.strip()
        clean_json = re.sub(r"^```(?:json)?\s*", "", content_text, flags=re.MULTILINE)
        clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE).strip()
        parsed = json.loads(clean_json)

        result: Dict[str, Any] = {}
        for k, v in parsed.items():
            if v is not None:
                if k in ("total_kwh", "total_kvah", "max_demand_kva", "contract_demand_kva", "power_factor", "total_amount_inr", "tod_peak_kwh", "tod_offpeak_kwh"):
                    try:
                        result[k] = float(v)
                    except (ValueError, TypeError):
                        pass
                else:
                    result[k] = str(v)
        return result
    except Exception as e:
        logger.warning("Claude Vision OCR error: %s", e)
        return {}


def validate_bill_telemetry(extracted: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Sanity validation for extracted electricity bill metrics.
    Prevents hallucinated or corrupted OCR telemetry from contaminating analytics.
    Rules:
    - total_kwh > 0 and <= 50,000,000
    - 0.5 <= power_factor <= 1.0 (if present)
    - total_amount_inr > 0 (if present)
    - max_demand_kva > 0 (if present)
    """
    if not extracted:
        return False, "No data extracted from document"

    if "total_kwh" in extracted:
        try:
            kwh = float(extracted["total_kwh"])
            if kwh <= 0:
                return False, f"Invalid total_kwh ({kwh}): Energy consumption must be strictly positive."
            if kwh > 50_000_000:
                return False, f"Unrealistic total_kwh ({kwh}): Exceeds industrial plant threshold."
        except (ValueError, TypeError):
            return False, f"Non-numeric total_kwh value: {extracted['total_kwh']}"

    if "power_factor" in extracted:
        try:
            pf = float(extracted["power_factor"])
            if pf < 0.5 or pf > 1.0:
                return False, f"Physically impossible Power Factor ({pf}): Power factor must satisfy 0.5 <= PF <= 1.0."
        except (ValueError, TypeError):
            return False, f"Non-numeric power_factor value: {extracted['power_factor']}"

    if "total_amount_inr" in extracted:
        try:
            amt = float(extracted["total_amount_inr"])
            if amt <= 0:
                return False, f"Invalid total_amount_inr ({amt}): Billed amount must be strictly positive."
        except (ValueError, TypeError):
            return False, f"Non-numeric total_amount_inr value: {extracted['total_amount_inr']}"

    if "max_demand_kva" in extracted:
        try:
            md = float(extracted["max_demand_kva"])
            if md <= 0:
                return False, f"Invalid max_demand_kva ({md}): Maximum demand must be positive."
        except (ValueError, TypeError):
            return False, f"Non-numeric max_demand_kva value: {extracted['max_demand_kva']}"

    return True, None


def process_uploaded_bill(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Main entry point for processing an uploaded electricity bill.
    Supports:
    1. Digital PDFs (PGVCL/DGVCL/MSEDCL text extraction via PyMuPDF)
    2. Photos and scanned images (JPG/PNG/WEBP via Claude Vision AI OCR)
    3. Scanned PDFs (renders page to image and runs Claude Vision AI OCR)
    4. Text/CSV bill logs
    """
    raw_text = ""
    engine_used = "Text Parser"
    extracted: Dict[str, Any] = {}
    lower_fn = filename.lower()

    image_ext_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    is_image = any(lower_fn.endswith(ext) for ext in image_ext_map)

    try:
        # A. Direct Bill Photo (JPG, PNG, WEBP)
        if is_image:
            ext = next(e for e in image_ext_map if lower_fn.endswith(e))
            media_type = image_ext_map[ext]
            engine_used = "Claude Vision AI OCR"
            extracted = extract_bill_from_image_claude(content_bytes, media_type)

        # B. PDF Document
        elif lower_fn.endswith(".pdf"):
            raw_text = extract_text_from_pdf(content_bytes)
            engine_used = "PyMuPDF Digital Text Engine"
            extracted = parse_discom_bill_text(raw_text)

            # Fallback for Scanned PDF without native text: Render first page and run Claude Vision OCR
            if not extracted and len(content_bytes) > 0:
                try:
                    with fitz.open(stream=content_bytes, filetype="pdf") as doc:
                        if len(doc) > 0:
                            pix = doc[0].get_pixmap(dpi=150)
                            png_bytes = pix.tobytes("png")
                            vision_extracted = extract_bill_from_image_claude(png_bytes, "image/png")
                            if vision_extracted:
                                extracted = vision_extracted
                                engine_used = "Claude Vision (Scanned PDF OCR)"
                except Exception as sc_err:
                    logger.debug("Scanned PDF OCR attempt error: %s", sc_err)

        # C. Text / CSV Transcripts
        else:
            raw_text = content_bytes.decode("utf-8", errors="ignore")
            engine_used = "Direct File Parser"
            extracted = parse_discom_bill_text(raw_text)

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract document contents: {str(e)}",
            "engine": engine_used,
        }

    has_kwh = "total_kwh" in extracted
    has_amount = "total_amount_inr" in extracted
    preliminary_success = bool(has_kwh or has_amount)

    if preliminary_success:
        is_valid, validation_error = validate_bill_telemetry(extracted)
        if not is_valid:
            return {
                "success": False,
                "validation_failed": True,
                "validation_error": validation_error,
                "error": validation_error,
                "engine": engine_used,
                "filename": filename,
                "text_length": len(raw_text),
                "extracted_data": extracted,
                "snippet": raw_text[:300].strip() if raw_text else "",
            }

    return {
        "success": preliminary_success,
        "engine": engine_used,
        "filename": filename,
        "text_length": len(raw_text),
        "extracted_data": extracted,
        "snippet": raw_text[:300].strip() if raw_text else "",
    }
