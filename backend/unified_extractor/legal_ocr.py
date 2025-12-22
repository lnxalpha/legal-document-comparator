# ----------------------------
# file: unified_extractor/legal_ocr.py
# ----------------------------
"""High-level legal OCR pipeline with provenance tracking."""
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import re
import logging

LOG = logging.getLogger(__name__)


def classify_line(text: str) -> str:
    """Classify line type for appropriate OCR settings."""
    t = (text or "").lower()
    if re.search(r"section \d+|article \d+|\(\d+\)|^\d+\.\s", t):
        return "citation"
    if len(t.split()) > 8:
        return "body"
    return "general"


def ocr_legal_array(
    img_arr: np.ndarray,
    dict_manager=None,
    use_gpu: bool = False
) -> Dict:
    """
    OCR a legal document image with provenance tracking.

    Returns:
        {
            "text": "combined text",
            "lines": [
                {
                    "text": "line text",
                    "confidence": 0.85,
                    "line_id": 0,
                    "ocr_method": "tesseract",
                    "bbox": (y1, y2, x1, x2)
                },
                ...
            ],
            "overall_confidence": 0.82,
            "method": "line_based"
        }
    """
    from .preprocess import preprocess_image_array, detect_text_line_coordinates
    from .correction import apply_ocr_corrections, enhance_with_legal_context
    
    def perform_ocr(img_arr, use_gpu=False):
        from .ocr_engine import OCREngines
        engines = OCREngines.get_singleton(use_gpu=False)
        text, conf = engines.tesseract(img_arr)
        return text, conf
    
    # 1️⃣ Preprocess ONLY for line detection
    bin_img = preprocess_image_array(img_arr)
    line_coords = detect_text_line_coordinates(bin_img)

    # 2️⃣ Fallback – no lines detected → full image OCR
    if not line_coords:
        LOG.warning("No lines detected, using full-image OCR")
        t_text, t_conf = engines.tesseract(img_arr)
        e_text, e_conf = engines.easyocr(img_arr)
        best = t_text if len(t_text) >= len(e_text) else e_text
        best_conf = max(t_conf, e_conf)

        if dict_manager:
            best = apply_ocr_corrections(best, dict_manager)
            best = enhance_with_legal_context(best, dict_manager)

        return {
            "text": best.strip(),
            "lines": [{
                "text": best.strip(),
                "confidence": best_conf,
                "line_id": 0,
                "ocr_method": "tesseract" if t_conf >= e_conf else "easyocr",
                "bbox": None
            }],
            "overall_confidence": best_conf,
            "method": "full_image"
        }

    # 3️⃣ OCR each line using ORIGINAL image crop
    out_lines = []
    confidences = []

    for line_id, (y_start, y_end, x_start, x_end) in enumerate(line_coords):
        # Crop from ORIGINAL image (not preprocessed!)
        line_img = img_arr[y_start:y_end, x_start:x_end]

        # Skip empty crops
        if line_img.size == 0:
            continue

        # Try both OCR engines
        t_text, t_conf = engines.tesseract(line_img)
        e_text, e_conf = engines.easyocr(line_img)

        # Select best result
        if t_conf >= e_conf:
            best_text = t_text
            best_conf = t_conf
            method = "tesseract"
        else:
            best_text = e_text
            best_conf = e_conf
            method = "easyocr"

        # IMPROVED: Retry with enhancement if confidence is low
        if best_conf < 0.6 and best_text.strip():
            LOG.debug(f"Line {line_id} has low confidence ({best_conf:.2f}), retrying with enhancement")
            enhanced = enhance_for_ocr(line_img)
            t_text_2, t_conf_2 = engines.tesseract(enhanced)
            e_text_2, e_conf_2 = engines.easyocr(enhanced)

            if max(t_conf_2, e_conf_2) > best_conf:
                best_text = t_text_2 if t_conf_2 >= e_conf_2 else e_text_2
                best_conf = max(t_conf_2, e_conf_2)
                method = "tesseract_enhanced" if t_conf_2 >= e_conf_2 else "easyocr_enhanced"
                LOG.debug(f"Enhancement improved confidence to {best_conf:.2f}")

        if best_text.strip():
            out_lines.append({
                "text": best_text,
                "confidence": best_conf,
                "line_id": line_id,
                "ocr_method": method,
                "bbox": (y_start, y_end, x_start, x_end)
            })
            confidences.append(best_conf)

    # Combine text
    combined_text = "\n".join(line["text"] for line in out_lines)

    # Apply corrections
    if dict_manager:
        combined_text = apply_ocr_corrections(combined_text, dict_manager)
        combined_text = enhance_with_legal_context(combined_text, dict_manager)

    # Calculate overall confidence
    overall_conf = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "text": combined_text.strip(),
        "lines": out_lines,
        "overall_confidence": overall_conf,
        "method": "line_based"
    }


def enhance_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Aggressive enhancement for problematic lines.
    Used when initial OCR has low confidence.
    """
    import cv2

    # Upscale if too small
    if img.shape[0] < 25:
        scale = 30 / img.shape[0]
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Convert to grayscale if needed
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Stronger denoising
    img = cv2.fastNlMeansDenoising(img, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    img = clahe.apply(img)

    # Sharpen
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    img = cv2.filter2D(img, -1, kernel)

    return img


def ocr_legal_image_path(image_path: Path, use_gpu: bool = False) -> Dict:
    """
    OCR an image file with provenance tracking.

    Returns same format as ocr_legal_array()
    """
    import cv2
    arr = cv2.imread(str(image_path))
    if arr is None:
        return {
            "text": "",
            "lines": [],
            "overall_confidence": 0.0,
            "method": "failed"
        }
    return ocr_legal_array(arr, use_gpu=use_gpu)
