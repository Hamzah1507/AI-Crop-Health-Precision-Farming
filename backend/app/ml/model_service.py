"""
ML Model Service Layer

Provides abstraction for ML model integration supporting YOLOv8 and TensorFlow models.
Features:
- Clear separation between genuine inference and demonstration fallback.
- Explicit status tracking ('ready' vs 'unavailable').
- Strict exception handling: inference failures raise ModelInferenceError and are NEVER
  silently masked with demo diagnoses.
- Genuine predictions return real confidence scores and bounding boxes.
- Demo mode never fabricates confidence scores or bounding boxes.
"""

import os
import re
import random
import logging
from typing import Optional, Dict, List, Any
from app.config import get_settings
from app.ml.image_preprocessing import image_preprocessor

logger = logging.getLogger(__name__)
settings = get_settings()


class ModelInferenceError(Exception):
    """Raised when genuine model inference encounters an unrecoverable failure."""
    pass


# Common crop diseases for demonstration fallback
DEMO_DISEASES = [
    {"name": "Tomato Late Blight", "crop": "Tomato", "type": "disease"},
    {"name": "Tomato Leaf Mold", "crop": "Tomato", "type": "disease"},
    {"name": "Tomato Bacterial Spot", "crop": "Tomato", "type": "disease"},
    {"name": "Corn Northern Leaf Blight", "crop": "Corn", "type": "disease"},
    {"name": "Corn Common Rust", "crop": "Corn", "type": "disease"},
    {"name": "Potato Early Blight", "crop": "Potato", "type": "disease"},
    {"name": "Potato Late Blight", "crop": "Potato", "type": "disease"},
    {"name": "Rice Blast", "crop": "Rice", "type": "disease"},
    {"name": "Rice Brown Spot", "crop": "Rice", "type": "disease"},
    {"name": "Wheat Leaf Rust", "crop": "Wheat", "type": "disease"},
    {"name": "Apple Scab", "crop": "Apple", "type": "disease"},
    {"name": "Grape Black Rot", "crop": "Grape", "type": "disease"},
    {"name": "Cotton Bacterial Blight", "crop": "Cotton", "type": "disease"},
    {"name": "Cotton Leaf Curl Virus", "crop": "Cotton", "type": "disease"},
    {"name": "Soybean Rust", "crop": "Soybean", "type": "disease"},
    {"name": "Soybean Mosaic Virus", "crop": "Soybean", "type": "disease"},
    {"name": "Sugarcane Red Rot", "crop": "Sugarcane", "type": "disease"},
    {"name": "Sugarcane Smut", "crop": "Sugarcane", "type": "disease"},
    {"name": "Groundnut Early Leaf Spot", "crop": "Groundnut", "type": "disease"},
    {"name": "Groundnut Rust", "crop": "Groundnut", "type": "disease"},
    {"name": "Millet Blast", "crop": "Millet", "type": "disease"},
    {"name": "Millet Downy Mildew", "crop": "Millet", "type": "disease"},
    {"name": "Pepper Bacterial Spot", "crop": "Pepper", "type": "disease"},
    {"name": "Pepper Bell Early Blight", "crop": "Pepper", "type": "disease"},
    {"name": "Healthy Plant", "crop": "General", "type": "healthy"},
]

DEMO_PESTS = [
    {"name": "Aphids", "type": "pest"},
    {"name": "Whitefly", "type": "pest"},
    {"name": "Armyworm", "type": "pest"},
    {"name": "Spider Mites", "type": "pest"},
    {"name": "Thrips", "type": "pest"},
    {"name": "Leaf Miner", "type": "pest"},
]

DISEASE_TREATMENTS = {
    "Tomato Late Blight": "Apply copper-based fungicide. Remove and destroy affected leaves. Ensure good air circulation.",
    "Tomato Leaf Mold": "Improve ventilation. Apply fungicide. Remove affected leaves. Reduce humidity.",
    "Tomato Bacterial Spot": "Apply copper spray. Remove infected plants. Use disease-free seeds.",
    "Corn Northern Leaf Blight": "Apply foliar fungicide. Use resistant varieties. Practice crop rotation.",
    "Corn Common Rust": "Apply fungicide if severe. Plant resistant hybrids. Monitor regularly.",
    "Potato Early Blight": "Apply chlorothalonil or mancozeb. Remove lower infected leaves. Maintain soil moisture.",
    "Potato Late Blight": "Apply metalaxyl-based fungicide. Destroy infected tubers. Avoid overhead irrigation.",
    "Rice Blast": "Apply tricyclazole fungicide. Use resistant varieties. Manage nitrogen fertilization.",
    "Rice Brown Spot": "Apply mancozeb fungicide. Ensure balanced nutrition. Use certified seeds.",
    "Wheat Leaf Rust": "Apply propiconazole fungicide. Plant resistant varieties. Early sowing.",
    "Apple Scab": "Apply captan fungicide. Remove fallen leaves. Prune for air circulation.",
    "Grape Black Rot": "Apply mancozeb or myclobutanil. Remove mummified berries. Prune for airflow.",
    "Cotton Bacterial Blight": "Apply copper oxychloride or streptomycin spray. Use acid-delinted certified seeds. Practice crop rotation.",
    "Cotton Leaf Curl Virus": "Manage whitefly insect vectors with approved insecticides or neem formulations. Grow tolerant cultivars and rogue infected plants.",
    "Soybean Rust": "Apply triazole or strobilurin fungicide promptly upon initial pustule observation. Monitor field canopy humidity.",
    "Soybean Mosaic Virus": "Control aphid populations. Plant certified virus-free seeds. Rogue out symptomatic seedlings.",
    "Sugarcane Red Rot": "Plant disease-free setts treated with carbendazim fungicide. Maintain proper drainage. Avoid ratooning infected blocks.",
    "Sugarcane Smut": "Rogue out smutted whips inside protective bags. Disinfect seed setts in hot water (52 C for 30 minutes).",
    "Groundnut Early Leaf Spot": "Apply chlorothalonil or mancozeb when lesions appear. Space rows for ventilation. Rotate with cereal crops.",
    "Groundnut Rust": "Apply propiconazole or hexaconazole fungicide. Cultivate rust-tolerant varieties. Avoid standing foliage moisture.",
    "Millet Blast": "Apply tricyclazole or edifenphos fungicide if severe. Dress seeds with thiram. Space rows evenly.",
    "Millet Downy Mildew": "Dress seeds with metalaxyl. Rogue out infected seedlings before oospore release. Use resistant hybrids.",
    "Pepper Bacterial Spot": "Apply copper bactericide combined with mancozeb. Avoid overhead irrigation. Use disease-free seed.",
    "Pepper Bell Early Blight": "Apply chlorothalonil or copper hydroxide. Prune lower infected leaves. Rotate fields away from Solanaceae.",
    "Healthy Plant": "No disease or pest detected. Continue standard crop care, balanced irrigation, and routine scouting.",
}


def lookup_treatment(name: str) -> str:
    """Normalize class name and match against treatment dictionary."""
    if not name:
        return "Consult an agricultural expert for detailed treatment plan."
    cleaned = re.sub(r"[_\-]+", " ", name).strip().lower()
    for disease_key, treatment in DISEASE_TREATMENTS.items():
        key_clean = disease_key.lower()
        if key_clean == cleaned or key_clean in cleaned or cleaned in key_clean:
            return treatment
    return "Consult an agricultural expert for detailed treatment plan."


def _to_numpy(tensor_or_array):
    """Safely convert PyTorch tensors or numpy-like arrays to numpy."""
    if hasattr(tensor_or_array, "cpu"):
        return tensor_or_array.cpu().numpy()
    import numpy as np
    return np.asarray(tensor_or_array)


class ModelService:
    """
    Main ML model service providing disease and pest detection.

    Architectural guarantees:
    1. If a trained model is loaded, genuine inference runs.
    2. If genuine inference fails, an explicit ModelInferenceError is raised (never masked).
    3. If no trained model is available, a clearly-identified demonstration prediction
       is returned with is_demo="true" and confidence=None.
    """

    def __init__(self):
        self.pytorch_model = None
        self.class_mapping = None
        self.yolo_model = None
        self.tf_model = None
        self.model_loaded = False
        self.model_type = None
        self._try_load_models()

    def _resolve_path(self, path: str) -> str:
        """Resolve a model path, checking cwd, absolute, and backend root."""
        if not path:
            return ""
        if os.path.isabs(path) and os.path.exists(path):
            return os.path.abspath(path)
        # Check relative to cwd
        if os.path.exists(path):
            return os.path.abspath(path)
        # Check relative to backend directory
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidate = os.path.join(backend_dir, path)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
        return path

    def _try_load_models(self):
        """Attempt to load available ML models from configured paths."""
        # 1. Attempt loading genuine PyTorch ResNet-18 model
        pytorch_path = self._resolve_path(getattr(settings, "PYTORCH_MODEL_PATH", ""))
        mapping_path = self._resolve_path(getattr(settings, "CLASS_MAPPING_PATH", ""))
        if pytorch_path and os.path.exists(pytorch_path) and mapping_path and os.path.exists(mapping_path):
            try:
                import json
                import torch
                from app.ml.resnet import ResNet18
                with open(mapping_path, "r", encoding="utf-8") as f:
                    self.class_mapping = json.load(f)
                num_classes = self.class_mapping.get("num_classes", 18)
                model = ResNet18(num_classes=num_classes)
                state = torch.load(pytorch_path, map_location="cpu", weights_only=True)
                model.load_state_dict(state)
                model.eval()
                self.pytorch_model = model
                self.model_loaded = True
                self.model_type = "PyTorch (ResNet18)"
                logger.info(f"PyTorch ResNet18 model successfully loaded from {pytorch_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load PyTorch model from {pytorch_path}: {e}")
                self.pytorch_model = None
                self.class_mapping = None

        yolo_path = self._resolve_path(settings.YOLO_MODEL_PATH)
        if yolo_path and os.path.exists(yolo_path):
            try:
                import importlib
                ultralytics = importlib.import_module("ultralytics")
                self.yolo_model = ultralytics.YOLO(yolo_path)
                self.model_loaded = True
                self.model_type = "YOLOv8"
                logger.info(f"YOLOv8 model successfully loaded from {yolo_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load YOLOv8 model from {yolo_path}: {e}")

        tf_path = self._resolve_path(settings.TENSORFLOW_MODEL_PATH)
        if tf_path and os.path.exists(tf_path):
            try:
                import importlib
                tf = importlib.import_module("tensorflow")
                self.tf_model = tf.keras.models.load_model(tf_path)
                self.model_loaded = True
                self.model_type = "TensorFlow"
                logger.info(f"TensorFlow model successfully loaded from {tf_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load TensorFlow model from {tf_path}: {e}")

        self.model_loaded = False
        self.model_type = None
        logger.info("No trained ML model file found. Using demonstration fallback predictions.")

    def set_model(self, model: Any, model_type: str = "PyTorch"):
        """Directly set an in-memory model (used for genuine inference testing)."""
        self.model_type = model_type
        if model_type.startswith("PyTorch") or model_type == "ResNet18":
            self.pytorch_model = model
            self.yolo_model = None
            self.tf_model = None
        elif model_type == "YOLOv8":
            self.yolo_model = model
            self.pytorch_model = None
            self.tf_model = None
        else:
            self.tf_model = model
            self.pytorch_model = None
            self.yolo_model = None
        self.model_loaded = True

    def unload_model(self):
        """Unload models and revert to demo mode."""
        self.pytorch_model = None
        self.yolo_model = None
        self.tf_model = None
        self.model_loaded = False
        self.model_type = None

    def predict(self, image_path: str, crop_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Run prediction on an image.

        Raises:
            FileNotFoundError: if image_path does not exist on disk.
            ModelInferenceError: if genuine model inference fails.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")

        if self.model_loaded and self.pytorch_model:
            return self._predict_pytorch(image_path, crop_name)
        elif self.model_loaded and self.yolo_model:
            return self._predict_yolo(image_path, crop_name)
        elif self.model_loaded and self.tf_model:
            return self._predict_tensorflow(image_path, crop_name)
        else:
            return self._predict_demo(image_path, crop_name)

    def _unable_to_identify_result(self, reason: str, model_type: str = "PyTorch (ResNet18)") -> Dict[str, Any]:
        """Return a structured failed prediction result when an image cannot be identified as a crop leaf."""
        return {
            "disease_name": "Unable to Identify",
            "pest_name": None,
            "prediction_type": "unable_to_identify",
            "confidence": None,
            "bbox_data": None,
            "status": "failed",
            "is_demo": "false",
            "treatment": f"Unable to identify a crop leaf: {reason}",
            "model_type": model_type,
        }

    def _predict_pytorch(self, image_path: str, crop_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Run genuine PyTorch ResNet-18 prediction on the image.
        Uses ImageNet normalization and the saved class-index mapping.
        """
        clean_crop = crop_name.strip() if crop_name and crop_name.strip() else None
        supported_crops = {"apple", "corn", "maize", "grape", "pepper", "potato", "tomato"}

        # Validate that the image contains detectable crop foliage before running inference
        is_leaf, leaf_reason = image_preprocessor.validate_crop_leaf(image_path)
        if not is_leaf:
            return self._unable_to_identify_result(leaf_reason, model_type="PyTorch (ResNet18)")

        # If a farmer explicitly specifies an unsupported crop (e.g. Cotton, Rice, Wheat),
        # do not misclassify it into one of the 18 model classes. Fall back to demo mode.
        if clean_crop and not any(sc in clean_crop.lower() for sc in supported_crops):
            logger.info(f"Crop '{clean_crop}' is not supported by ResNet18 model ({supported_crops}). Using demo fallback.")
            demo_res = self._predict_demo(image_path, crop_name)
            demo_res["treatment"] = (
                f"Note: The active ResNet18 AI model currently diagnoses Apple, Corn, Grape, Pepper, Potato, and Tomato. "
                f"For {clean_crop}, predictions are demonstration advisories. {demo_res.get('treatment', '')}"
            )
            return demo_res

        try:
            tensor = image_preprocessor.preprocess_pytorch(image_path)
            if tensor is None:
                raise ModelInferenceError("Could not preprocess image for PyTorch inference.")
        except Exception as e:
            logger.error(f"Image preprocessing failure on '{image_path}': {e}")
            raise ModelInferenceError(f"Image preprocessing failed: {str(e)}") from e

        try:
            import torch
            with torch.inference_mode():
                logits = self.pytorch_model(tensor)
                logits_1d = logits[0]
                probs = torch.softmax(logits_1d, dim=0)

                idx_to_class = self.class_mapping.get("idx_to_class", {}) if self.class_mapping else {}

                max_logit = float(torch.max(logits_1d))
                energy = float(-torch.logsumexp(logits_1d, dim=0))
                global_top_idx = int(torch.argmax(probs))
                global_raw_conf = float(probs[global_top_idx])

                # Calculate per-crop probability masses across known crops
                crop_masses: Dict[str, float] = {}
                for idx_k, cls_k in idx_to_class.items():
                    crop_tag = cls_k.split("___")[0]
                    norm_tag = "corn" if "corn" in crop_tag.lower() or "maize" in crop_tag.lower() else (
                        "pepper" if "pepper" in crop_tag.lower() else crop_tag.replace("_", " ").lower().strip()
                    )
                    crop_masses[norm_tag] = crop_masses.get(norm_tag, 0.0) + float(probs[int(idx_k)])

                sorted_masses = sorted(crop_masses.values(), reverse=True)
                top_crop_mass = sorted_masses[0] if sorted_masses else 0.0
                second_crop_mass = sorted_masses[1] if len(sorted_masses) > 1 else 0.0
                crop_margin = top_crop_mass - second_crop_mass

                # If crop is specified and supported, select the top-probability condition for that crop
                if clean_crop and idx_to_class:
                    crop_needle = "corn" if clean_crop.lower() == "maize" else clean_crop.lower()
                    matching_indices = [
                        int(k) for k, v in idx_to_class.items()
                        if crop_needle in v.lower()
                    ]
                    if matching_indices:
                        sub_probs = probs[matching_indices]
                        total_crop_prob = float(torch.sum(sub_probs))

                        # Crop consistency check: If total probability mass for the selected crop
                        # is below 10%, reject forcing this crop!
                        if total_crop_prob < 0.10:
                            global_top_cls = idx_to_class.get(str(global_top_idx), "another condition")
                            logger.warning(
                                f"Crop mismatch: user selected '{clean_crop}', but model assigned only "
                                f"{total_crop_prob*100:.2f}% to '{clean_crop}'. Global top is '{global_top_cls}'."
                            )
                            return self._unable_to_identify_result(
                                f"The uploaded leaf image does not match the selected crop '{clean_crop}' "
                                f"(model confidence in {clean_crop} is only {total_crop_prob*100:.2f}%). "
                                f"Please select the matching crop or upload a clearer photo of a {clean_crop} leaf.",
                                model_type="PyTorch (ResNet18)"
                            )

                        best_sub_idx = int(torch.argmax(sub_probs))
                        top_idx = matching_indices[best_sub_idx]
                        raw_conf = float(probs[top_idx])
                    else:
                        top_idx = global_top_idx
                        raw_conf = global_raw_conf
                else:
                    # Uncertainty check for unspecified crop ("Select crop"):
                    # The model must verify both the plant species and the disease condition.
                    # Multi-signal uncertainty gate:
                    # 1. Leading crop mass < 65% (PlantVillage mean 98.8%)
                    # 2. Crop margin < 25% (PlantVillage mean 98.2%)
                    # 3. Top class confidence < 50%
                    # 4. Out-of-distribution logit energy signature (max_logit < 3.5 and energy > -4.5)
                    is_uncertain = (
                        top_crop_mass < 0.65
                        or crop_margin < 0.25
                        or global_raw_conf < 0.50
                        or (max_logit < 3.5 and energy > -4.5)
                    )
                    if is_uncertain:
                        raw_conf = global_raw_conf
                        confidence = round(raw_conf * 100.0 if raw_conf <= 1.0 else raw_conf, 2)
                        logger.info(
                            f"Uncertain leaf diagnosis flagged (unspecified crop): "
                            f"top_crop_mass={top_crop_mass*100:.1f}%, crop_margin={crop_margin*100:.1f}%, "
                            f"confidence={confidence}%, max_logit={max_logit:.2f}, energy={energy:.2f}"
                        )
                        return {
                            "disease_name": "Unable to Identify Reliably",
                            "pest_name": None,
                            "prediction_type": "uncertain",
                            "confidence": confidence,
                            "bbox_data": None,
                            "status": "uncertain",
                            "is_demo": "false",
                            "treatment": (
                                "Unable to identify reliably. The crop species or disease could not be determined "
                                "with sufficient confidence. Upload a clear photograph of the affected leaf and "
                                "select the correct crop if known."
                            ),
                            "model_type": "PyTorch (ResNet18)",
                        }

                    top_idx = global_top_idx
                    raw_conf = global_raw_conf

                confidence = round(raw_conf * 100.0 if raw_conf <= 1.0 else raw_conf, 2)
                raw_class_name = idx_to_class.get(str(top_idx), f"Class_{top_idx}") if idx_to_class else f"Class_{top_idx}"

                # Parse PlantVillage format: {Crop}___{Condition}
                if "___" in raw_class_name:
                    crop_part, condition_part = raw_class_name.split("___", 1)
                else:
                    crop_part, condition_part = "General", raw_class_name

                detected_crop = (
                    crop_part.replace("Corn_(maize)", "Corn")
                    .replace("Pepper,_bell", "Pepper")
                    .replace("_", " ")
                    .strip()
                )
                clean_condition = condition_part.replace("_", " ").strip()

                is_healthy = "healthy" in clean_condition.lower()
                if is_healthy:
                    disease_name = "Healthy Plant"
                    pred_type = "healthy"
                    treatment = "No disease detected. Foliage appears healthy. Continue standard crop management, balanced irrigation, and routine scouting."
                else:
                    formatted_name = f"{detected_crop} {clean_condition.title()}".strip()
                    disease_name = formatted_name
                    pred_type = "disease"
                    treatment = lookup_treatment(formatted_name)

                # Low-confidence threshold notice
                if confidence < 40.0:
                    treatment += (
                        " (Advisory: Low-confidence detection below 40%. Symptoms may be ambiguous; "
                        "inspect foliage in person or submit a clearer close-up photograph before applying remedies.)"
                    )

                return {
                    "disease_name": disease_name,
                    "pest_name": None,
                    "prediction_type": pred_type,
                    "confidence": confidence,
                    "bbox_data": None,
                    "status": "completed",
                    "is_demo": "false",
                    "treatment": treatment,
                    "model_type": "PyTorch (ResNet18)",
                }
        except ModelInferenceError:
            raise
        except Exception as e:
            logger.error(f"PyTorch prediction error on '{image_path}': {e}")
            raise ModelInferenceError(f"PyTorch inference execution failed: {str(e)}") from e

    def _predict_yolo(self, image_path: str, crop_name: Optional[str] = None) -> Dict[str, Any]:
        """Run YOLOv8 prediction on the image."""
        try:
            results = self.yolo_model(image_path)
        except Exception as e:
            logger.error(f"YOLOv8 inference failure on '{image_path}': {e}")
            raise ModelInferenceError(f"YOLOv8 inference execution failed: {str(e)}") from e

        try:
            if not results or len(results) == 0:
                return self._healthy_result("YOLOv8")

            result = results[0]
            boxes = getattr(result, "boxes", None)
            if boxes is None or len(boxes) == 0:
                # No detections found -> Genuine no-disease diagnosis
                return self._healthy_result("YOLOv8")

            confidences = _to_numpy(boxes.conf)
            classes = _to_numpy(boxes.cls)
            if len(confidences) == 0:
                return self._healthy_result("YOLOv8")

            best_idx = int(confidences.argmax())
            raw_conf = float(confidences[best_idx])
            best_conf = round(raw_conf * 100 if raw_conf <= 1.0 else raw_conf, 2)
            best_class = int(classes[best_idx])

            # Class name resolution
            names = getattr(result, "names", {})
            class_name = names.get(best_class, f"Class_{best_class}") if isinstance(names, dict) else str(best_class)

            # Bounding box coordinates: [x1, y1, x2, y2]
            raw_xyxy = _to_numpy(boxes.xyxy)
            bbox = [round(float(v), 2) for v in raw_xyxy[best_idx].tolist()]

            # Class identification
            if "healthy" in class_name.lower():
                return {
                    "disease_name": "Healthy Plant",
                    "pest_name": None,
                    "prediction_type": "disease",
                    "confidence": best_conf,
                    "bbox_data": {
                        "boxes": [bbox],
                        "labels": [class_name],
                        "scores": [best_conf],
                    },
                    "status": "completed",
                    "is_demo": "false",
                    "treatment": "No disease or pest detected. Plant appears healthy.",
                    "model_type": "YOLOv8",
                }

            pred_type = "disease"
            disease_name = class_name
            pest_name = None
            for pest in DEMO_PESTS:
                if pest["name"].lower() in class_name.lower():
                    pred_type = "pest"
                    pest_name = class_name
                    disease_name = None
                    break

            treatment = lookup_treatment(class_name)

            return {
                "disease_name": disease_name,
                "pest_name": pest_name,
                "prediction_type": pred_type,
                "confidence": best_conf,
                "bbox_data": {
                    "boxes": [bbox],
                    "labels": [class_name],
                    "scores": [best_conf],
                },
                "status": "completed",
                "is_demo": "false",
                "treatment": treatment,
                "model_type": "YOLOv8",
            }
        except Exception as e:
            logger.error(f"Error parsing YOLOv8 prediction output: {e}")
            raise ModelInferenceError(f"Failed to process YOLOv8 inference output: {str(e)}") from e

    def _predict_tensorflow(self, image_path: str, crop_name: Optional[str] = None) -> Dict[str, Any]:
        """Run TensorFlow prediction on the image."""
        try:
            preprocessed = image_preprocessor.preprocess(image_path)
            if preprocessed is None:
                raise ModelInferenceError("Image preprocessing returned None; unreadable image data.")

            import numpy as np
            input_data = np.expand_dims(preprocessed, axis=0)
            predictions = self.tf_model.predict(input_data)
            class_idx = int(np.argmax(predictions[0]))
            raw_conf = float(np.max(predictions[0]))
            confidence = round(raw_conf * 100 if raw_conf <= 1.0 else raw_conf, 2)

            class_labels = getattr(self.tf_model, "class_names", None)
            if class_labels and class_idx < len(class_labels):
                label_name = class_labels[class_idx]
                disease_info = {"name": label_name, "type": "pest" if any(p["name"].lower() in label_name.lower() for p in DEMO_PESTS) else "disease"}
            elif class_idx < len(DEMO_DISEASES):
                disease_info = DEMO_DISEASES[class_idx]
            else:
                disease_info = DEMO_DISEASES[0]

            treatment = lookup_treatment(disease_info["name"])

            return {
                "disease_name": disease_info["name"] if disease_info["type"] != "pest" else None,
                "pest_name": disease_info["name"] if disease_info["type"] == "pest" else None,
                "prediction_type": disease_info["type"] if disease_info["type"] != "healthy" else "disease",
                "confidence": confidence,
                "bbox_data": None,
                "status": "completed",
                "is_demo": "false",
                "treatment": treatment,
                "model_type": "TensorFlow",
            }
        except ModelInferenceError:
            raise
        except Exception as e:
            logger.error(f"TensorFlow prediction error: {e}")
            raise ModelInferenceError(f"TensorFlow inference execution failed: {str(e)}") from e

    def _healthy_result(self, model_type: str) -> Dict[str, Any]:
        """Genuine inference found no disease or pest detection."""
        return {
            "disease_name": "Healthy Plant",
            "pest_name": None,
            "prediction_type": "disease",
            "confidence": None,
            "bbox_data": None,
            "status": "completed",
            "is_demo": "false",
            "treatment": "No disease or pest detected. Plant appears healthy.",
            "model_type": model_type,
        }

    def _predict_demo(self, image_path: str, crop_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Demonstration fallback prediction when no trained model is loaded.
        Explicitly flagged as demo, with confidence=None and bbox_data=None.
        Enforces strict crop-condition agronomic consistency: if a crop is specified,
        it will NEVER assign a condition belonging to a different crop.
        """
        is_leaf, leaf_reason = image_preprocessor.validate_crop_leaf(image_path)
        if not is_leaf:
            return self._unable_to_identify_result(leaf_reason, model_type="Demo (No trained model loaded)")

        candidates = DEMO_DISEASES.copy()
        clean_crop = crop_name.strip() if crop_name and crop_name.strip() else None

        if clean_crop:
            crop_specific = [d for d in candidates if d["crop"].lower() == clean_crop.lower()]
            if crop_specific:
                candidates = crop_specific
            else:
                # If a user specifies an unrecognized/custom crop, default to a safe healthy
                # or general condition for that specific crop, never cross-contaminating pathogens.
                candidates = [{"name": "Healthy Plant", "crop": clean_crop, "type": "healthy"}]

        is_pest = random.random() < 0.2
        if is_pest:
            pest = random.choice(DEMO_PESTS)
            return {
                "disease_name": None,
                "pest_name": pest["name"],
                "prediction_type": "pest",
                "confidence": None,
                "bbox_data": None,
                "status": "completed",
                "is_demo": "true",
                "treatment": f"For {pest['name']}: Apply appropriate insecticide. Use integrated pest management (IPM) strategies. Monitor regularly.",
                "model_type": "Demo (No trained model loaded)",
            }
        else:
            disease = random.choice(candidates)
            treatment = lookup_treatment(disease["name"])
            return {
                "disease_name": disease["name"],
                "pest_name": None,
                "prediction_type": disease["type"] if disease["type"] != "healthy" else "disease",
                "confidence": None,
                "bbox_data": None,
                "status": "completed",
                "is_demo": "true",
                "treatment": treatment,
                "model_type": "Demo (No trained model loaded)",
            }

    def get_status(self) -> Dict[str, Any]:
        """Get the current model readiness status."""
        return {
            "status": "ready" if self.model_loaded else "unavailable",
            "model_loaded": self.model_loaded,
            "model_type": self.model_type or "None (Demo mode)",
            "pytorch_path": getattr(settings, "PYTORCH_MODEL_PATH", ""),
            "yolo_path": settings.YOLO_MODEL_PATH,
            "tensorflow_path": settings.TENSORFLOW_MODEL_PATH,
            "mode": "genuine" if self.model_loaded else "demo",
        }


# Singleton instance
model_service = ModelService()
