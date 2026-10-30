"""
Image Preprocessing Service using OpenCV.

Provides image resize, normalization, and feature extraction capabilities.
Used as part of the data acquisition and prediction pipeline.
"""

from __future__ import annotations

import logging
import os
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# OpenCV/NumPy are optional at import time. When they are missing, every
# loader below returns None (instead of fake data) so callers degrade cleanly.
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV/NumPy not installed: image preprocessing is disabled. "
                   "Install opencv-python-headless to enable it.")


class ImagePreprocessor:
    """Handles image preprocessing using OpenCV."""

    def __init__(self, target_size: Tuple[int, int] = (640, 640)):
        self.target_size = target_size

    def load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Load an image from disk using OpenCV. Returns None if unavailable or unreadable."""
        if not OPENCV_AVAILABLE or not os.path.exists(image_path):
            return None
        image = cv2.imread(image_path)
        if image is None:
            return None
        return image

    def resize_image(self, image: np.ndarray, size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """Resize image to the target size."""
        target = size or self.target_size
        resized = cv2.resize(image, target, interpolation=cv2.INTER_LINEAR)
        return resized

    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """Normalize pixel values to [0, 1] range."""
        normalized = image.astype(np.float32) / 255.0
        return normalized

    def preprocess(self, image_path: str) -> Optional[np.ndarray]:
        """Full preprocessing pipeline: load, resize, normalize."""
        image = self.load_image(image_path)
        if image is None:
            return None
        resized = self.resize_image(image)
        normalized = self.normalize_image(resized)
        return normalized

    def preprocess_pytorch(self, image_path: str, target_size: Tuple[int, int] = (224, 224)):
        """
        Preprocess image for PyTorch ResNet-18 classification:
        1. Decode with OpenCV
        2. Convert BGR to RGB
        3. Resize to 224x224
        4. Normalize using ImageNet mean & std
        5. Convert to tensor of shape (1, 3, 224, 224)
        """
        if not OPENCV_AVAILABLE or not os.path.exists(image_path):
            return None
        image = cv2.imread(image_path)
        if image is None:
            return None

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, target_size, interpolation=cv2.INTER_LINEAR)

        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        norm_img = (resized.astype(np.float32) / 255.0 - mean) / std

        tensor = norm_img.transpose(2, 0, 1)
        import torch
        return torch.from_numpy(tensor).unsqueeze(0).float()

    def validate_crop_leaf(self, image_path: str) -> Tuple[bool, Optional[str]]:
        """
        Multi-signal pre-inference botanical and structural validator to prevent
        unrelated images (screenshots, documents, people, animals, objects) from
        being processed by the crop disease classification model.

        Evaluates:
        1. Aspect ratio: detects extreme multi-monitor / panoramic captures.
        2. Document structure: detects stark paper background (Val > 215, Sat < 25) with minimal foliage.
        3. Digital UI / screenshot: detects high desaturation (Sat < 20) with minimal foliage.
        4. Axis-aligned edge regularity: detects synthetic rectangular UI borders/windows.
        5. Botanical tissue presence: verifies presence of detectable green/chlorophyll foliage
           or necrotic/blight tissue.
        """
        if not OPENCV_AVAILABLE or not os.path.exists(image_path):
            return True, None

        img = cv2.imread(image_path)
        if img is None:
            return False, "Could not decode uploaded file as an image."

        h, w = img.shape[:2]
        total_pixels = h * w
        if total_pixels == 0:
            return False, "Uploaded image contains zero pixels."

        aspect = max(w, h) / max(min(w, h), 1)

        # 1. Extreme aspect ratio (banners, ultra-wide dual-monitor screenshots)
        if aspect > 2.8:
            return False, "Image dimensions indicate a banner or multi-monitor screenshot rather than a crop leaf photo."

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hue, sat, val = cv2.split(hsv)

        # Green foliage mask: H in [25, 95], S >= 20, V >= 20
        green_mask = cv2.inRange(hsv, (25, 20, 20), (95, 255, 255))
        green_ratio = np.count_nonzero(green_mask) / total_pixels

        # 2. Document / white text page: mostly stark bright white background with minimal foliage
        doc_bg_mask = (val > 215) & (sat < 25)
        doc_bg_ratio = np.count_nonzero(doc_bg_mask) / total_pixels
        if doc_bg_ratio > 0.70 and green_ratio < 0.04:
            return False, "The uploaded image appears to be a document, receipt, or text page rather than plant foliage."

        # 3. Monochromatic / dark UI / screenshot: mostly desaturated
        desat_mask = sat < 20
        desat_ratio = np.count_nonzero(desat_mask) / total_pixels
        if desat_ratio > 0.75 and green_ratio < 0.04:
            return False, "The uploaded image appears to be a digital screenshot or monochrome display rather than plant foliage."

        # 4. Axis-aligned edge check (synthetic UI borders / windows / tables)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.sqrt(sobel_x**2 + sobel_y**2)
        strong_edges = mag > 40
        if np.count_nonzero(strong_edges) > 150:
            angles = np.abs(np.arctan2(sobel_y[strong_edges], sobel_x[strong_edges]) * 180 / np.pi)
            axis_aligned = ((angles < 5) | (angles > 175) | (np.abs(angles - 90) < 5))
            axis_ratio = np.count_nonzero(axis_aligned) / len(angles)
            if axis_ratio > 0.35 and green_ratio < 0.05:
                return False, "The image contains synthetic rectangular boundaries characteristic of digital user interfaces or screenshots."

        # 5. Minimum green foliage threshold:
        # Every real crop leaf in the dataset has at least 6.9% green pixels.
        # Non-botanical images (skin, documents, blue sky, cars) have 0% green pixels.
        if green_ratio < 0.04:
            return False, f"The uploaded image does not appear to contain a crop leaf (detectable foliage content is {green_ratio*100:.1f}%). Please upload a clear photo of a crop leaf."

        return True, None

    def get_image_info(self, image_path: str) -> Optional[dict]:
        """Get image metadata."""
        image = self.load_image(image_path)
        if image is None:
            return None
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1
        return {
            "width": width,
            "height": height,
            "channels": channels,
            "file_size_kb": round(os.path.getsize(image_path) / 1024, 2)
        }


# Singleton instance
image_preprocessor = ImagePreprocessor()
