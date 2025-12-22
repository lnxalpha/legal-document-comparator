"""
Decision Engine Module
Attributes system decisions to differences with reasoning (Phase 5)
"""

from typing import Tuple, Dict
import logging

LOG = logging.getLogger(__name__)


def decide_action(
    classification: str,
    severity: str,
    similarity: float,
    diff_stats: Dict = None
) -> Tuple[str, str, float]:
    """
    Determine system decision for a difference with reasoning.
    
    Args:
        classification: Type of difference (ocr_error, formatting_only, etc.)
        severity: Severity level (low, medium, high)
        similarity: Semantic similarity score (0.0 - 1.0)
        diff_stats: Optional detailed diff statistics
    
    Returns:
        Tuple of (decision, rationale, confidence)
        - decision: "accept", "flag", "needs_review"
        - rationale: Human-readable explanation
        - confidence: 0.0 - 1.0
    """
    
    # ========== AUTO-ACCEPT CASES ==========
    
    # Exact matches
    if classification == "exact_match":
        return (
            "accept",
            "Text is identical in both documents.",
            1.0
        )
    
    # Formatting-only changes
    if classification in ["formatting_only", "number_formatting", "citation_format"]:
        return (
            "accept",
            f"Only formatting differs. Content is semantically identical. "
            f"({classification.replace('_', ' ')})",
            0.95
        )
    
    # Minor OCR errors with high similarity
    if classification == "ocr_error" and similarity > 0.95:
        char_changes = diff_stats.get("char_changes", 0) if diff_stats else 0
        return (
            "accept",
            f"Minor OCR character recognition error detected. "
            f"Semantic meaning preserved. ({char_changes} character(s) affected)",
            0.90
        )
    
    # ========== NEEDS REVIEW CASES ==========
    
    # OCR errors with lower similarity
    if classification == "ocr_error" and 0.85 <= similarity <= 0.95:
        return (
            "needs_review",
            "Possible OCR error, but similarity is moderate. "
            "Manual verification recommended to ensure accuracy.",
            0.70
        )
    
    # Minor differences
    if classification == "minor_difference" and similarity > 0.90:
        return (
            "needs_review",
            "Text is very similar but not identical. "
            "Review to determine if difference is acceptable.",
            0.75
        )
    
    # Rewordings with high similarity
    if classification == "rewording" and similarity > 0.85:
        return (
            "needs_review",
            "Content appears reworded but semantically similar. "
            "Verify that meaning is preserved.",
            0.70
        )
    
    # Merged sentences (structural change)
    if classification == "sentence_merge":
        return (
            "needs_review",
            "Sentence boundaries differ between documents. "
            "Content may be identical but structured differently.",
            0.80
        )
    
    # ========== FLAG CASES (High Priority) ==========
    
    # High severity automatically flagged
    if severity == "high":
        return (
            "flag",
            "Significant difference detected with high severity. "
            "Critical manual review required before acceptance.",
            0.85
        )
    
    # Low similarity indicates substantial change
    if similarity < 0.75:
        return (
            "flag",
            f"Low semantic similarity ({similarity:.1%}) indicates substantial textual changes. "
            "Content verification essential.",
            0.90
        )
    
    # Significant classification
    if classification == "significant":
        return (
            "flag",
            "Substantial content difference detected. "
            "May represent intentional change or data loss.",
            0.85
        )
    
    # Missing content (one-sided)
    if classification == "addition":
        return (
            "flag",
            "Content appears in one document but not the other. "
            "Verify if this is an addition, deletion, or extraction error.",
            0.90
        )
    
    # ========== FALLBACK ==========
    
    # Medium severity, moderate similarity
    if severity == "medium":
        return (
            "needs_review",
            f"Medium severity difference ({classification.replace('_', ' ')}). "
            "Manual review recommended to assess impact.",
            0.65
        )
    
    # Default: needs review
    LOG.warning(
        f"Unhandled decision case: classification={classification}, "
        f"severity={severity}, similarity={similarity}"
    )
    return (
        "needs_review",
        "Difference type requires manual assessment to determine appropriate action.",
        0.50
    )


def generate_detailed_rationale(
    classification: str,
    diff: Dict,
    decision: str
) -> str:
    """
    Generate detailed, legally-oriented rationale for a decision.
    
    Args:
        classification: Type of difference
        diff: Full difference dictionary
        decision: System decision
    
    Returns:
        Detailed rationale string
    """
    base_rationale = ""
    
    # Context
    position1 = diff.get("position1", "N/A")
    position2 = diff.get("position2", "N/A")
    similarity = diff.get("similarity", 0.0)
    
    base_rationale += f"**Position:** Doc1: {position1}, Doc2: {position2}\n"
    base_rationale += f"**Similarity:** {similarity:.1%}\n"
    base_rationale += f"**Classification:** {classification.replace('_', ' ').title()}\n\n"
    
    # Type-specific analysis
    if classification == "ocr_error":
        base_rationale += (
            "**Analysis:** This appears to be an optical character recognition (OCR) error "
            "from document scanning. Common OCR mistakes include confusing similar-looking "
            "characters (e.g., 'O' and '0', 'l' and '1'). "
        )
        if decision == "accept":
            base_rationale += (
                "Given the high semantic similarity, this is likely a scanning artifact "
                "that does not affect legal meaning."
            )
        else:
            base_rationale += (
                "While likely an OCR error, manual verification against the original "
                "physical document is recommended to ensure accuracy."
            )
    
    elif classification == "formatting_only":
        base_rationale += (
            "**Analysis:** Only formatting differs (capitalization, punctuation, spacing). "
            "The actual content and legal meaning are identical. "
            "This typically results from different document formatting standards or "
            "conversion between file formats."
        )
    
    elif classification == "sentence_merge":
        base_rationale += (
            "**Analysis:** Sentence boundaries are detected differently between documents. "
            "This commonly occurs when:\n"
            "- OCR merges multiple sentences without proper punctuation\n"
            "- Different sentence splitting algorithms are used\n"
            "- Original document had ambiguous sentence boundaries\n\n"
            "Content may be identical despite structural difference."
        )
    
    elif classification == "significant":
        base_rationale += (
            "**Analysis:** Substantial content difference detected. This may indicate:\n"
            "- Intentional amendment or revision\n"
            "- Data loss during conversion/scanning\n"
            "- Different document versions\n\n"
            "**Recommendation:** Compare against authoritative source document."
        )
    
    elif classification == "addition":
        base_rationale += (
            "**Analysis:** Content appears in one document but not the other. Possible causes:\n"
            "- Content was added or deleted between versions\n"
            "- OCR failed to extract this section from one document\n"
            "- Documents represent different stages of the same text\n\n"
            "**Recommendation:** Verify against original source to determine cause."
        )
    
    # Suggestions
    if diff.get("suggestions"):
        base_rationale += f"\n**Suggestions:**\n"
        for i, suggestion in enumerate(diff["suggestions"][:3], 1):
            base_rationale += f"{i}. {suggestion}\n"
    
    return base_rationale.strip()


def assess_legal_risk(
    flagged_items: list,
    summary_stats: Dict
) -> Tuple[str, str]:
    """
    Assess overall legal risk level of differences.
    
    Returns:
        Tuple of (risk_level, risk_explanation)
        - risk_level: "low", "medium", "high", "critical"
        - risk_explanation: Detailed explanation
    """
    total_diffs = len(flagged_items)
    
    if total_diffs == 0:
        return (
            "low",
            "No significant differences detected. Documents appear identical."
        )
    
    # Count by severity
    high_severity = sum(1 for item in flagged_items if item.get("severity") == "high")
    medium_severity = sum(1 for item in flagged_items if item.get("severity") == "medium")
    
    # Count by type
    significant_changes = sum(
        1 for item in flagged_items 
        if item.get("classification") in ["significant", "addition"]
    )
    
    formatting_only = sum(
        1 for item in flagged_items 
        if item.get("classification") in ["formatting_only", "number_formatting", "citation_format"]
    )
    
    # Risk assessment logic
    if high_severity > 0 or significant_changes > 2:
        risk_level = "high"
        explanation = (
            f"**High risk detected:** {high_severity} high-severity difference(s) "
            f"and {significant_changes} significant content change(s) found. "
            "These differences may affect legal interpretation or enforceability. "
            "Thorough manual review by legal counsel strongly recommended."
        )
    
    elif medium_severity > 3 or significant_changes > 0:
        risk_level = "medium"
        explanation = (
            f"**Medium risk detected:** {medium_severity} medium-severity difference(s) found. "
            "While most differences may be minor, manual review is recommended "
            "to ensure no critical clauses have been altered."
        )
    
    elif formatting_only / total_diffs > 0.8:
        risk_level = "low"
        explanation = (
            f"**Low risk:** Most differences ({formatting_only}/{total_diffs}) are formatting-only. "
            "Content appears substantively identical. "
            "Spot-check review recommended for peace of mind."
        )
    
    else:
        risk_level = "low"
        explanation = (
            f"**Low risk:** {total_diffs} minor difference(s) detected, "
            "primarily OCR errors or minor variations. "
            "Quick review recommended to confirm acceptability."
        )
    
    return (risk_level, explanation)


# Testing
if __name__ == "__main__":
    # Test decision logic
    test_cases = [
        ("exact_match", "none", 1.0),
        ("formatting_only", "very_low", 1.0),
        ("ocr_error", "low", 0.96),
        ("ocr_error", "low", 0.88),
        ("significant", "high", 0.65),
        ("minor_difference", "low", 0.92)
    ]
    
    print("Decision Engine Test Cases:")
    print("=" * 80)
    
    for classification, severity, similarity in test_cases:
        decision, rationale, confidence = decide_action(
            classification, severity, similarity
        )
        
        print(f"\nInput: {classification} | {severity} | {similarity:.2f}")
        print(f"Decision: {decision.upper()} (confidence: {confidence:.2f})")
        print(f"Rationale: {rationale}")
        print("-" * 80)
