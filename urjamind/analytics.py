from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .data_loader import load_sample_data


def _numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        raise ValueError(f"Required column '{column}' is missing.")

    values = pd.to_numeric(df[column], errors="coerce")
    if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"Column '{column}' must contain only finite numeric values.")
    if column in {"total_kwh", "total_kw", "production_units", "tariff_rate_rs", "idle_kw"} and (values < 0).any():
        raise ValueError(f"Column '{column}' must contain non-negative values.")
    if column == "power_factor" and ((values < 0) | (values > 1)).any():
        raise ValueError("Column 'power_factor' must contain values between 0 and 1.")
    return values


def get_energy_summary(df: pd.DataFrame | None = None) -> Dict[str, float | str]:
    df = df if df is not None else load_sample_data()
    if df.empty:
        raise ValueError("No data available for energy summary.")

    total_kwh = float(_numeric_column(df, "total_kwh").sum())
    total_kw = _numeric_column(df, "total_kw")
    production_units = float(_numeric_column(df, "production_units").sum())
    specific_energy = total_kwh / production_units if production_units else 0.0
    tariff_rates = _numeric_column(df, "tariff_rate_rs")
    bill_cost_rs = float((_numeric_column(df, "total_kwh") * tariff_rates).sum())

    return {
        "total_energy_kwh": round(total_kwh, 2),
        "average_load_kw": round(float(total_kw.mean()), 2),
        "peak_load_kw": round(float(total_kw.max()), 2),
        "production_units": round(production_units, 2),
        "specific_energy_kwh_per_unit": round(specific_energy, 4),
        "estimated_bill_cost_rs": round(bill_cost_rs, 2),
    }


def detect_anomalies(df: pd.DataFrame | None = None) -> List[Dict[str, object]]:
    df = df if df is not None else load_sample_data()
    anomalies: List[Dict[str, object]] = []

    if "power_factor" in df.columns:
        power_factor = _numeric_column(df, "power_factor")
        poor_pf = df[power_factor < 0.9]
        if not poor_pf.empty:
            affected_energy = _numeric_column(poor_pf, "total_kwh")
            affected_tariff = _numeric_column(poor_pf, "tariff_rate_rs")
            anomalies.append(
                {
                    "type": "power_factor",
                    "severity": "medium",
                    "detail": "Power factor is below 0.90 for part of the observed period.",
                    "impact_rs": round(float((affected_tariff * affected_energy).sum() * 0.08), 2),
                }
            )

    if "idle_kw" in df.columns:
        total_kw = _numeric_column(df, "total_kw")
        idle_kw = _numeric_column(df, "idle_kw")
        idle_rows = df[idle_kw > 0.2 * float(total_kw.max())]
        if not idle_rows.empty:
            idle_load = _numeric_column(idle_rows, "idle_kw")
            anomalies.append(
                {
                    "type": "idle_load",
                    "severity": "high",
                    "detail": "Idle machinery appears to be drawing a significant share of the plant load.",
                    "impact_rs": round(float(idle_load.sum() * 0.12), 2),
                }
            )

    if "total_kw" in df.columns and "shift" in df.columns:
        shift_load = _numeric_column(df, "total_kw")
        shift_summary = shift_load.groupby(df["shift"]).mean()
        worst_shift = shift_summary.idxmax()
        worst_avg = float(shift_summary.max())
        if worst_avg > 0:
            anomalies.append(
                {
                    "type": "shift_inefficiency",
                    "severity": "medium",
                    "detail": f"Shift {worst_shift} has the highest average load and may be the most energy-intensive period.",
                    "impact_rs": round(worst_avg * 12 * 0.18, 2),
                }
            )

    return anomalies


def generate_schedule(df: pd.DataFrame | None = None) -> List[Dict[str, object]]:
    df = df if df is not None else load_sample_data()
    if df.empty:
        raise ValueError("No data available to generate a schedule.")

    shift_names = ("A", "B", "C")
    shift_energy = _numeric_column(df, "total_kwh")
    tariffs = _numeric_column(df, "tariff_rate_rs")
    shift_tariffs: dict[str, float] = {}
    shift_energies: dict[str, float] = {}

    if "shift" not in df.columns:
        raise ValueError("Required column 'shift' is missing.")
    for shift in shift_names:
        rows = df["shift"] == shift
        energy = float(shift_energy[rows].sum())
        if energy > 0:
            shift_tariffs[shift] = float((shift_energy[rows] * tariffs[rows]).sum() / energy)
        shift_energies[shift] = energy

    if not shift_tariffs:
        return [
            {
                "shift": shift,
                "recommended_action": "no observed data; collect shift-level energy and tariff data",
                "average_load_kw": 0.0,
                "estimated_savings_rs": 0.0,
            }
            for shift in shift_names
        ]

    lowest_tariff = min(shift_tariffs.values())
    shift_load = _numeric_column(df, "total_kw")
    schedule = []
    for shift in ["A", "B", "C"]:
        rows = df["shift"] == shift
        avg_load = float(shift_load[rows].mean()) if rows.any() else 0.0
        tariff = shift_tariffs.get(shift)
        if tariff is None:
            action = "collect more data for this shift before scheduling changes"
            savings = 0.0
            savings_basis = "No observed energy and tariff data for this shift."
        elif tariff > lowest_tariff:
            action = "consider moving flexible jobs to a lower-tariff shift"
            savings = shift_energies[shift] * (tariff - lowest_tariff)
            savings_basis = (
                "Upper-bound estimate assumes all observed shift energy can move "
                "to the lowest-tariff shift without changing total consumption."
            )
        else:
            action = "retain flexible jobs in this lowest-tariff shift"
            savings = 0.0
            savings_basis = "No lower-tariff shift was observed."
        schedule.append(
            {
                "shift": shift,
                "recommended_action": action,
                "average_load_kw": round(avg_load, 2),
                "estimated_savings_rs": round(savings, 2),
                "savings_basis": savings_basis,
            }
        )
    return schedule


def compute_carbon(df: pd.DataFrame | None = None, grid_emission_factor_kg_per_kwh: float = 0.716) -> Dict[str, float]:
    """
    Compute Scope 2 GHG emissions.
    Default: 0.716 kgCO₂/kWh — CEA India 2023-24, Western Regional Grid (Gujarat).
    """
    df = df if df is not None else load_sample_data()
    if df.empty:
        raise ValueError("No data available to calculate carbon emissions.")
    if not np.isfinite(grid_emission_factor_kg_per_kwh) or grid_emission_factor_kg_per_kwh < 0:
        raise ValueError("Grid emission factor must be a finite, non-negative value.")
    total_kwh = float(_numeric_column(df, "total_kwh").sum())
    scope2_kg = total_kwh * grid_emission_factor_kg_per_kwh
    scope2_tco2e = scope2_kg / 1000.0
    return {
        "total_energy_kwh": round(total_kwh, 2),
        "scope2_kgco2e": round(scope2_kg, 2),
        "scope2_tco2e": round(scope2_tco2e, 4),
    }
