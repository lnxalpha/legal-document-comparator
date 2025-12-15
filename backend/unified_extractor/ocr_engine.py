# ----------------------------
# file: unified_extractor/ocr_engine.py
# ----------------------------
"""Tesseract + EasyOCR wrapper. Provides a singleton engine for reuse."""
from PIL import Image, ImageEnhance
import pytesseract
import easyocr
import numpy as np
from typing import Tuple
import cv2

class OCREngines:
    _singleton = None

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        try:
            # EasyOCR reader initialization can be slow; we keep it once per process
            self.reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)
        except Exception:
            self.reader = None

        self.configs = {
            "default": "--psm 6 --oem 3",
            "citation": "--psm 6 --oem 3 -c tessedit_char_blacklist=|",
            "body": "--psm 4 --oem 3",
        }

    @classmethod
    def get_singleton(cls, use_gpu: bool = False):
        if cls._singleton is None:
            cls._singleton = cls(use_gpu=use_gpu)
        return cls._singleton

    def tesseract(self, img_arr: np.ndarray, config_type: str = "default") -> Tuple[str, float]:
        try:
            pil = Image.fromarray(img_arr)
            if pil.height < 30:
                scale = 30 / pil.height
                pil = pil.resize((int(pil.width * scale), 30), Image.Resampling.LANCZOS)
            pil = ImageEnhance.Sharpness(pil).enhance(1.5)
            pil = ImageEnhance.Contrast(pil).enhance(1.3)
            data = pytesseract.image_to_data(pil, config=self.configs.get(config_type, self.configs["default"]), output_type=pytesseract.Output.DICT)
            words, confs = [], []
            for w, c in zip(data.get("text", []), data.get("conf", [])):
                try:
                    if str(w).strip() and int(float(c)) > 0:
                        words.append(str(w))
                        confs.append(int(float(c))/100.0)
                except Exception:
                    continue
            if not words:
                return "", 0.0
            return " ".join(words), float(sum(confs)/len(confs))
        except Exception:
            return "", 0.0

    def easyocr(self, img_arr: np.ndarray) -> Tuple[str, float]:
        if self.reader is None:
            return "", 0.0
        try:
            if len(img_arr.shape) == 2:
                img = cv2.cvtColor(img_arr, cv2.COLOR_GRAY2BGR)
            else:
                img = img_arr
            results = self.reader.readtext(img, detail=1)
            texts, confs = [], []
            for r in results:
                if len(r) >= 3:
                    texts.append(str(r[1]).strip())
                    confs.append(float(r[2]))
            if not texts:
                return "", 0.0
            return " ".join(texts), float(np.mean(confs))
        except Exception:
            return "", 0.0
