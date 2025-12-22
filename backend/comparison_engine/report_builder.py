"""
Report Builder Service
Constructs structured reports from comparison results (Phase 5)
"""

from typing import Dict, List, Optional
from datetime import datetime
from uuid import uuid4
import logging

from comparison_engine.report_schema import (
    ComparisonReport,
    FlaggedItem,
    SummaryStats,
    calculate_summary_stats,
    generate_overall_assessment
)
from comparison_engine.decision_engine import (
    decide_action,
    generate_detailed_rationale,
    assess_legal_risk
)

LOG = logging.getLogger(__name__)

def normalize_user_decisions(user_decisions: Dict) -> Dict[int, Dict]:
    """
    Normalize user decisions into:
    { int_index: {"decision": str, "note": Optional[str]} }
    """
    normalized = {}

    for k, v in user_decisions.items():
        try:
            idx = int(k)
        except (TypeError, ValueError):
            continue

        if isinstance(v, dict):
            normalized[idx] = {
                "decision": v.get("decision"),
                "note": v.get("note")
            }
        else:
            normalized[idx] = {
                "decision": v,
                "note": None
            }

    return normalized

def build_comparison_report(
    comparison_result: Dict,
    file1_name: str,
    file2_name: str,
    user_decisions: Optional[Dict] = None
) -> ComparisonReport:
    """
    Build a complete ComparisonReport from raw comparison data.

    Args:
        comparison_result: Output from match_documents + generate_report
        file1_name: Name of reference document
        file2_name: Name of target document
        user_decisions: Optional dict of user decisions {diff_index: {"decision": "accept", "note": "..."}}

    Returns:
        ComparisonReport object ready for export
    """

    LOG.info(f"Building report for {file1_name} vs {file2_name}")

    # Generate unique report ID
    report_id = uuid4().hex[:12]

    # Calculate summary statistics
    summary_stats = calculate_summary_stats(comparison_result)

    # Build flagged items with decisions
    normalized_decisions = normalize_user_decisions(user_decisions or {})

    flagged_items = build_flagged_items(
        comparison_result["differences"],
        normalized_decisions
    )

    summary_stats.user_accepted = sum(
        1 for d in normalized_decisions.values() if d["decision"] == "accept"
    )
    summary_stats.user_flagged = sum(
        1 for d in normalized_decisions.values() if d["decision"] == "flag"
    )
    summary_stats.user_skipped = sum(
        1 for d in normalized_decisions.values() if d["decision"] == "skip"
    )


    # Generate overall assessment
    assessment = generate_overall_assessment(summary_stats)
    verdict_message = comparison_result["verdict"]["message"]

    # Build recommendations
    recommendations = comparison_result.get("recommendations", [])

    # Add legal risk assessment
    risk_level, risk_explanation = assess_legal_risk(
        flagged_items,
        summary_stats.to_dict()
    )
    recommendations.insert(0, f"**Legal Risk Assessment:** {risk_level.upper()}\n{risk_explanation}")

    # Create report
    report = ComparisonReport(
        report_id=report_id,
        generated_at=datetime.utcnow(),
        reference_document=file1_name,
        target_document=file2_name,
        summary_stats=summary_stats,
        overall_assessment=assessment,
        verdict_message=verdict_message,
        flagged_items=flagged_items,
        recommendations=recommendations,
        raw_data=comparison_result  # Store for potential regeneration
    )

    LOG.info(
        f"Report {report_id} created: {len(flagged_items)} flagged items, "
        f"{summary_stats.overall_match}% match"
    )

    return report


def build_flagged_items(
    differences: List[Dict],
    user_decisions: Dict
) -> List[FlaggedItem]:
    """
    Convert difference list to FlaggedItem objects with decisions.

    Args:
        differences: List of difference dicts from generate_report
        user_decisions: Dict of user overrides {index: {"decision": "accept", "note": "..."}}

    Returns:
        List of FlaggedItem objects
    """

    flagged_items = []

    for idx, diff in enumerate(differences):
        # Determine system decision
        decision, rationale, confidence = decide_action(
            classification=diff["classification"],
            severity=diff["severity"],
            similarity=diff["similarity"],
            diff_stats=diff.get("diff_stats")
        )

        # Generate detailed rationale
        detailed_rationale = generate_detailed_rationale(
            diff["classification"],
            diff,
            decision
        )

        # Check for user override
        user_decision = None
        user_note = None
        if idx in user_decisions:
            user_decision = user_decisions[idx].get("decision")
            user_note = user_decisions[idx].get("note")

        # Create flagged item
        item = FlaggedItem(
            id=f"{uuid4().hex[:8]}",
            reference_text=diff.get("sentence1") or "N/A",
            target_text=diff.get("sentence2") or "N/A",
            difference_type=diff["classification"],
            severity=diff["severity"],
            system_decision=decision,
            rationale=detailed_rationale,
            confidence=confidence,
            position1=diff.get("position1"),
            position2=diff.get("position2"),
            similarity=diff["similarity"],
            diff_html1=diff.get("diff_html1"),
            diff_html2=diff.get("diff_html2"),
            suggestions=diff.get("suggestions", []),
            user_decision=user_decision,
            user_note=user_note
        )

        flagged_items.append(item)

    LOG.debug(f"Built {len(flagged_items)} flagged items")
    return flagged_items


def update_report_with_user_decisions(
    report: ComparisonReport,
    user_decisions: Dict
) -> ComparisonReport:
    """
    Update an existing report with user decisions.

    Args:
        report: Existing ComparisonReport
        user_decisions: Dict mapping item IDs to decisions
            {
                "item_id_1": {"decision": "accept", "note": "Approved by counsel"},
                "item_id_2": {"decision": "flag", "note": "Needs clarification"}
            }

    Returns:
        Updated ComparisonReport
    """

    # Update each flagged item
    for item in report.flagged_items:
        if item.id in user_decisions:
            decision_data = user_decisions[item.id]
            item.user_decision = decision_data.get("decision")
            item.user_note = decision_data.get("note")

    # Recalculate user decision stats
    report.summary_stats.user_accepted = sum(
        1 for item in report.flagged_items if item.user_decision == "accept"
    )
    report.summary_stats.user_flagged = sum(
        1 for item in report.flagged_items if item.user_decision == "flag"
    )
    report.summary_stats.user_skipped = sum(
        1 for item in report.flagged_items if item.user_decision == "skip"
    )

    LOG.info(
        f"Report {report.report_id} updated with user decisions: "
        f"{report.summary_stats.user_accepted} accepted, "
        f"{report.summary_stats.user_flagged} flagged"
    )

    return report


def generate_executive_summary(report: ComparisonReport) -> str:
    """
    Generate a concise executive summary for the report.

    Returns:
        Markdown-formatted executive summary
    """

    stats = report.summary_stats

    # Determine recommendation
    if stats.high_severity == 0 and stats.overall_match >= 95:
        recommendation = "✅ **Documents are substantially identical.** Minor differences detected do not affect legal meaning."
    elif stats.high_severity > 0:
        recommendation = f"⚠️ **Manual review required.** {stats.high_severity} high-severity difference(s) detected that may affect legal interpretation."
    elif stats.overall_match >= 90:
        recommendation = "⚠️ **Review recommended.** Documents are very similar with minor variations. Verify differences are acceptable."
    else:
        recommendation = "❌ **Significant differences detected.** Documents may not be equivalent. Detailed review essential."

    summary = f"""
# Executive Summary

**Overall Match:** {stats.overall_match}% | **Assessment:** {report.overall_assessment.replace('_', ' ').title()}

{recommendation}

## Key Metrics

- **Total Differences:** {stats.total_differences}
  - High Severity: {stats.high_severity}
  - Medium Severity: {stats.medium_severity}
  - Low Severity: {stats.low_severity}

- **Difference Types:**
  - Formatting Only: {stats.formatting_only}
  - OCR Errors: {stats.ocr_errors}
  - Minor Differences: {stats.minor_differences}
  - Significant Changes: {stats.significant_differences}

- **System Analysis:**
  - Auto-Accepted: {stats.system_accepted}
  - Flagged for Review: {stats.system_flagged}
  - Needs Manual Review: {stats.needs_review}
"""

    if stats.user_accepted + stats.user_flagged + stats.user_skipped > 0:
        summary += f"""
- **User Decisions:**
  - Accepted: {stats.user_accepted}
  - Flagged: {stats.user_flagged}
  - Skipped: {stats.user_skipped}
"""

    summary += f"""
## Verdict

{report.verdict_message}

**Generated:** {report.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Report ID:** {report.report_id}
"""

    return summary.strip()


def save_report(report: ComparisonReport, output_path: str):
    """
    Save report as JSON file.

    Args:
        report: ComparisonReport to save
        output_path: Path to save JSON file
    """
    import json
    from pathlib import Path

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report.to_dict(), f, indent=2)

    LOG.info(f"Report saved to {output_path}")


def load_report(input_path: str) -> ComparisonReport:
    """
    Load report from JSON file.

    Args:
        input_path: Path to JSON file

    Returns:
        ComparisonReport object
    """
    import json
    from pathlib import Path

    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Report not found: {input_path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    report = ComparisonReport.from_dict(data)
    LOG.info(f"Report loaded from {input_path}")

    return report


# Testing
if __name__ == "__main__":
    # Mock comparison result for testing
    mock_comparison = {
        "summary": {
            "overall_match": 94.2,
            "total_sentences_doc1": 100,
            "total_sentences_doc2": 98,
            "matched_sentences": 95,
            "exact_matches": 90,
            "minor_differences": 5,
            "significant_differences": 3,
            "formatting_only": 2,
            "ocr_errors": 3,
            "avg_similarity": 0.942
        },
        "verdict": {
            "status": "very_similar",
            "message": "Documents are very similar with minor differences",
            "color": "green"
        },
        "differences": [
            {
                "classification": "ocr_error",
                "severity": "low",
                "position1": 5,
                "position2": 5,
                "sentence1": "WAHAB O. ONAKOYA",
                "sentence2": "WAHAB OG. ONAKOYA",
                "similarity": 0.962,
                "suggestions": ["Possible OCR error: 'O.' → 'OG.'"]
            },
            {
                "classification": "formatting_only",
                "severity": "very_low",
                "position1": 10,
                "position2": 10,
                "sentence1": "This is a test.",
                "sentence2": "THIS IS A TEST.",
                "similarity": 1.0,
                "suggestions": ["Only case differs"]
            }
        ],
        "recommendations": [
            "2 difference(s) are formatting-only. These can be safely ignored.",
            "3 likely OCR errors detected. Consider rescanning at higher resolution."
        ]
    }

    # Build report
    report = build_comparison_report(
        mock_comparison,
        "contract_original.pdf",
        "contract_signed.jpg"
    )

    # Print executive summary
    print(generate_executive_summary(report))
    print("\n" + "="*80 + "\n")

    # Print flagged items
    print(f"Flagged Items: {len(report.flagged_items)}")
    for item in report.flagged_items:
        print(f"\n- {item.difference_type} | {item.severity} | Decision: {item.system_decision}")
        print(f"  Confidence: {item.confidence:.2f}")
        print(f"  Rationale: {item.rationale[:100]}...")
