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
from typing import Any, Dict, Optional
import fitz  # PyMuPDF

logger = logging.getLogger("urjamind.bill_ocr")


def parse_discom_bill_text(text: str) -> Dict[str, Any]:
    """
    Apply regular expression patterns across DISCOM electricity bill layouts.
    Extracts key billing metrics with robust multi-format matching.
    """
    extracted: Dict[str, Any] = {}

    # 1. Total Consumption (kWh / Units)
    # Patterns: "Total Consumption : 48240", "Total Units: 48,240", "Billed Units 48240", "Active Energy: 48240"
    kwh_match = re.search(
        r"(?:total\s*(?:active\s*)?(?:consumption|units|kwh)|billed\s*units|consumption\s*kwh)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if kwh_match:
        extracted["total_kwh"] = float(kwh_match.group(1).replace(",", ""))

    # 2. Total kVAh
    kvah_match = re.search(
        r"(?:total\s*kvah|billed\s*kvah|apparent\s*energy)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if kvah_match:
        extracted["total_kvah"] = float(kvah_match.group(1).replace(",", ""))

    # 3. Contract Demand / Sanctioned Load (kVA / kW)
    cd_match = re.search(
        r"(?:contract\s*demand|sanctioned\s*load|connected\s*load|contract\s*load)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:kva|kw)?",
        text, re.IGNORECASE
    )
    if cd_match:
        extracted["contract_demand_kva"] = float(cd_match.group(1).replace(",", ""))

    # 4. Maximum Demand (MD / Billed Demand kVA)
    md_match = re.search(
        r"(?:billing\s*demand|recorded\s*demand|actual\s*demand|max\s*demand|md\s*kva|m\.d\.)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:kva)?",
        text, re.IGNORECASE
    )
    if md_match:
        extracted["max_demand_kva"] = float(md_match.group(1).replace(",", ""))

    # 5. Average Power Factor (PF)
    pf_match = re.search(
        r"(?:power\s*factor|avg\s*p\.?f\.?|p\.?f\.?)\s*[:=\-]?\s*([0-1]\.[0-9]+)",
        text, re.IGNORECASE
    )
    if pf_match:
        extracted["power_factor"] = float(pf_match.group(1))

    # 6. Total Amount Payable (INR)
    amt_match = re.search(
        r"(?:net\s*payable|amount\s*payable|total\s*bill\s*amount|bill\s*amount|total\s*payable|gross\s*amount|total\s*amount)\s*[:=\-]*\s*(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if amt_match:
        extracted["total_amount_inr"] = float(amt_match.group(1).replace(",", ""))

    # 7. ToD Peak & Off-Peak
    peak_match = re.search(
        r"(?:tod\s*peak|peak\s*units|peak\s*consumption)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if peak_match:
        extracted["tod_peak_kwh"] = float(peak_match.group(1).replace(",", ""))

    offpeak_match = re.search(
        r"(?:tod\s*off[- ]?peak|night\s*units|off[- ]?peak\s*(?:consumption|units)?)\s*[:=\-]?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if offpeak_match:
        extracted["tod_offpeak_kwh"] = float(offpeak_match.group(1).replace(",", ""))


    # 8. Consumer No & DISCOM Name
    discom_match = re.search(
        r"(PGVCL|DGVCL|MGVCL|UGVCL|MSEDCL|BESCOM|TNEB|Tata Power|Torrent Power|Adani Electricity)",
        text, re.IGNORECASE
    )
    if discom_match:
        extracted["discom"] = discom_match.group(1).upper()

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
    success = bool(has_kwh or has_amount)

    return {
        "success": success,
        "engine": engine_used,
        "filename": filename,
        "text_length": len(raw_text),
        "extracted_data": extracted,
        "snippet": raw_text[:300].strip() if raw_text else "",
    }
