"""
Ingestion Router — Transparently handles real CSV parsing and demo fallbacks.
Updates active_plant data store so uploaded interval data feeds the live dashboard.
"""
from fastapi import APIRouter, UploadFile, File, Form
from constants import (
    SEP_TOTAL_KWH, SEP_TOTAL_KVAH, SEP_MAX_DEMAND_KVA, SEP_AVG_PF,
    SEP_TOD_PEAK_KWH, SEP_TOD_OFFPEAK_KWH, SEP_TOTAL_AMOUNT_INR, SEP_PF_PENALTY_INR,
)
from active_data import active_plant

router = APIRouter()


from bill_ocr import process_uploaded_bill, validate_bill_telemetry


@router.post("/upload-bill")
async def upload_bill(file: UploadFile = File(...), plant_id: str = Form("1")):
    """
    Bill upload endpoint.
    Extracts consumption, demand, PF, and payable amount from digital PDF or text bills via PyMuPDF.
    Validates metrics against physical sanity rules before updating active plant state.
    """
    content = await file.read()
    ocr_res = process_uploaded_bill(content, file.filename)

    # 1. Check if extraction failed sanity checks (e.g. negative kWh, PF > 1.0)
    if ocr_res.get("validation_failed"):
        val_error = ocr_res.get("validation_error", "Sanity validation failed")
        return {
            "status": "demo_fallback",
            "mode": "demo_values_used",
            "validation_failed": True,
            "file": file.filename,
            "size_kb": round(len(content) / 1024, 1),
            "ocr_engine": ocr_res.get("engine", "OCR Parser"),
            "message": f"Bill metrics rejected by sanity check: {val_error} — demo baseline retained.",
            "validation_error": val_error,
            "raw_extracted": ocr_res.get("extracted_data", {}),
            "extracted": {
                "month": "Sep 2026",
                "total_kwh": SEP_TOTAL_KWH,
                "total_kvah": SEP_TOTAL_KVAH,
                "max_demand_kva": SEP_MAX_DEMAND_KVA,
                "power_factor": SEP_AVG_PF,
                "tod_peak_kwh": SEP_TOD_PEAK_KWH,
                "tod_offpeak_kwh": SEP_TOD_OFFPEAK_KWH,
                "total_amount_inr": SEP_TOTAL_AMOUNT_INR,
                "pf_penalty_inr": SEP_PF_PENALTY_INR,
            },
            "data_tier": 1,
        }

    # 2. If valid metrics were extracted and passed sanity checks
    if ocr_res.get("success"):
        extracted = ocr_res["extracted_data"]
        # Double-check sanity
        is_valid, val_error = validate_bill_telemetry(extracted)
        if not is_valid:
            return {
                "status": "demo_fallback",
                "mode": "demo_values_used",
                "validation_failed": True,
                "file": file.filename,
                "size_kb": round(len(content) / 1024, 1),
                "ocr_engine": ocr_res.get("engine", "OCR Parser"),
                "message": f"Bill metrics rejected by sanity check: {val_error} — demo baseline retained.",
                "validation_error": val_error,
                "raw_extracted": extracted,
                "extracted": {
                    "month": "Sep 2026",
                    "total_kwh": SEP_TOTAL_KWH,
                    "total_kvah": SEP_TOTAL_KVAH,
                    "max_demand_kva": SEP_MAX_DEMAND_KVA,
                    "power_factor": SEP_AVG_PF,
                    "tod_peak_kwh": SEP_TOD_PEAK_KWH,
                    "tod_offpeak_kwh": SEP_TOD_OFFPEAK_KWH,
                    "total_amount_inr": SEP_TOTAL_AMOUNT_INR,
                    "pf_penalty_inr": SEP_PF_PENALTY_INR,
                },
                "data_tier": 1,
            }

        # Do not ingest immediately: require user review & confirmation before updating live state
        return {
            "status": "requires_confirmation",
            "mode": "ocr_parsed_pending_confirmation",
            "file": file.filename,
            "size_kb": round(len(content) / 1024, 1),
            "ocr_engine": ocr_res["engine"],
            "message": f"Bill parsed via {ocr_res['engine']}. Please review and confirm numbers before updating live dashboard.",
            "extracted": extracted,
            "requires_confirmation": True,
            "confirmation_fields": {
                "total_kwh": extracted.get("total_kwh"),
                "total_amount_inr": extracted.get("total_amount_inr"),
                "power_factor": extracted.get("power_factor"),
                "max_demand_kva": extracted.get("max_demand_kva"),
                "discom": extracted.get("discom", "DISCOM"),
            },
            "data_tier": 1,
            "active_state": {
                "total_kwh": active_plant.total_kwh,
                "total_bill_inr": active_plant.total_bill_inr,
                "power_factor": active_plant.avg_pf,
                "peak_kw": active_plant.peak_kw,
            }
        }

    return {
        "status": "demo_fallback",
        "mode": "demo_values_used",
        "file": file.filename,
        "size_kb": round(len(content) / 1024, 1),
        "ocr_engine": ocr_res.get("engine", "Generic Parser"),
        "message": "Bill file received but DISCOM metrics could not be extracted — demo baseline values retained.",
        "extracted": {
            "month": "Sep 2026",
            "total_kwh": SEP_TOTAL_KWH,
            "total_kvah": SEP_TOTAL_KVAH,
            "max_demand_kva": SEP_MAX_DEMAND_KVA,
            "power_factor": SEP_AVG_PF,
            "tod_peak_kwh": SEP_TOD_PEAK_KWH,
            "tod_offpeak_kwh": SEP_TOD_OFFPEAK_KWH,
            "total_amount_inr": SEP_TOTAL_AMOUNT_INR,
            "pf_penalty_inr": SEP_PF_PENALTY_INR,
        },
        "data_tier": 1,
    }


@router.post("/confirm-bill")
async def confirm_bill(payload: dict):
    """
    User verification and confirmation endpoint for bill OCR metrics.
    Allows factory operators to review and confirm or correct extracted values.
    Validates updated values before committing to active plant state.
    """
    extracted = {
        "total_kwh": payload.get("total_kwh"),
        "total_amount_inr": payload.get("total_amount_inr"),
        "power_factor": payload.get("power_factor"),
        "max_demand_kva": payload.get("max_demand_kva"),
        "discom": payload.get("discom", "DISCOM"),
    }
    extracted = {k: v for k, v in extracted.items() if v is not None}
    is_valid, reason = validate_bill_telemetry(extracted)
    if not is_valid:
        return {
            "status": "demo_fallback",
            "validation_failed": True,
            "message": f"Sanity check failed: {reason}",
            "error": reason,
        }

    active_plant.ingest_bill(extracted, payload.get("filename", "user_verified_bill"))
    return {
        "status": "confirmed",
        "message": "✅ Bill metrics successfully confirmed! Live dashboard updated.",
        "active_state": {
            "total_kwh": active_plant.total_kwh,
            "total_bill_inr": active_plant.total_bill_inr,
            "power_factor": active_plant.avg_pf,
            "peak_kw": active_plant.peak_kw,
        }
    }



@router.post("/upload-meter-data")
async def upload_meter_data(file: UploadFile = File(...), plant_id: str = Form("1")):
    """
    Interval meter data upload.
    If valid CSV is uploaded, parses rows, calculates actual total_kwh and peak_kw,
    and updates the active analytics state.
    If random file or non-CSV, gracefully falls back to demo values with clear labeling.
    """
    content = await file.read()
    result = active_plant.ingest_csv(content, file.filename)

    if result.get("success"):
        return {
            "status": "processed",
            "mode": "data_parsed",
            "file": file.filename,
            "rows_detected": result["rows"],
            "total_kwh": result["total_kwh"],
            "peak_kw": result["peak_kw"],
            "avg_pf": result["avg_pf"],
            "specific_energy": result["specific_energy"],
            "data_tier": 2,
            "message": result["message"],
        }

    return {
        "status": "demo_fallback",
        "mode": "demo_values_used",
        "file": file.filename,
        "reason": result.get("reason", "Could not parse interval data columns"),
        "message": "File received but not recognized as interval CSV — demo baseline values retained.",
        "total_kwh": SEP_TOTAL_KWH,
        "data_tier": 2,
    }


@router.post("/upload-production")
async def upload_production(file: UploadFile = File(...), plant_id: str = Form("1")):
    content = await file.read()
    return {
        "status": "demo_fallback",
        "mode": "demo_values_used",
        "file": file.filename,
        "days_detected": 30,
        "total_production_kg": 12_580,
        "message": "Production log received (demo baseline applied for benchmark).",
    }


@router.post("/upload-equipment")
async def upload_equipment(file: UploadFile = File(...), plant_id: str = Form("1")):
    return {
        "status": "demo_fallback",
        "mode": "demo_values_used",
        "file": file.filename,
        "machines_detected": 5,
        "total_installed_kw": 355,
        "message": "Equipment register received (standard 5-machine profile active).",
    }


@router.post("/load-demo")
async def load_demo(plant_id: str = "1"):
    active_plant.reset_to_demo()
    return {
        "status": "success",
        "mode": "demo_loaded",
        "plant": "Rajkot Precision Foundry Pvt. Ltd.",
        "data_loaded": {
            "monthly_bill": True,
            "interval_data_15min": True,
            "production_log": True,
            "equipment_register": True,
        },
        "total_kwh": SEP_TOTAL_KWH,
        "period": "Sep 2026",
        "message": "✅ Rajkot Foundry demo dataset active (48,240 kWh baseline).",
    }
