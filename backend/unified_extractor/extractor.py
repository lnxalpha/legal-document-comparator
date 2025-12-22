# unified_extractor/extractor.py
"""Robust top-level document extraction orchestration with provenance tracking."""
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
    repair_sentence_boundaries,
    clean_ocr_artifacts
)

LOG = logging.getLogger(__name__)


# ========== EXTRACTION FUNCTIONS ==========

async def extract_from_txt(path: Path) -> Dict:
    """Extract from text file with metadata."""
    try:
        text = path.read_text(encoding='utf-8')
        return {
            "text": text,
            "method": "direct",
            "confidence": 1.0,
            "lines": [],
            "warnings": []
        }
    except Exception as e:
        LOG.warning("Failed to read TXT %s: %s", path.name, e)
        return {
            "text": "<unreadable text file>",
            "method": "failed",
            "confidence": 0.0,
            "lines": [],
            "warnings": [f"Failed to read file: {e}"]
        }


async def extract_from_image(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None
) -> Dict:
    """Extract from image with provenance."""
    try:
        from .legal_ocr import ocr_legal_image_path
        use_gpu = getattr(config, "use_gpu", False) if config else False
        result = ocr_legal_image_path(path, use_gpu=use_gpu)

        warnings = []
        if result["overall_confidence"] < 0.7:
            warnings.append("Low OCR confidence detected")

        return {
            "text": result["text"],
            "method": "ocr",
            "confidence": result["overall_confidence"],
            "lines": result["lines"],
            "warnings": warnings,
            "ocr_details": {
                "ocr_method": result.get("method", "unknown"),
                "line_count": len(result["lines"])
            }
        }
    except Exception as e:
        LOG.warning("Failed to OCR image %s: %s", path.name, e)
        return {
            "text": "<unreadable image>",
            "method": "failed",
            "confidence": 0.0,
            "lines": [],
            "warnings": [f"OCR failed: {e}"]
        }


async def extract_from_pdf(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None,
    parallel: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict:
    """Extract from PDF with provenance."""
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
        page_results = [None] * total
        all_lines = []

        def process_page(idx: int, page) -> Dict:
            """Process single page and return provenance."""
            try:
                # Try text extraction first
                text = page.get_text()
                if text.strip():
                    return {
                        "text": text,
                        "method": "direct",
                        "confidence": 1.0,
                        "lines": [],
                        "page": idx
                    }

                # Fallback to OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                ocr_result = ocr_legal_array(arr, dict_manager=dict_manager)

                return {
                    "text": ocr_result["text"],
                    "method": "ocr",
                    "confidence": ocr_result["overall_confidence"],
                    "lines": ocr_result["lines"],
                    "page": idx
                }
            except Exception as e:
                LOG.warning("Failed OCR on PDF page %d: %s", idx, e)
                return {
                    "text": "<unreadable page>",
                    "method": "failed",
                    "confidence": 0.0,
                    "lines": [],
                    "page": idx
                }

        if parallel:
            loop = asyncio.get_running_loop()
            tasks = []
            for i, page in enumerate(doc):
                tasks.append(loop.run_in_executor(None, process_page, i, page))
                if progress_callback:
                    progress_callback(i + 1, total)

            results = await asyncio.gather(*tasks)
            for i, result in enumerate(results):
                page_results[i] = result
        else:
            for i, page in enumerate(doc):
                page_results[i] = process_page(i, page)
                if progress_callback:
                    progress_callback(i + 1, total)

        doc.close()

        # Combine all pages
        combined_text = "\n\n".join(
            str(r["text"]) if r and r["text"] else "<unreadable page>"
            for r in page_results
        )

        # Collect all line metadata
        for page_result in page_results:
            if page_result and page_result.get("lines"):
                for line in page_result["lines"]:
                    line["page"] = page_result["page"]
                    all_lines.append(line)

        # Calculate overall confidence
        confidences = [r["confidence"] for r in page_results if r and r["confidence"] > 0]
        overall_conf = sum(confidences) / len(confidences) if confidences else 0.0

        # Warnings
        warnings = []
        if overall_conf < 0.7:
            warnings.append("Low overall OCR confidence")

        ocr_pages = sum(1 for r in page_results if r and r["method"] == "ocr")
        if ocr_pages > 0:
            warnings.append(f"{ocr_pages}/{total} pages required OCR")

        return {
            "text": combined_text,
            "method": "mixed" if ocr_pages > 0 and ocr_pages < total else ("ocr" if ocr_pages == total else "direct"),
            "confidence": overall_conf,
            "lines": all_lines,
            "warnings": warnings,
            "ocr_details": {
                "total_pages": total,
                "ocr_pages": ocr_pages,
                "direct_pages": total - ocr_pages
            }
        }

    except Exception as e:
        LOG.warning("Failed to extract PDF %s: %s", path.name, e)
        return {
            "text": "<unreadable PDF>",
            "method": "failed",
            "confidence": 0.0,
            "lines": [],
            "warnings": [f"PDF extraction failed: {e}"]
        }


def extract_from_doc(path: Path) -> Dict:
    """Extract from .doc file."""
    try:
        import mammoth
        with open(path, "rb") as f:
            text = mammoth.extract_raw_text(f).value
            return {
                "text": text if text.strip() else "<empty DOC>",
                "method": "direct",
                "confidence": 1.0,
                "lines": [],
                "warnings": []
            }
    except Exception as e:
        LOG.warning("Failed to extract DOC %s: %s", path.name, e)
        return {
            "text": "<unreadable DOC>",
            "method": "failed",
            "confidence": 0.0,
            "lines": [],
            "warnings": [f"DOC extraction failed: {e}"]
        }


async def extract_from_docx(path: Path) -> Dict:
    """Extract from .docx file."""
    try:
        from docx import Document
        doc = Document(path)
        texts = [str(p.text) for p in doc.paragraphs if p.text]
        return {
            "text": "\n".join(texts) if texts else "<empty DOCX>",
            "method": "direct",
            "confidence": 1.0,
            "lines": [],
            "warnings": []
        }
    except Exception as e:
        LOG.warning("Failed to extract DOCX %s: %s", path.name, e)
        return {
            "text": "<unreadable DOCX>",
            "method": "failed",
            "confidence": 0.0,
            "lines": [],
            "warnings": [f"DOCX extraction failed: {e}"]
        }


# ========== PUBLIC API ==========

async def extract_text(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """
    Extract text from document (legacy API - returns string only).

    For provenance metadata, use extract_text_with_confidence().
    """
    result = await extract_text_with_confidence(path, config, dict_manager, progress_callback)
    return result["text"]


async def extract_text_with_confidence(
    path: Path,
    config: Optional[OCRConfig] = None,
    dict_manager: Optional[DictionaryManager] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict:
    """
    Extract text and return full provenance metadata.

    Returns:
        {
            "text": "extracted text",
            "confidence": 0.85,
            "method": "ocr" | "direct" | "mixed" | "failed",
            "lines": [
                {
                    "text": "line text",
                    "confidence": 0.85,
                    "line_id": 0,
                    "ocr_method": "tesseract",
                    "bbox": (y1, y2, x1, x2),
                    "page": 0  # for PDFs
                },
                ...
            ],
            "warnings": ["Low OCR confidence", ...],
            "ocr_details": {
                "total_pages": 10,
                "ocr_pages": 3,
                ...
            }
        }
    """
    validate_file_path(path)

    if dict_manager is None:
        dict_manager = DictionaryManager.get_instance()
    if config is None:
        config = OCRConfig()

    suffix = path.suffix.lower()

    # Route to appropriate extractor
    if suffix == '.pdf':
        result = await extract_from_pdf(path, config, dict_manager, progress_callback=progress_callback)
    elif suffix in {'.png', '.jpg', '.jpeg'}:
        result = await extract_from_image(path, config, dict_manager)
    elif suffix == '.docx':
        result = await extract_from_docx(path)
    elif suffix == '.doc':
        result = extract_from_doc(path)
    elif suffix == '.txt':
        result = await extract_from_txt(path)
    else:
        LOG.warning("Unsupported file type: %s", suffix)
        result = {
            "text": "<unsupported file type>",
            "method": "failed",
            "confidence": 0.0,
            "lines": [],
            "warnings": [f"Unsupported file type: {suffix}"]
        }

    text = result["text"]

    # Apply corrections safely
    try:
        text = apply_ocr_corrections(text, dict_manager)
        text = enhance_with_legal_context(text, dict_manager)

        # PHASE 1 FIX: Repair sentence boundaries
        text = repair_sentence_boundaries(text)
        text = clean_ocr_artifacts(text)

    except Exception as e:
        LOG.warning("Failed to apply corrections: %s", e)
        result["warnings"].append(f"Correction failed: {e}")

    # Ensure text is never empty
    if not text.strip():
        text = "<empty document>"

    result["text"] = text

    # Add quality warnings
    if result["confidence"] < MIN_CONFIDENCE_THRESHOLD:
        if "Low OCR confidence detected" not in result["warnings"]:
            result["warnings"].append("Low OCR confidence detected")

    return result
