"""
Report Schema Module
Canonical data model for comparison reports (Phase 5)
"""

from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json


@dataclass
class FlaggedItem:
    """Represents a single flagged difference with decision tracking."""
    
    id: str
    reference_text: str
    target_text: str
    difference_type: str  # missing, altered, reordered, OCR_noise, formatting
    severity: str  # low, medium, high
    system_decision: str  # accept, flag, needs_review
    rationale: str  # Why the system made this decision
    confidence: float  # 0.0 - 1.0
    
    # Position tracking
    position1: Optional[int] = None
    position2: Optional[int] = None
    
    # Analysis metadata
    similarity: float = 0.0
    diff_html1: Optional[str] = None
    diff_html2: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    
    # User decision (overrides system)
    user_decision: Optional[str] = None  # accept, flag, skip
    user_note: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "reference_text": self.reference_text,
            "target_text": self.target_text,
            "difference_type": self.difference_type,
            "severity": self.severity,
            "system_decision": self.system_decision,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "position1": self.position1,
            "position2": self.position2,
            "similarity": self.similarity,
            "suggestions": self.suggestions,
            "user_decision": self.user_decision,
            "user_note": self.user_note
        }


@dataclass
class SummaryStats:
    """Aggregate statistics for the comparison."""
    
    total_sentences_doc1: int
    total_sentences_doc2: int
    matched_sentences: int
    exact_matches: int
    
    # Difference counts
    total_differences: int
    formatting_only: int
    ocr_errors: int
    minor_differences: int
    significant_differences: int
    
    # Severity breakdown
    high_severity: int
    medium_severity: int
    low_severity: int
    
    # Decision breakdown
    system_accepted: int
    system_flagged: int
    needs_review: int
    
    # User decisions (if available)
    user_accepted: int = 0
    user_flagged: int = 0
    user_skipped: int = 0
    
    # Quality metrics
    overall_match: float = 0.0
    avg_similarity: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_sentences_doc1": self.total_sentences_doc1,
            "total_sentences_doc2": self.total_sentences_doc2,
            "matched_sentences": self.matched_sentences,
            "exact_matches": self.exact_matches,
            "total_differences": self.total_differences,
            "formatting_only": self.formatting_only,
            "ocr_errors": self.ocr_errors,
            "minor_differences": self.minor_differences,
            "significant_differences": self.significant_differences,
            "high_severity": self.high_severity,
            "medium_severity": self.medium_severity,
            "low_severity": self.low_severity,
            "system_accepted": self.system_accepted,
            "system_flagged": self.system_flagged,
            "needs_review": self.needs_review,
            "user_accepted": self.user_accepted,
            "user_flagged": self.user_flagged,
            "user_skipped": self.user_skipped,
            "overall_match": self.overall_match,
            "avg_similarity": self.avg_similarity
        }


@dataclass
class ComparisonReport:
    """Complete comparison report with all metadata."""
    
    report_id: str
    generated_at: datetime
    
    # Document metadata
    reference_document: str
    target_document: str
    
    # Summary
    summary_stats: SummaryStats
    overall_assessment: str  # "identical", "minor_differences", "significant_differences"
    verdict_message: str
    
    # Detailed differences
    flagged_items: List[FlaggedItem]
    
    # Recommendations
    recommendations: List[str]
    
    # Optional: Raw comparison data for regeneration
    raw_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "reference_document": self.reference_document,
            "target_document": self.target_document,
            "summary_stats": self.summary_stats.to_dict(),
            "overall_assessment": self.overall_assessment,
            "verdict_message": self.verdict_message,
            "flagged_items": [item.to_dict() for item in self.flagged_items],
            "recommendations": self.recommendations
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ComparisonReport':
        """Deserialize from dictionary."""
        summary_stats = SummaryStats(**data["summary_stats"])
        flagged_items = [
            FlaggedItem(**item) for item in data["flagged_items"]
        ]
        
        return cls(
            report_id=data["report_id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            reference_document=data["reference_document"],
            target_document=data["target_document"],
            summary_stats=summary_stats,
            overall_assessment=data["overall_assessment"],
            verdict_message=data["verdict_message"],
            flagged_items=flagged_items,
            recommendations=data["recommendations"]
        )
    
    def get_critical_items(self) -> List[FlaggedItem]:
        """Get high-severity flagged items."""
        return [
            item for item in self.flagged_items
            if item.severity == "high" or item.user_decision == "flag"
        ]
    
    def get_accepted_items(self) -> List[FlaggedItem]:
        """Get accepted differences."""
        return [
            item for item in self.flagged_items
            if item.user_decision == "accept" or 
               (item.user_decision is None and item.system_decision == "accept")
        ]
    
    def get_pending_review(self) -> List[FlaggedItem]:
        """Get items still needing review."""
        return [
            item for item in self.flagged_items
            if item.user_decision is None and item.system_decision == "needs_review"
        ]


# Helper functions for report creation
def calculate_summary_stats(comparison_data: Dict) -> SummaryStats:
    """Extract summary statistics from comparison data."""
    summary = comparison_data["summary"]
    differences = comparison_data["differences"]
    
    return SummaryStats(
        total_sentences_doc1=summary["total_sentences_doc1"],
        total_sentences_doc2=summary["total_sentences_doc2"],
        matched_sentences=summary["matched_sentences"],
        exact_matches=summary["exact_matches"],
        total_differences=len(differences),
        formatting_only=summary.get("formatting_only", 0),
        ocr_errors=summary.get("ocr_errors", 0),
        minor_differences=summary["minor_differences"],
        significant_differences=summary["significant_differences"],
        high_severity=sum(1 for d in differences if d["severity"] == "high"),
        medium_severity=sum(1 for d in differences if d["severity"] == "medium"),
        low_severity=sum(1 for d in differences if d["severity"] == "low" or d["severity"] == "very_low"),
        system_accepted=sum(1 for d in differences if d.get("system_decision") == "accept"),
        system_flagged=sum(1 for d in differences if d.get("system_decision") == "flag"),
        needs_review=sum(1 for d in differences if d.get("system_decision") == "needs_review"),
        overall_match=summary["overall_match"],
        avg_similarity=summary.get("avg_similarity", 0.0)
    )


def generate_overall_assessment(summary_stats: SummaryStats) -> str:
    """Determine overall document similarity assessment."""
    if summary_stats.overall_match >= 98:
        return "identical"
    elif summary_stats.overall_match >= 90:
        return "very_similar"
    elif summary_stats.overall_match >= 75:
        return "similar"
    elif summary_stats.overall_match >= 50:
        return "different"
    else:
        return "very_different"


# For testing
if __name__ == "__main__":
    # Example usage
    from uuid import uuid4
    
    test_item = FlaggedItem(
        id=uuid4().hex,
        reference_text="WAHAB O. ONAKOYA",
        target_text="WAHAB OG. ONAKOYA",
        difference_type="ocr_error",
        severity="low",
        system_decision="accept",
        rationale="Minor OCR character recognition error (O. vs OG.)",
        confidence=0.96,
        position1=5,
        position2=5,
        similarity=0.962,
        suggestions=["Likely OCR scanning artifact"]
    )
    
    print("Flagged Item:")
    print(json.dumps(test_item.to_dict(), indent=2))
