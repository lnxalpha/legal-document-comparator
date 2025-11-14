"""
Comparison Engine Package
Smart document comparison with semantic understanding
"""

from .text_extractor import extract_text, extract_with_confidence
from .smart_chunker import chunk_into_sentences, get_statistics
from .semantic_matcher import match_documents
from .report_generator import generate_report, generate_html_report

__version__ = "1.0.0"

__all__ = [
    "extract_text",
    "extract_with_confidence",
    "chunk_into_sentences",
    "get_statistics",
    "match_documents",
    "generate_report",
    "generate_html_report"
]
