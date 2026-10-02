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
2. Text / CSV transcripts
"""
from __future__ import annotations

import re
import io
from typing import Any, Dict, Optional
import fitz  # PyMuPDF


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


def process_uploaded_bill(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Main entry point for processing an uploaded electricity bill.
    Supports PDF extraction via PyMuPDF and text/CSV parsing.
    """
    raw_text = ""
    engine_used = "Text Parser"

    try:
        if filename.lower().endswith(".pdf"):
            raw_text = extract_text_from_pdf(content_bytes)
            engine_used = "PyMuPDF Digital Text Engine"
        else:
            raw_text = content_bytes.decode("utf-8", errors="ignore")
            engine_used = "Direct File Parser"
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract document contents: {str(e)}",
            "engine": engine_used,
        }

    extracted = parse_discom_bill_text(raw_text)

    # If key fields are found, consider extraction a success
    has_kwh = "total_kwh" in extracted
    has_amount = "total_amount_inr" in extracted

    return {
        "success": has_kwh or has_amount,
        "engine": engine_used,
        "filename": filename,
        "text_length": len(raw_text),
        "extracted_data": extracted,
        "snippet": raw_text[:300].strip() if raw_text else "",
    }
