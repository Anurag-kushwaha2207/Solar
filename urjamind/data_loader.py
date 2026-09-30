from io import StringIO
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_factory_data.csv"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

    rename_map = {
        "totalenergykwh": "total_kwh",
        "totalkwh": "total_kwh",
        "totalloadkw": "total_kw",
        "totalkw": "total_kw",
        "production": "production_units",
        "productionunits": "production_units",
        "unitproduced": "production_units",
        "tariff": "tariff_rate_rs",
        "tariffrate": "tariff_rate_rs",
        "tariffrate_rs": "tariff_rate_rs",
        "powerfactor": "power_factor",
        "pf": "power_factor",
        "idleloadkw": "idle_kw",
        "idlekw": "idle_kw",
    }
    df.rename(columns=rename_map, inplace=True)

    for col in ["total_kwh", "total_kw", "production_units", "tariff_rate_rs", "power_factor", "idle_kw"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    if "shift" in df.columns:
        df["shift"] = df["shift"].astype(str).str.upper()

    if "total_kwh" not in df.columns and "total_kw" in df.columns:
        df["total_kwh"] = df["total_kw"]

    if "tariff_rate_rs" not in df.columns:
        df["tariff_rate_rs"] = 8.5

    if "production_units" not in df.columns:
        df["production_units"] = 1.0

    if "power_factor" not in df.columns:
        df["power_factor"] = 0.9

    if "idle_kw" not in df.columns:
        df["idle_kw"] = 0.0

    return df


def load_csv_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    text = file_bytes.decode("utf-8-sig")
    df = pd.read_csv(StringIO(text))
    return normalize_columns(df)


def load_sample_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Sample dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    return normalize_columns(df)
