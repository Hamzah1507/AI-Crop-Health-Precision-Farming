"""
Soil analysis scoring tests (pure unit tests, no database or network).

Run from the backend folder:  python -m unittest tests.test_soil_service -v
"""
import itertools
import unittest

from app.services.soil_service import soil_analysis_service as soil

LOW = dict(ph=5, nitrogen=10, phosphorus=10, potassium=15, moisture=25)           # every value below its range
MODERATE = dict(ph=5.5, nitrogen=15, phosphorus=20, potassium=18, moisture=25)    # mixed: 4 of 5 slightly off
SUITABLE = dict(ph=6.5, nitrogen=35, phosphorus=25, potassium=30, moisture=50)    # all within range


class SoilScoreScenarios(unittest.TestCase):
    def test_low_soil_is_poor_not_excellent(self):
        """Regression: this input used to score 80/100 'Excellent' while every value was flagged Low."""
        result = soil.analyze(**LOW)
        self.assertLess(result["soil_health_score"], 45)
        self.assertIn(result["soil_health_status"], ("Poor", "Critical"))
        statuses = {k: v["status"] for k, v in result["detailed_analysis"].items()}
        self.assertEqual(statuses["ph"], "Very Acidic")
        self.assertTrue(all(s != "Optimal" for s in statuses.values()), statuses)
        self.assertIn("5 of 5", result["health_summary"])

    def test_moderate_soil_is_moderate(self):
        result = soil.analyze(**MODERATE)
        self.assertEqual(result["soil_health_status"], "Moderate")
        self.assertTrue(45 <= result["soil_health_score"] < 65, result["soil_health_score"])

    def test_suitable_soil_is_excellent(self):
        result = soil.analyze(**SUITABLE)
        self.assertEqual(result["soil_health_score"], 100.0)
        self.assertEqual(result["soil_health_status"], "Excellent")
        self.assertIn("within their ideal ranges", result["health_summary"])
        self.assertTrue(all(v["status"] == "Optimal" for v in result["detailed_analysis"].values()))

    def test_single_flagged_value_cannot_be_excellent(self):
        result = soil.analyze(**{**SUITABLE, "ph": 5.0})
        self.assertNotEqual(result["soil_health_status"], "Excellent")
        self.assertLessEqual(result["soil_health_score"], 84)

    def test_no_measurements_is_unknown(self):
        result = soil.analyze()
        self.assertEqual(result["soil_health_status"], "Unknown")

    def test_range_boundaries_are_inclusive(self):
        for kw in (dict(ph=6.0), dict(ph=7.5), dict(nitrogen=20), dict(nitrogen=50), dict(phosphorus=15),
                   dict(phosphorus=40), dict(potassium=20), dict(potassium=45), dict(moisture=30), dict(moisture=70)):
            with self.subTest(**kw):
                result = soil.analyze(**kw)
                self.assertEqual(result["soil_health_score"], 100.0)
                self.assertEqual(result["soil_health_status"], "Excellent")

    def test_worse_values_never_score_higher(self):
        scores = [soil.analyze(**{**SUITABLE, "ph": p})["soil_health_score"] for p in (6.0, 5.8, 5.5, 5.0, 4.5)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_data_sufficiency_flags(self):
        """Task 4 Audit: Incomplete measurements (< 3 params) must be marked insufficient."""
        single = soil.analyze(ph=7.0)
        self.assertFalse(single["is_sufficient"])
        self.assertEqual(single["measured_parameters_count"], 1)
        self.assertIn("Preliminary assessment", single["health_summary"])
        self.assertIn("At least 3 parameters are required", single["health_summary"])

        double = soil.analyze(ph=7.0, nitrogen=35.0)
        self.assertFalse(double["is_sufficient"])
        self.assertEqual(double["measured_parameters_count"], 2)

        triple = soil.analyze(ph=7.0, nitrogen=35.0, phosphorus=25.0)
        self.assertTrue(triple["is_sufficient"])
        self.assertEqual(triple["measured_parameters_count"], 3)

        full = soil.analyze(**SUITABLE)
        self.assertTrue(full["is_sufficient"])
        self.assertEqual(full["measured_parameters_count"], 5)

    def test_invalid_and_out_of_bounds_measurements(self):
        """Task 4 Audit: Negative or physically impossible measurements must raise ValueError."""
        with self.assertRaises(ValueError):
            soil.analyze(ph=-1.0, nitrogen=30, phosphorus=20, potassium=30, moisture=50)

        with self.assertRaises(ValueError):
            soil.analyze(ph=15.0, nitrogen=30, phosphorus=20, potassium=30, moisture=50)

        with self.assertRaises(ValueError):
            soil.analyze(ph=7.0, nitrogen=-10, phosphorus=20, potassium=30, moisture=50)

        with self.assertRaises(ValueError):
            soil.analyze(ph=7.0, nitrogen=30, phosphorus=20, potassium=30, moisture=110.0)

    def test_existing_app_db_user_records_are_justified_at_100(self):
        """Task 4 Audit: Farmer 7's two historical records in app.db are 100/100 by arithmetic."""
        # Row 1: pH 7.0, N 30.0, P 29.0, K 25.0, Moisture 45.0
        rec1 = soil.analyze(ph=7.0, nitrogen=30.0, phosphorus=29.0, potassium=25.0, moisture=45.0)
        self.assertEqual(rec1["soil_health_score"], 100.0)
        self.assertEqual(rec1["soil_health_status"], "Excellent")
        self.assertTrue(rec1["is_sufficient"])
        self.assertEqual(rec1["measured_parameters_count"], 5)

        # Row 2: pH 7.0, N 23.0, P 21.0, K 29.0, Moisture 45.0
        rec2 = soil.analyze(ph=7.0, nitrogen=23.0, phosphorus=21.0, potassium=29.0, moisture=45.0)
        self.assertEqual(rec2["soil_health_score"], 100.0)
        self.assertEqual(rec2["soil_health_status"], "Excellent")
        self.assertTrue(rec2["is_sufficient"])
        self.assertEqual(rec2["measured_parameters_count"], 5)


class SoilScoreConsistency(unittest.TestCase):
    def test_score_and_status_always_agree_with_parameter_flags(self):
        """Across a grid of inputs, the headline result must match the per-parameter statuses."""
        grid = itertools.product(
            (4.0, 5.0, 5.9, 6.0, 6.5, 7.5, 7.6, 8.5),    # pH
            (0, 10, 19, 20, 35, 50, 51),                  # nitrogen
            (0, 14, 15, 25, 40, 41),                      # phosphorus
            (0, 19, 20, 30, 45, 46),                      # potassium
            (10, 25, 29, 30, 50, 70, 71, 90),             # moisture
        )
        checked = 0
        for ph, n, p, k, m in grid:
            score, status, _ = soil._calculate_health_score(ph, n, p, k, m)
            detailed = soil._detailed_analysis(ph, n, p, k, m)
            flagged = sum(1 for v in detailed.values() if v["status"] != "Optimal")
            if flagged == 0:
                ok = status == "Excellent"
            elif flagged == 1:
                ok = status != "Excellent"
            elif flagged == 2:
                ok = score <= 74
            else:
                ok = status in ("Moderate", "Poor", "Critical")
            self.assertTrue(ok, f"inconsistent: ph={ph} n={n} p={p} k={k} m={m} -> {score:.1f} {status}, {flagged} flagged")
            self.assertTrue(0 <= score <= 100)
            checked += 1
        self.assertEqual(checked, 8 * 7 * 6 * 6 * 8)


if __name__ == "__main__":
    unittest.main()
