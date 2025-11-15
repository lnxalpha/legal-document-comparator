"""
Comparison Engine Package
Smart document comparison with semantic understanding
Lightweight version for 512MB RAM limit
"""

from .text_extractor import extract_text, extract_with_confidence
from .smart_chunker import chunk_into_sentences, get_statistics

# Use lightweight matcher for memory efficiency
try:
    from .semantic_matcher_lite import (
        match_documents,
        analyze_match_quality,
        find_potential_reorderings,
        suggest_corrections
    )
except ImportError:
    # Fallback to heavy version if lite not available
    from .semantic_matcher import (
        match_documents,
        analyze_match_quality,
        find_potential_reorderings,
        suggest_corrections
    )

from .report_generator import generate_report, generate_html_report

__version__ = "1.0.0-lite"

__all__ = [
    "extract_text",
    "extract_with_confidence",
    "chunk_into_sentences",
    "get_statistics",
    "match_documents",
    "generate_report",
    "generate_html_report"
]
