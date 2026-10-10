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
            "plant_name": extracted.get("consumer_name", active_plant.plant_name),
            "message": f"Bill parsed via {ocr_res['engine']}. Please review and confirm numbers before updating live dashboard.",
            "extracted": extracted,
            "requires_confirmation": True,
            "confirmation_fields": {
                "total_kwh": extracted.get("total_kwh"),
                "total_amount_inr": extracted.get("total_amount_inr"),
                "power_factor": extracted.get("power_factor"),
                "max_demand_kva": extracted.get("max_demand_kva"),
                "discom": extracted.get("discom", "DISCOM"),
                "consumer_name": extracted.get("consumer_name", active_plant.plant_name),
            },
            "data_tier": 1,
            "active_state": {
                "plant": active_plant.plant_name,
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
        "consumer_name": payload.get("consumer_name"),
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
        "message": f"✅ Bill metrics confirmed for '{active_plant.plant_name}'! Live dashboard updated.",
        "active_state": {
            "plant": active_plant.plant_name,
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
    """
    content = await file.read()
    result = active_plant.ingest_csv(content, file.filename)

    if result.get("success"):
        return {
            "status": "processed",
            "mode": result.get("mode", "data_parsed"),
            "file": file.filename,
            "file_status": result.get("file_status", "Parsed"),
            "rows_detected": result.get("rows"),
            "total_kwh": result.get("total_kwh") or result.get("monthly_kwh_estimated"),
            "peak_kw": result.get("peak_kw"),
            "avg_pf": result.get("avg_pf"),
            "specific_energy": result.get("specific_energy"),
            "warning": result.get("warning"),
            "data_tier": 2,
            "message": result["message"],
        }

    return {
        "status": "demo_fallback",
        "mode": "demo_values_used",
        "file": file.filename,
        "reason": result.get("reason", "Could not parse interval data columns"),
        "message": "File received but not recognized as interval data — demo baseline values retained.",
        "total_kwh": SEP_TOTAL_KWH,
        "data_tier": 2,
    }


@router.post("/upload-production")
async def upload_production(file: UploadFile = File(...), plant_id: str = Form("1")):
    """Parse production log and recalculate Specific Energy Consumption."""
    content = await file.read()
    result = active_plant.ingest_production(content, file.filename)
    return result


@router.post("/upload-equipment")
async def upload_equipment(file: UploadFile = File(...), plant_id: str = Form("1")):
    """Parse equipment register (PDF, CSV, Excel, Text) and dynamically update machine inventory."""
    content = await file.read()
    result = active_plant.ingest_equipment(content, file.filename)
    return result


@router.post("/load-demo")
@router.post("/reset")
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
        "message": "✅ Sample plant baseline loaded (48,240 kWh).",
    }


@router.post("/load-abc-dummy")
async def load_abc_dummy():
    """Instantly pre-loads the 4 dummy files for ABC Manufacturing Pvt. Ltd."""
    active_plant.source = "uploaded_bill_ocr"
    active_plant.filename = "01_Electricity_Bill_Dummy.pdf"
    active_plant.plant_name = "ABC Manufacturing Pvt. Ltd."
    active_plant.billing_period = "Sep 2026"
    active_plant.total_kwh = 18450.0
    active_plant.total_bill_inr = 176450.0
    active_plant.avg_pf = 0.94
    active_plant.pf_penalty_inr = 0.0
    active_plant.max_demand_kva = 285.0
    active_plant.spot_load_readings = {"observed_peak_kva": 253.3}
    active_plant.production_kg = 1145.0
    active_plant.specific_energy = 1.24
    active_plant.equipment_list = [
        {"name": "CNC Production Machine #1", "total_kw": 22.0, "qty": 1, "duty_factor": 0.65},
        {"name": "CNC Production Machine #2", "total_kw": 22.0, "qty": 1, "duty_factor": 0.60},
        {"name": "CNC Heavy Roughing #3", "total_kw": 30.0, "qty": 1, "duty_factor": 0.50},
        {"name": "CNC Finishing Machine #4", "total_kw": 18.0, "qty": 1, "duty_factor": 0.45},
    ]
    active_plant.recalculate_machine_energy()
    return {
        "status": "success",
        "mode": "abc_dummy_loaded",
        "plant": "ABC Manufacturing Pvt. Ltd.",
        "total_kwh": 18450.0,
        "max_demand_kva": 285.0,
        "observed_peak_kva": 253.3,
        "message": "✅ ABC Manufacturing Pvt. Ltd. dummy telemetry loaded.",
    }


@router.get("/file-status")
async def get_file_status():
    """Returns processing status for each data source category and any interval mismatch notices."""
    return {
        "file_statuses": active_plant.file_statuses,
        "interval_warning": active_plant.interval_warning,
        "spot_load_readings": active_plant.spot_load_readings,
        "production_extrapolation": active_plant.production_extrapolation,
        "has_real_baseline": active_plant.has_real_baseline,
    }


@router.get("/template/interval-csv")
async def get_interval_template():
    """Generates and downloads a standardized 96-slot 15-minute interval data CSV template."""
    from fastapi.responses import Response
    lines = ["timestamp,load_kw,power_factor"]
    import datetime
    base_date = datetime.date.today()
    for slot in range(96):
        total_mins = slot * 15
        h = total_mins // 60
        m = total_mins % 60
        ts = f"{base_date} {h:02d}:{m:02d}:00"
        # Sample plausible load
        sample_kw = 45.0 if 8 <= h < 20 else 8.5
        lines.append(f"{ts},{sample_kw:.1f},0.92")
    csv_content = "\n".join(lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=urjamind_interval_template_96slot.csv"}
    )


