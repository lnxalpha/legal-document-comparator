# unified_extractor/utils.py
"""
Utility functions for text quality estimation.
NO extraction logic here - only helpers.
"""
import re
import logging

LOG = logging.getLogger(__name__)

# Import only from config (no circular dependencies)
try:
    from .config import QUALITY_ERROR_MULTIPLIER
except ImportError:
    QUALITY_ERROR_MULTIPLIER = 10.0  # Fallback


def estimate_text_quality(text: str) -> float:
    """
    Estimate OCR quality based on error patterns.

    Args:
        text: Input text to analyze

    Returns:
        Quality score between 0.0 (poor) and 1.0 (excellent)
    """
    if not text:
        return 0.0

    # Count error indicators
    weird_chars = len(re.findall(r"[^\w\s.,!?;:'\"()-]", text))
    isolated_chars = len(re.findall(r"\s\w\s", text))
    mixed_alphanum = len(re.findall(r"\d[a-zA-Z]|[a-zA-Z]\d", text))

    total_errors = weird_chars + isolated_chars + mixed_alphanum
    error_rate = total_errors / max(len(text), 1)

    quality = max(0.0, 1.0 - (QUALITY_ERROR_MULTIPLIER * error_rate))

    return quality
