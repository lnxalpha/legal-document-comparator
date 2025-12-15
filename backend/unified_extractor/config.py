## unified_extractor/config.py
from dataclasses import dataclass

MIN_CONFIDENCE_THRESHOLD = 0.7
QUALITY_ERROR_MULTIPLIER = 10.0
DEFAULT_PDF_MATRIX_SCALE = 2.0
MIN_LINE_HEIGHT = 5
MIN_LINE_WIDTH = 10

@dataclass
class OCRConfig:
    tesseract_default_psm: int = 6
    tesseract_default_oem: int = 3
    tesseract_citation_psm: int = 6
    tesseract_body_psm: int = 4
    min_confidence: int = 30
    use_gpu: bool = False
    easyocr_languages: list = None

    def __post_init__(self):
        if self.easyocr_languages is None:
            self.easyocr_languages = ["en"]

    def get_tesseract_config(self, mode="default") -> str:
        if mode == "citation":
            return f"--psm {self.tesseract_citation_psm} --oem {self.tesseract_default_oem}"
        if mode == "body":
            return f"--psm {self.tesseract_body_psm} --oem {self.tesseract_default_oem}"
        return f"--psm {self.tesseract_default_psm} --oem {self.tesseract_default_oem}"
