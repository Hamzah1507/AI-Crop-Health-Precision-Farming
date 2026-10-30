"""
Crop Yield Prediction Service

Provides yield prediction based on crop, soil, and weather parameters.
Currently uses a rule-based model. Architecture supports replacement with
a trained ML model.
"""

from typing import Optional, Dict, Any


# Base yield data (tons/hectare) for different crops
CROP_BASE_YIELDS = {
    "rice": {"min": 3.0, "max": 8.0, "avg": 5.5},
    "wheat": {"min": 2.5, "max": 6.0, "avg": 4.0},
    "corn": {"min": 4.0, "max": 12.0, "avg": 8.0},
    "tomato": {"min": 20.0, "max": 80.0, "avg": 50.0},
    "potato": {"min": 15.0, "max": 45.0, "avg": 30.0},
    "soybean": {"min": 1.5, "max": 4.0, "avg": 2.5},
    "cotton": {"min": 1.0, "max": 3.0, "avg": 2.0},
    "sugarcane": {"min": 50.0, "max": 120.0, "avg": 80.0},
    "groundnut": {"min": 1.0, "max": 3.5, "avg": 2.0},
    "millet": {"min": 0.8, "max": 3.0, "avg": 1.5},
    "apple": {"min": 10.0, "max": 40.0, "avg": 25.0},
    "grape": {"min": 8.0, "max": 25.0, "avg": 15.0},
}


class YieldPredictionService:
    """
    Crop yield prediction service.

    Currently uses rule-based estimation. Can be replaced with
    a trained regression model (e.g., Random Forest, Neural Network).
    """

    def predict(
        self,
        crop_name: str,
        area: Optional[float] = None,
        soil_ph: Optional[float] = None,
        soil_nitrogen: Optional[float] = None,
        soil_phosphorus: Optional[float] = None,
        soil_potassium: Optional[float] = None,
        soil_moisture: Optional[float] = None,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        rainfall: Optional[float] = None,
        season: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Predict crop yield based on input parameters."""

        crop_key = crop_name.lower().strip()
        base = CROP_BASE_YIELDS.get(crop_key, {"min": 2.0, "max": 8.0, "avg": 5.0})

        # Calculate yield modifier based on soil and weather conditions
        modifier = 1.0
        factors = []

        # pH factor
        if soil_ph is not None:
            if 6.0 <= soil_ph <= 7.5:
                modifier *= 1.1
                factors.append({"factor": "Soil pH", "impact": "Positive", "detail": f"pH {soil_ph} is in optimal range"})
            elif soil_ph < 5.0 or soil_ph > 8.5:
                modifier *= 0.7
                factors.append({"factor": "Soil pH", "impact": "Negative", "detail": f"pH {soil_ph} is outside optimal range"})
            else:
                modifier *= 0.9
                factors.append({"factor": "Soil pH", "impact": "Slight Negative", "detail": f"pH {soil_ph} is slightly outside optimal range"})

        # Nitrogen factor
        if soil_nitrogen is not None:
            if 25 <= soil_nitrogen <= 50:
                modifier *= 1.1
                factors.append({"factor": "Nitrogen", "impact": "Positive", "detail": "Adequate nitrogen levels"})
            elif soil_nitrogen < 15:
                modifier *= 0.75
                factors.append({"factor": "Nitrogen", "impact": "Negative", "detail": "Low nitrogen may limit growth"})

        # Moisture factor
        if soil_moisture is not None:
            if 35 <= soil_moisture <= 65:
                modifier *= 1.05
                factors.append({"factor": "Soil Moisture", "impact": "Positive", "detail": "Optimal moisture levels"})
            elif soil_moisture < 20:
                modifier *= 0.6
                factors.append({"factor": "Soil Moisture", "impact": "Negative", "detail": "Drought stress likely"})
            elif soil_moisture > 80:
                modifier *= 0.7
                factors.append({"factor": "Soil Moisture", "impact": "Negative", "detail": "Waterlogging risk"})

        # Temperature factor
        if temperature is not None:
            if 20 <= temperature <= 30:
                modifier *= 1.05
                factors.append({"factor": "Temperature", "impact": "Positive", "detail": "Favorable growing temperature"})
            elif temperature > 40 or temperature < 5:
                modifier *= 0.65
                factors.append({"factor": "Temperature", "impact": "Negative", "detail": "Extreme temperature stress"})

        # Rainfall factor
        if rainfall is not None:
            if 5 <= rainfall <= 15:
                modifier *= 1.05
                factors.append({"factor": "Rainfall", "impact": "Positive", "detail": "Adequate rainfall"})
            elif rainfall > 30:
                modifier *= 0.8
                factors.append({"factor": "Rainfall", "impact": "Negative", "detail": "Excess rainfall may damage crops"})

        # Calculate predicted yield
        # Deterministic: the same inputs always give the same estimate
        predicted = base["avg"] * modifier
        predicted = max(base["min"] * 0.5, min(base["max"] * 1.2, predicted))
        predicted = round(predicted, 2)

        # Calculate total yield if area is provided
        total_yield = round(predicted * area, 2) if area else None

        # Confidence based on number of input parameters provided
        param_count = sum(1 for p in [soil_ph, soil_nitrogen, soil_phosphorus, soil_potassium,
                                       soil_moisture, temperature, humidity, rainfall] if p is not None)
        confidence = min(95, 50 + param_count * 6)

        return {
            "crop_name": crop_name,
            "predicted_yield": predicted,
            "yield_unit": "tons/hectare",
            "total_yield": total_yield,
            "total_yield_unit": "tons" if total_yield else None,
            "confidence": confidence,
            "yield_range": {"min": round(base["min"] * modifier * 0.9, 2),
                            "max": round(base["max"] * modifier * 0.9, 2)},
            "factors": factors,
            "is_demo": "true",
            "model_note": "Rule-based estimate from typical crop yields and simple soil/weather adjustments. Not a trained ML model."
        }


# Singleton instance
yield_prediction_service = YieldPredictionService()
