import unittest

import pandas as pd

from urjamind.analytics import (
    compute_carbon,
    detect_anomalies,
    generate_schedule,
    get_energy_summary,
)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "total_kwh": [10.0, 20.0, 30.0],
                "total_kw": [10.0, 20.0, 30.0],
                "production_units": [2.0, 4.0, 6.0],
                "tariff_rate_rs": [10.0, 5.0, 7.0],
                "power_factor": [0.85, 0.95, 0.88],
                "shift": ["A", "B", "C"],
                "idle_kw": [1.0, 2.0, 3.0],
            }
        )

    def test_summary_calculates_tariff_cost_per_interval(self):
        summary = get_energy_summary(self.data)

        self.assertEqual(summary["total_energy_kwh"], 60.0)
        self.assertEqual(summary["estimated_bill_cost_rs"], 410.0)
        self.assertEqual(summary["specific_energy_kwh_per_unit"], 5.0)

    def test_schedule_uses_observed_tariffs_and_discloses_estimate_basis(self):
        schedule = generate_schedule(self.data)

        self.assertEqual([item["estimated_savings_rs"] for item in schedule], [50.0, 0.0, 60.0])
        self.assertIn("lowest-tariff shift", schedule[1]["recommended_action"])
        self.assertIn("Upper-bound", schedule[0]["savings_basis"])

    def test_carbon_uses_configured_emission_factor(self):
        carbon = compute_carbon(self.data, grid_emission_factor_kg_per_kwh=0.5)

        self.assertEqual(carbon["scope2_kgco2e"], 30.0)
        self.assertEqual(carbon["scope2_tco2e"], 0.03)

    def test_anomaly_cost_estimate_uses_interval_tariffs(self):
        anomalies = detect_anomalies(self.data)
        power_factor = next(item for item in anomalies if item["type"] == "power_factor")

        self.assertEqual(power_factor["impact_rs"], 24.8)

    def test_summary_rejects_non_numeric_measurements(self):
        invalid_data = self.data.copy()
        invalid_data.loc[0, "total_kwh"] = "not-a-number"

        with self.assertRaisesRegex(ValueError, "total_kwh"):
            get_energy_summary(invalid_data)

    def test_carbon_rejects_negative_emission_factor(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            compute_carbon(self.data, grid_emission_factor_kg_per_kwh=-0.1)


if __name__ == "__main__":
    unittest.main()
