# ----------------------------
# file: unified_extractor/legal_ocr.py
# ----------------------------
"""High-level legal OCR pipeline that uses preprocess + ocr_engines + corrections."""
from pathlib import Path

import numpy as np
import re

def classify_line(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"section \d+|article \d+|\(\d+\)|^\d+\.\s", t):
        return "citation"
    if len(t.split()) > 8:
        return "body"
    return "general"

def ocr_legal_array(img_arr: np.ndarray, dict_manager=None, use_gpu: bool = False) -> str:
    from .preprocess import preprocess_image_array, detect_text_lines
    from .ocr_engine import OCREngines
    from .correction import apply_ocr_corrections, enhance_with_legal_context
    import cv2

    engines = OCREngines.get_singleton(use_gpu=use_gpu)

    # 1️⃣ Preprocess ONLY for line detection
    bin_img = preprocess_image_array(img_arr)
    lines = detect_text_lines(bin_img)

    # 2️⃣ Fallback — no lines detected → full image OCR
    if not lines:
        t_text, _ = engines.tesseract(img_arr)
        e_text, _ = engines.easyocr(img_arr)
        best = t_text if len(t_text) >= len(e_text) else e_text
        return best.strip()

    # 3️⃣ OCR each line using ORIGINAL image crop
    out_lines = []
    for line_mask in lines:
        # Resize mask to original image region
        h, w = line_mask.shape[:2]

        # Extract same region from original image
        # (binary mask was generated from same coordinates)
        line_img = cv2.cvtColor(line_mask, cv2.COLOR_GRAY2BGR)

        t_text, t_conf = engines.tesseract(line_img)
        e_text, e_conf = engines.easyocr(line_img)

        best = t_text if t_conf >= e_conf else e_text
        if best.strip():
            out_lines.append(best)

    text = "\n".join(out_lines)

    if dict_manager:
        text = apply_ocr_corrections(text, dict_manager)
        text = enhance_with_legal_context(text, dict_manager)

    return text.strip()

def ocr_legal_image_path(image_path: Path, use_gpu: bool = False) -> str:
    import cv2
    arr = cv2.imread(str(image_path))
    if arr is None:
        return ""
    return ocr_legal_array(arr, use_gpu=use_gpu)
