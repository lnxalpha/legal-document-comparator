"""Public API for unified_extractor
Keep this stable so existing imports continue to work.
"""
from pathlib import Path
from .extractor import extract_text, extract_text_with_confidence

__version__ = "4.1.0"
__all__ = ["extract_text", "extract_text_with_confidence"]
