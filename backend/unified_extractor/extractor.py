# unified_extractor/extractor.py
"""Robust top-level document extraction orchestration with logging."""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Callable

from .config import OCRConfig, MIN_CONFIDENCE_THRESHOLD
from .io_utils import validate_file_path
from .utils import estimate_text_quality
from .correction import (
    DictionaryManager,
    apply_ocr_corrections,
    enhance_with_legal_context,
)

LOG = logging.getLogger(__name__)


# ========== EXTRACTION FUNCTIONS ==========

async def extract_from_txt(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except Exception as e:
        LOG.warning("Failed to read TXT %s: %s", path.name, e)
        return "<unreadable text file>"


async def extract_from_image(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None
) -> str:
    try:
        from .legal_ocr import ocr_legal_image_path
        use_gpu = getattr(config, "use_gpu", False) if config else False
        return ocr_legal_image_path(path, use_gpu=use_gpu)
    except Exception as e:
        LOG.warning("Failed to OCR image %s: %s", path.name, e)
        return "<unreadable image>"


async def extract_from_pdf(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None,
    parallel: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    try:
        import fitz
        from .legal_ocr import ocr_legal_array
        import cv2
        import numpy as np
        from PIL import Image
        import io

        if config is None:
            config = OCRConfig()
        if dict_manager is None:
            dict_manager = DictionaryManager.get_instance()

        doc = fitz.open(str(path))
        total = len(doc)
        texts = [None] * total

        def process_page(idx: int, page) -> str:
            try:
                text = page.get_text()
                if text.strip():
                    return text

                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                return ocr_legal_array(arr, dict_manager=dict_manager)
            except Exception as e:
                LOG.warning("Failed OCR on PDF page %d: %s", idx, e)
                return "<unreadable page>"

        if parallel:
            loop = asyncio.get_running_loop()
            tasks = []
            for i, page in enumerate(doc):
                tasks.append(loop.run_in_executor(None, process_page, i, page))
                if progress_callback:
                    progress_callback(i + 1, total)

            results = await asyncio.gather(*tasks)
            for i, result in enumerate(results):
                texts[i] = result
        else:
            for i, page in enumerate(doc):
                texts[i] = process_page(i, page)
                if progress_callback:
                    progress_callback(i + 1, total)

        doc.close()

        # Ensure all items are strings
        cleaned_texts = [str(t) if t else "<unreadable page>" for t in texts]
        return "\n\n".join(cleaned_texts)

    except Exception as e:
        LOG.warning("Failed to extract PDF %s: %s", path.name, e)
        return "<unreadable PDF>"


def extract_from_doc(path: Path) -> str:
    try:
        import mammoth
        with open(path, "rb") as f:
            text = mammoth.extract_raw_text(f).value
            return text if text.strip() else "<empty DOC>"
    except Exception as e:
        LOG.warning("Failed to extract DOC %s: %s", path.name, e)
        return "<unreadable DOC>"


async def extract_from_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(path)
        texts = [str(p.text) for p in doc.paragraphs if p.text]
        return "\n".join(texts) if texts else "<empty DOCX>"
    except Exception as e:
        LOG.warning("Failed to extract DOCX %s: %s", path.name, e)
        return "<unreadable DOCX>"


# ========== PUBLIC API ==========

async def extract_text(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    validate_file_path(path)

    if dict_manager is None:
        dict_manager = DictionaryManager.get_instance()
    if config is None:
        config = OCRConfig()

    suffix = path.suffix.lower()

    if suffix == '.pdf':
        text = await extract_from_pdf(path, config, dict_manager, progress_callback=progress_callback)
    elif suffix in {'.png', '.jpg', '.jpeg'}:
        text = await extract_from_image(path, config, dict_manager)
    elif suffix == '.docx':
        text = await extract_from_docx(path)
    elif suffix == '.doc':
        text = extract_from_doc(path)
    elif suffix == '.txt':
        text = await extract_from_txt(path)
    else:
        LOG.warning("Unsupported file type: %s", suffix)
        text = "<unsupported file type>"

    # Apply corrections safely
    try:
        text = apply_ocr_corrections(text, dict_manager)
        text = enhance_with_legal_context(text, dict_manager)
    except Exception as e:
        LOG.warning("Failed to apply OCR corrections: %s", e)

    # Ensure text is never empty
    if not text.strip():
        text = "<empty document>"

    return text

async def extract_text_with_confidence(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None
) -> Dict:
    """
    Extract text and return confidence metrics.
    Always returns a dictionary, even if extraction fails.
    """
    text = await extract_text(path, config, dict_manager)

    # Simple confidence estimation
    try:
        confidence = estimate_text_quality(text)
    except Exception as e:
        LOG.warning("Failed to estimate confidence: %s", e)
        confidence = 0.0

    warnings = []
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        warnings.append("Low OCR confidence detected")

    # Determine if OCR method was used
    is_ocr = path.suffix.lower() in {'.pdf', '.png', '.jpg', '.jpeg'}

    return {
        "text": text,
        "confidence": confidence,
        "method": "ocr" if is_ocr else "direct",
        "warnings": warnings
    }
