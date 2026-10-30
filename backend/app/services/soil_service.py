"""
Soil Analysis & Recommendation Service

Provides rule-based intelligent recommendations for:
- Soil health assessment
- Fertilizer recommendations
- Suitable crop recommendations
- Irrigation recommendations
- Weather-based farming alerts

Architecture: Modular design so it can be replaced with an ML model later.
"""

from typing import Optional, Dict, Any, List


class SoilAnalysisService:
    """Rule-based soil analysis and recommendation engine."""

    # Optimal ranges for soil parameters
    OPTIMAL_RANGES = {
        "ph": {"min": 6.0, "max": 7.5, "ideal": 6.5},
        "nitrogen": {"min": 20, "max": 50, "ideal": 35, "unit": "kg/ha"},
        "phosphorus": {"min": 15, "max": 40, "ideal": 25, "unit": "kg/ha"},
        "potassium": {"min": 20, "max": 45, "ideal": 30, "unit": "kg/ha"},
        "moisture": {"min": 30, "max": 70, "ideal": 50, "unit": "%"},
    }

    # Physical valid bounds to prevent invalid, corrupt, or negative measurements
    VALID_BOUNDS = {
        "ph": (0.0, 14.0),
        "nitrogen": (0.0, 1000.0),
        "phosphorus": (0.0, 1000.0),
        "potassium": (0.0, 1000.0),
        "moisture": (0.0, 100.0),
    }

    # Crop suitability based on soil conditions
    CROP_SUITABILITY = {
        "rice": {"ph_range": (5.5, 7.0), "moisture_min": 60, "n_need": "high"},
        "wheat": {"ph_range": (6.0, 7.5), "moisture_min": 35, "n_need": "medium"},
        "corn": {"ph_range": (5.8, 7.0), "moisture_min": 40, "n_need": "high"},
        "tomato": {"ph_range": (6.0, 6.8), "moisture_min": 40, "n_need": "medium"},
        "potato": {"ph_range": (5.0, 6.5), "moisture_min": 45, "n_need": "medium"},
        "soybean": {"ph_range": (6.0, 7.0), "moisture_min": 35, "n_need": "low"},
        "cotton": {"ph_range": (6.0, 7.5), "moisture_min": 30, "n_need": "medium"},
        "sugarcane": {"ph_range": (6.0, 7.5), "moisture_min": 50, "n_need": "high"},
        "groundnut": {"ph_range": (5.5, 7.0), "moisture_min": 30, "n_need": "low"},
        "millet": {"ph_range": (5.5, 7.5), "moisture_min": 20, "n_need": "low"},
    }

    def validate_measurements(
        self,
        ph: Optional[float] = None,
        nitrogen: Optional[float] = None,
        phosphorus: Optional[float] = None,
        potassium: Optional[float] = None,
        moisture: Optional[float] = None,
    ) -> None:
        """Validate that all provided measurements fall within physically possible bounds."""
        checks = {"ph": ph, "nitrogen": nitrogen, "phosphorus": phosphorus, "potassium": potassium, "moisture": moisture}
        for key, val in checks.items():
            if val is not None and key in self.VALID_BOUNDS:
                low, high = self.VALID_BOUNDS[key]
                if val < low or val > high:
                    raise ValueError(f"Soil parameter '{key}' value {val} is outside valid physical bounds ({low} to {high}).")

    def analyze(
        self,
        ph: Optional[float] = None,
        nitrogen: Optional[float] = None,
        phosphorus: Optional[float] = None,
        potassium: Optional[float] = None,
        moisture: Optional[float] = None,
        crop_name: Optional[str] = None,
        location: Optional[str] = None,
        weather: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Perform complete soil analysis and generate recommendations."""
        # Validate sanity bounds
        self.validate_measurements(ph=ph, nitrogen=nitrogen, phosphorus=phosphorus, potassium=potassium, moisture=moisture)

        # Count provided parameters and evaluate sufficiency
        raw_measurements = {"ph": ph, "nitrogen": nitrogen, "phosphorus": phosphorus, "potassium": potassium, "moisture": moisture}
        provided_count = sum(1 for v in raw_measurements.values() if v is not None)
        is_sufficient = provided_count >= 3

        # Calculate soil health score
        score, status, health_summary = self._calculate_health_score(ph, nitrogen, phosphorus, potassium, moisture)

        # Generate detailed analysis
        detailed = self._detailed_analysis(ph, nitrogen, phosphorus, potassium, moisture)

        # Generate fertilizer recommendations
        fertilizer_recs = self._fertilizer_recommendations(nitrogen, phosphorus, potassium, ph)

        # Generate crop recommendations
        crop_recs = self._crop_recommendations(ph, nitrogen, phosphorus, potassium, moisture)

        # Generate irrigation recommendation
        irrigation_rec = self._irrigation_recommendation(moisture, weather)

        # Generate weather-based alerts
        weather_alerts = self._weather_alerts(weather, crop_name)

        return {
            "soil_health_status": status,
            "soil_health_score": round(score, 1),
            "health_summary": health_summary,
            "is_sufficient": is_sufficient,
            "measured_parameters_count": provided_count,
            "fertilizer_recommendations": fertilizer_recs,
            "crop_recommendations": crop_recs,
            "irrigation_recommendation": irrigation_rec,
            "weather_alerts": weather_alerts,
            "detailed_analysis": detailed,
        }

    # Overall status bands (score is 0-100)
    STATUS_BANDS = [(85, "Excellent"), (65, "Good"), (45, "Moderate"), (25, "Poor"), (0, "Critical")]

    # The more parameters fall outside their ideal range, the lower the best possible score.
    # This keeps the headline result consistent with the per-parameter statuses.
    SCORE_CAP_BY_OUT_OF_RANGE = {0: 100.0, 1: 84.0, 2: 74.0}   # 3 or more -> 64.0 (at best "Moderate")
    SCORE_CAP_MANY_OUT_OF_RANGE = 64.0

    def _parameter_score(self, key: str, value: float) -> float:
        """
        Score one measurement from 0-100 against its ideal range.

        Inside the ideal range -> 100. Outside it, the score is at most 70 and falls
        in proportion to how far away the value is (relative to the width of the ideal
        range), so a clearly flagged parameter can never look "excellent".
        """
        opt = self.OPTIMAL_RANGES[key]
        if opt["min"] <= value <= opt["max"]:
            return 100.0
        distance = (opt["min"] - value) if value < opt["min"] else (value - opt["max"])
        relative = distance / (opt["max"] - opt["min"])
        return max(0.0, 70.0 - 100.0 * relative)

    def _calculate_health_score(self, ph, nitrogen, phosphorus, potassium, moisture) -> tuple:
        """
        Calculate the overall soil health score (0-100), its status and a short summary.

        Rule-based: the average of the per-parameter scores, capped according to how many
        parameters are outside their ideal range (the same ranges that produce the
        Optimal/Low/High labels in the detailed analysis).
        """
        measurements = {"ph": ph, "nitrogen": nitrogen, "phosphorus": phosphorus,
                        "potassium": potassium, "moisture": moisture}
        provided = {k: v for k, v in measurements.items() if v is not None}
        if not provided:
            return 50.0, "Unknown", "No measurements provided."

        scores = {k: self._parameter_score(k, v) for k, v in provided.items()}
        out_of_range = [k for k, s in scores.items() if s < 100.0]

        score = sum(scores.values()) / len(scores)
        cap = self.SCORE_CAP_BY_OUT_OF_RANGE.get(len(out_of_range), self.SCORE_CAP_MANY_OUT_OF_RANGE)
        score = min(score, cap)

        status = next(label for threshold, label in self.STATUS_BANDS if score >= threshold)

        if len(provided) < 3:
            names = ", ".join("pH" if k == "ph" else k for k in provided.keys())
            summary = (f"Preliminary assessment based on {len(provided)} of 5 standard soil parameters ({names}). "
                       "At least 3 parameters are required for a reliable Soil Health Index; missing parameters are not assumed to be optimal.")
        elif not out_of_range:
            if len(provided) == 5:
                summary = "All 5 measurements are within their ideal ranges."
            else:
                missing_keys = [k for k in self.OPTIMAL_RANGES if k not in provided]
                summary = f"All {len(provided)} provided measurements are within their ideal ranges (unmeasured: {', '.join(missing_keys)})."
        else:
            names = ", ".join("pH" if k == "ph" else k for k in out_of_range)
            summary = (f"{len(out_of_range)} of {len(provided)} measurements are outside their ideal range ({names}). "
                       "The score averages how close each measurement is to its range, capped by how many are off.")
        return score, status, summary

    def _detailed_analysis(self, ph, nitrogen, phosphorus, potassium, moisture) -> Dict:
        """Generate detailed analysis for each parameter."""
        analysis = {}

        if ph is not None:
            if ph < 5.5:
                analysis["ph"] = {"value": ph, "status": "Very Acidic", "action": "Apply agricultural lime to raise pH"}
            elif ph < 6.0:
                analysis["ph"] = {"value": ph, "status": "Acidic", "action": "Consider applying lime"}
            elif ph <= 7.5:
                analysis["ph"] = {"value": ph, "status": "Optimal", "action": "pH is in the ideal range"}
            elif ph <= 8.0:
                analysis["ph"] = {"value": ph, "status": "Alkaline", "action": "Consider applying sulfur or organic matter"}
            else:
                analysis["ph"] = {"value": ph, "status": "Very Alkaline", "action": "Apply sulfur or gypsum to lower pH"}

        if nitrogen is not None:
            if nitrogen < 20:
                analysis["nitrogen"] = {"value": nitrogen, "status": "Low", "action": "Apply nitrogen-rich fertilizer (Urea, Ammonium Nitrate)"}
            elif nitrogen <= 50:
                analysis["nitrogen"] = {"value": nitrogen, "status": "Optimal", "action": "Nitrogen levels are adequate"}
            else:
                analysis["nitrogen"] = {"value": nitrogen, "status": "High", "action": "Reduce nitrogen fertilization to avoid runoff"}

        if phosphorus is not None:
            if phosphorus < 15:
                analysis["phosphorus"] = {"value": phosphorus, "status": "Low", "action": "Apply phosphorus-rich fertilizer (DAP, SSP)"}
            elif phosphorus <= 40:
                analysis["phosphorus"] = {"value": phosphorus, "status": "Optimal", "action": "Phosphorus levels are adequate"}
            else:
                analysis["phosphorus"] = {"value": phosphorus, "status": "High", "action": "Reduce phosphorus application"}

        if potassium is not None:
            if potassium < 20:
                analysis["potassium"] = {"value": potassium, "status": "Low", "action": "Apply potassium-rich fertilizer (MOP, SOP)"}
            elif potassium <= 45:
                analysis["potassium"] = {"value": potassium, "status": "Optimal", "action": "Potassium levels are adequate"}
            else:
                analysis["potassium"] = {"value": potassium, "status": "High", "action": "Reduce potassium application"}

        if moisture is not None:
            if moisture < 20:
                analysis["moisture"] = {"value": moisture, "status": "Very Dry", "action": "Immediate irrigation required"}
            elif moisture < 30:
                analysis["moisture"] = {"value": moisture, "status": "Dry", "action": "Schedule irrigation soon"}
            elif moisture <= 70:
                analysis["moisture"] = {"value": moisture, "status": "Optimal", "action": "Moisture levels are adequate"}
            elif moisture <= 85:
                analysis["moisture"] = {"value": moisture, "status": "Wet", "action": "Reduce irrigation frequency"}
            else:
                analysis["moisture"] = {"value": moisture, "status": "Waterlogged", "action": "Improve drainage immediately"}

        return analysis

    def _fertilizer_recommendations(self, nitrogen, phosphorus, potassium, ph) -> List[Dict]:
        """Generate fertilizer recommendations based on NPK levels."""
        recs = []

        if nitrogen is not None and nitrogen < 20:
            recs.append({
                "fertilizer": "Urea (46-0-0)",
                "reason": f"Nitrogen level is low ({nitrogen} kg/ha). Recommended: 20-50 kg/ha",
                "priority": "high",
                "application": "Apply in split doses during crop growth stages"
            })
        if nitrogen is not None and nitrogen < 30:
            recs.append({
                "fertilizer": "Ammonium Sulphate (21-0-0-24S)",
                "reason": "Provides nitrogen along with sulfur for better nutrient uptake",
                "priority": "medium",
                "application": "Apply as basal dose or top dressing"
            })

        if phosphorus is not None and phosphorus < 15:
            recs.append({
                "fertilizer": "DAP (18-46-0)",
                "reason": f"Phosphorus level is low ({phosphorus} kg/ha). Recommended: 15-40 kg/ha",
                "priority": "high",
                "application": "Apply as basal dose before sowing"
            })

        if potassium is not None and potassium < 20:
            recs.append({
                "fertilizer": "Muriate of Potash (0-0-60)",
                "reason": f"Potassium level is low ({potassium} kg/ha). Recommended: 20-45 kg/ha",
                "priority": "high",
                "application": "Apply as basal dose or split application"
            })

        if ph is not None and ph < 5.5:
            recs.append({
                "fertilizer": "Agricultural Lime",
                "reason": f"Soil is very acidic (pH {ph}). Lime will help raise pH to optimal range",
                "priority": "high",
                "application": "Apply ahead of planting, following local soil-test guidance"
            })
        elif ph is not None and ph > 8.0:
            recs.append({
                "fertilizer": "Gypsum / Elemental Sulfur",
                "reason": f"Soil is very alkaline (pH {ph}). These amendments help lower pH",
                "priority": "high",
                "application": "Apply and incorporate into soil before planting"
            })

        if not recs:
            recs.append({
                "fertilizer": "Balanced NPK (10-10-10)",
                "reason": "Soil nutrient levels are generally adequate. Use balanced fertilizer for maintenance",
                "priority": "low",
                "application": "Apply according to crop requirements"
            })

        return recs

    def _crop_recommendations(self, ph, nitrogen, phosphorus, potassium, moisture) -> List[str]:
        """Recommend suitable crops based on soil conditions."""
        suitable = []

        for crop_name, requirements in self.CROP_SUITABILITY.items():
            score = 0
            checks = 0

            if ph is not None:
                checks += 1
                ph_min, ph_max = requirements["ph_range"]
                if ph_min <= ph <= ph_max:
                    score += 1

            if moisture is not None:
                checks += 1
                if moisture >= requirements["moisture_min"]:
                    score += 1

            if nitrogen is not None:
                checks += 1
                n_need = requirements["n_need"]
                if n_need == "low" and nitrogen >= 10:
                    score += 1
                elif n_need == "medium" and nitrogen >= 20:
                    score += 1
                elif n_need == "high" and nitrogen >= 30:
                    score += 1

            if checks > 0 and score / checks >= 0.6:
                suitable.append(crop_name.capitalize())

        if not suitable:
            suitable = ["Millet", "Sorghum", "Groundnut"]  # Hardy crops

        return suitable[:6]

    def _irrigation_recommendation(self, moisture, weather) -> Dict:
        """Generate irrigation recommendation."""
        if moisture is None:
            return {
                "status": "Unknown",
                "recommendation": "Enter soil moisture data for irrigation guidance",
                "schedule": "Not available",
                "priority": "medium"
            }

        rainfall = weather.get("rainfall", 0) if weather else 0
        temperature = weather.get("temperature", 25) if weather else 25

        if moisture < 20:
            return {
                "status": "Critical - Immediate Irrigation Needed",
                "recommendation": "Soil is very dry. Irrigate promptly (drip or sprinkler irrigation is water-efficient) and re-check soil moisture afterwards.",
                "schedule": "Irrigate now, then re-check moisture within a day or two before the next irrigation",
                "priority": "critical"
            }
        elif moisture < 30:
            return {
                "status": "Low Moisture - Irrigation Recommended",
                "recommendation": "Soil moisture is below the reference range. Plan irrigation soon, with an amount suited to your crop and soil type.",
                "schedule": "Irrigate within about a day, then re-check moisture before the next cycle",
                "priority": "high"
            }
        elif moisture <= 60:
            if rainfall > 5:
                return {
                    "status": "Adequate - Monitor",
                    "recommendation": f"Recent rainfall ({rainfall}mm) combined with current moisture ({moisture}%) is sufficient. Monitor for next 2-3 days.",
                    "schedule": "No irrigation needed for 3-5 days",
                    "priority": "low"
                }
            elif temperature > 35:
                return {
                    "status": "Adequate but Hot Weather",
                    "recommendation": f"Moisture is adequate but high temperature ({temperature}°C) may cause rapid evaporation. Consider light irrigation.",
                    "schedule": "Light, more frequent irrigation while it stays hot; re-check moisture regularly",
                    "priority": "medium"
                }
            return {
                "status": "Optimal",
                "recommendation": "Soil moisture is in the ideal range. Maintain current irrigation schedule.",
                "schedule": "Keep your normal irrigation routine and re-check moisture regularly",
                "priority": "low"
            }
        elif moisture <= 80:
            return {
                "status": "High Moisture - Reduce Irrigation",
                "recommendation": "Soil is wet. Skip the next irrigation cycle. Ensure proper drainage.",
                "schedule": "Skip next 1-2 irrigation cycles",
                "priority": "medium"
            }
        else:
            return {
                "status": "Waterlogged - Drainage Needed",
                "recommendation": "Soil is waterlogged. Stop irrigation. Improve drainage to prevent root rot.",
                "schedule": "No irrigation until moisture drops below 70%",
                "priority": "critical"
            }

    def _weather_alerts(self, weather: Optional[Dict], crop_name: Optional[str]) -> List[str]:
        """Generate weather-based farming alerts."""
        alerts = []

        if not weather:
            return ["No live weather data was used. Enter a valid location to include weather-based alerts."]

        temp = weather.get("temperature")
        humidity = weather.get("humidity")
        rainfall = weather.get("rainfall") or 0
        wind = weather.get("wind_speed") or 0

        if temp is not None:
            if temp > 40:
                alerts.append(f"🔴 Extreme heat alert ({temp}°C): Provide shade for sensitive crops. Increase irrigation frequency.")
            elif temp > 35:
                alerts.append(f"🟠 High temperature ({temp}°C): Monitor crops for heat stress. Consider mulching.")
            elif temp < 5:
                alerts.append(f"🔵 Frost risk ({temp}°C): Protect crops with covers. Delay transplanting.")
            elif temp < 10:
                alerts.append(f"🟡 Cold weather ({temp}°C): Monitor cold-sensitive crops. Avoid early morning irrigation.")

        if humidity is not None:
            if humidity > 85:
                alerts.append(f"🟠 High humidity ({humidity}%): Increased risk of fungal diseases. Apply preventive fungicide.")
            elif humidity < 30:
                alerts.append(f"🟡 Low humidity ({humidity}%): Increase irrigation to compensate for moisture loss.")

        if rainfall > 20:
            alerts.append(f"🔴 Heavy rainfall ({rainfall}mm): Risk of waterlogging and soil erosion. Check drainage systems.")
        elif rainfall > 10:
            alerts.append(f"🟡 Moderate rainfall ({rainfall}mm): May need to reduce irrigation schedule.")

        if wind > 30:
            alerts.append(f"🔴 Strong winds ({wind} km/h): Stake tall plants. Delay spraying operations.")
        elif wind > 20:
            alerts.append(f"🟡 Moderate wind ({wind} km/h): Avoid spray applications.")

        if not alerts:
            alerts.append("✅ Weather conditions are favorable for farming activities.")

        return alerts


# Singleton instance
soil_analysis_service = SoilAnalysisService()
