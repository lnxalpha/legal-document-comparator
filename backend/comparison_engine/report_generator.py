"""
Report Generation Module
Creates detailed comparison reports from match results
Phase 3: Added inline diffs, grouped differences, and enhanced visualization
"""

from typing import List, Dict
from comparison_engine.semantic_matcher import (
    classify_difference,
    analyze_match_quality,
    find_potential_reorderings,
    suggest_corrections
)
from comparison_engine.diff_utils import generate_smart_diff, get_diff_stats


from typing import Optional, Dict

def get_collapsed_explanation(sentence: Dict) -> Optional[str]:
    """
    Generate human-readable explanation for collapsed sentence blocks.
    """
    if not sentence:
        return None

    count = sentence.get("collapsed_count")
    if count and count > 1:
        return f"This block represents {count} collapsed name entries."

    return None


def generate_report(
    match_results: Dict,
    sentences1: List[Dict],
    sentences2: List[Dict]
) -> Dict:
    """
    Generate a comprehensive comparison report

    Phase 3: Now includes inline diffs and grouped differences

    Returns structured report with:
    - Overall statistics
    - Detailed differences with inline diffs
    - Grouped related differences
    - Quality analysis
    - Merged sentence detection
    - Recommendations
    """
    matches = match_results["matches"]
    only_in_doc1 = match_results["only_in_doc1"]
    only_in_doc2 = match_results["only_in_doc2"]
    merged_in_doc1 = match_results.get("merged_in_doc1", [])
    merged_in_doc2 = match_results.get("merged_in_doc2", [])
    match_score = match_results["match_score"]

    # Analyze match quality
    quality = analyze_match_quality(matches)

    # Find reorderings
    reorderings = find_potential_reorderings(matches)

    # Build difference list
    differences = []

    # 1. Non-exact matches
    for match in matches:
        if not match["exact_match"]:
            diff_type = classify_difference(match)

            # Check if this is a relocated sentence
            is_relocated = match.get("relocated", False)

            # PHASE 3: Generate inline diff
            diff1, diff2 = generate_smart_diff(
                match["sent1"]["text"],
                match["sent2"]["text"]
            )
            diff_stats = get_diff_stats(
                match["sent1"]["text"],
                match["sent2"]["text"]
            )

            explanation = (
                get_collapsed_explanation(match["sent1"])
                or get_collapsed_explanation(match["sent2"])
            )

            differences.append({
                "type": "relocated" if is_relocated else "mismatch",
                "classification": diff_type,
                "severity": get_severity(diff_type),
                "position1": match["index1"] + 1 if match.get("index1") is not None else None,
                "position2": match["index2"] + 1 if match.get("index2") is not None else None,
                "sentence1": match["sent1"]["text"],
                "sentence2": match["sent2"]["text"],
                "similarity": match["similarity"],
                "suggestions": suggest_corrections(match),
                "relocated": is_relocated,
                # ✅ ADD THESE
                "sent1_metadata": {
                    "confidence": match["sent1"].get("confidence"),
                    "ocr_method": match["sent1"].get("ocr_method"),
                    "source": match["sent1"].get("source")
                },
                "sent2_metadata": {
                    "confidence": match["sent2"].get("confidence"),
                    "ocr_method": match["sent2"].get("ocr_method"),
                    "source": match["sent2"].get("source")
                },

                # PHASE 3: Inline diffs
                "diff_html1": diff1,
                "diff_html2": diff2,
                "diff_stats": diff_stats,
                "explanation": explanation  # 🟢 NEW
            })

    # 2. PHASE 2: Merged sentences in doc2
    for merge_info in merged_in_doc2:
        source_sent = merge_info["source_sentence"]
        merged_sent = merge_info["merged_into"]
        merge_type = merge_info["merge_type"]

        explanation = (
            get_collapsed_explanation(source_sent)
            or get_collapsed_explanation(merged_sent)
        )

        differences.append({
            "type": "merged_in_doc2",
            "classification": "sentence_merge",
            "severity": "medium",
            "position1": source_sent["id"] + 1,
            "position2": merged_sent["id"] + 1,
            "sentence1": source_sent["text"],
            "sentence2": merged_sent["text"],
            "similarity": merge_info.get("similarity", 1.0),
            "suggestions": [
                f"This sentence from Doc1 appears merged into Doc2 position {merged_sent['id'] + 1}",
                f"Merge type: {merge_type}"
            ],
            "merge_type": merge_type,

            # PHASE 3: No inline diff for merges (not comparable)
            "diff_html1": None,
            "diff_html2": None,
            "explanation": explanation
        })

    # 3. PHASE 2: Merged sentences in doc1
    for merge_info in merged_in_doc1:
        source_sent = merge_info["source_sentence"]
        merged_sent = merge_info["merged_into"]
        merge_type = merge_info["merge_type"]

        differences.append({
            "type": "merged_in_doc1",
            "classification": "sentence_merge",
            "severity": "medium",
            "position1": merged_sent["id"] + 1,
            "position2": source_sent["id"] + 1,
            "sentence1": merged_sent["text"],
            "sentence2": source_sent["text"],
            "similarity": merge_info.get("similarity", 1.0),
            "suggestions": [
                f"This sentence from Doc2 appears merged into Doc1 position {merged_sent['id'] + 1}",
                f"Merge type: {merge_type}"
            ],
            "merge_type": merge_type,
            "diff_html1": None,
            "diff_html2": None
        })

    # 4. Sentences truly only in document 1 (after all checks)
    for sent in only_in_doc1:
        differences.append({
            "type": "missing_in_doc2",
            "classification": "addition",
            "severity": "high",
            "position1": sent["id"] + 1,
            "position2": None,
            "sentence1": sent["text"],
            "sentence2": None,
            "similarity": 0.0,
            "suggestions": ["This sentence appears in document 1 but not in document 2"],
            "diff_html1": None,
            "diff_html2": None,
            "explanation": get_collapsed_explanation(sent)
        })

    # 5. Sentences truly only in document 2 (after all checks)
    for sent in only_in_doc2:
        differences.append({
            "type": "missing_in_doc1",
            "classification": "addition",
            "severity": "high",
            "position1": None,
            "position2": sent["id"] + 1,
            "sentence1": None,
            "sentence2": sent["text"],
            "similarity": 0.0,
            "suggestions": ["This sentence appears in document 2 but not in document 1"],
            "diff_html1": None,
            "diff_html2": None,
            "explanation": get_collapsed_explanation(sent)
        })

    # PHASE 3: Group related differences
    grouped_differences = group_related_differences(differences)

    # Sort differences by position
    differences.sort(key=lambda d: (
        d["position1"] if d["position1"] is not None else float('inf'),
        d["position2"] if d["position2"] is not None else float('inf')
    ))

    # Generate summary
    summary = {
        "overall_match": round(match_score * 100, 2),  # Percentage
        "total_sentences_doc1": len(sentences1),
        "total_sentences_doc2": len(sentences2),
        "matched_sentences": len(matches),
        "exact_matches": quality["exact_matches"],
        "minor_differences": quality["minor_differences"],
        "significant_differences": quality["significant_differences"] + len(only_in_doc1) + len(only_in_doc2),
        "missing_in_doc1": len(only_in_doc2),
        "missing_in_doc2": len(only_in_doc1),
        "merged_in_doc1": len(merged_in_doc1),
        "merged_in_doc2": len(merged_in_doc2),
        "reorderings_detected": len(reorderings),
        "avg_similarity": round(quality["avg_similarity"], 3),
        # PHASE 3: Classification breakdown
        "formatting_only": sum(1 for d in differences if d["classification"] == "formatting_only"),
        "ocr_errors": sum(1 for d in differences if d["classification"] == "ocr_error"),
        "number_formatting": sum(1 for d in differences if d["classification"] == "number_formatting"),
    }

    # Generate verdict
    verdict = generate_verdict(summary)

    # Generate recommendations
    recommendations = generate_recommendations(summary, differences, reorderings)

    return {
        "summary": summary,
        "verdict": verdict,
        "differences": differences,
        "grouped_differences": grouped_differences,  # PHASE 3
        "reorderings": reorderings,
        "merged_sentences": {
            "merged_in_doc1": merged_in_doc1,
            "merged_in_doc2": merged_in_doc2
        },
        "recommendations": recommendations,
        "quality_analysis": quality
    }

def generate_report_with_collapsing(
    match_results: Dict,
    sentences1: List[Dict],
    sentences2: List[Dict]
) -> Dict:
    """
    Generate a Phase 3 report with smart missing sentence collapsing.
    """
    # Step 1: Generate standard report
    report = generate_report(match_results, sentences1, sentences2)

    # Step 2: Collapse consecutive missing sentences
    if report.get('differences'):
        report['differences'] = collapse_missing_sentences(report['differences'])

        # Step 3: Update summary
        collapsed_groups = sum(1 for d in report['differences'] if d.get('type') == 'missing_group')
        if collapsed_groups > 0:
            report['summary']['collapsed_missing_groups'] = collapsed_groups
            report['recommendations'].insert(0,
                f"{collapsed_groups} group(s) of consecutive missing sentences were detected. "
                "These may indicate OCR failure or missing pages."
            )

    return report

def get_severity(diff_type: str) -> str:
    """
    Map difference type to severity level
    Phase 3: Updated for new classifications
    """
    severity_map = {
        "citation_format": "very_low",      # ✅ Add this
        "latin_terminology": "very_low",    # ✅ Add this
        "statute_format": "very_low",       # ✅ Add this
        "name_variation": "low",            # ✅ Add this
        "exact_match": "none",
        "formatting_only": "very_low",      # PHASE 3
        "number_formatting": "very_low",    # PHASE 3
        "ocr_error": "low",                 # PHASE 3
        "minor_difference": "low",
        "rewording": "medium",
        "significant": "high",
        "sentence_merge": "medium"
    }
    return severity_map.get(diff_type, "medium")


def group_related_differences(differences: List[Dict]) -> List[Dict]:
    """
    PHASE 3: Group related differences together.

    Example:
        - Sentences 9-10 merged into 14 → Single grouped entry
        - Consecutive formatting-only changes → Grouped

    Returns list of groups:
        [
            {
                "type": "merge_group",
                "count": 2,
                "description": "Sentences 9-10 merged into Doc2 sentence 14",
                "differences": [...]
            },
            ...
        ]
    """
    groups = []
    used_indices = set()

    # Group 1: Merge groups (multiple sentences merged into one)
    merge_groups_doc1 = {}
    merge_groups_doc2 = {}

    for i, diff in enumerate(differences):
        if i in used_indices:
            continue

        if diff["type"] == "merged_in_doc1":
            target_pos = diff["position1"]
            if target_pos not in merge_groups_doc1:
                merge_groups_doc1[target_pos] = []
            merge_groups_doc1[target_pos].append((i, diff))
            used_indices.add(i)

        elif diff["type"] == "merged_in_doc2":
            target_pos = diff["position2"]
            if target_pos not in merge_groups_doc2:
                merge_groups_doc2[target_pos] = []
            merge_groups_doc2[target_pos].append((i, diff))
            used_indices.add(i)

    # Create merge group entries
    for target_pos, items in merge_groups_doc2.items():
        if len(items) > 1:
            source_positions = [d["position1"] for _, d in items]
            groups.append({
                "type": "merge_group",
                "count": len(items),
                "description": f"Sentences {min(source_positions)}-{max(source_positions)} from Doc1 merged into Doc2 sentence {target_pos}",
                "target_position": target_pos,
                "source_positions": source_positions,
                "differences": [d for _, d in items]
            })

    for target_pos, items in merge_groups_doc1.items():
        if len(items) > 1:
            source_positions = [d["position2"] for _, d in items]
            groups.append({
                "type": "merge_group",
                "count": len(items),
                "description": f"Sentences {min(source_positions)}-{max(source_positions)} from Doc2 merged into Doc1 sentence {target_pos}",
                "target_position": target_pos,
                "source_positions": source_positions,
                "differences": [d for _, d in items]
            })

    # Group 2: Consecutive formatting-only changes
    formatting_streak = []
    for i, diff in enumerate(differences):
        if i in used_indices:
            continue

        if diff["classification"] in ["formatting_only", "number_formatting", "citation_format"]:
            formatting_streak.append((i, diff))
        else:
            if len(formatting_streak) >= 3:  # Group if 3+ consecutive
                groups.append({
                    "type": "formatting_group",
                    "count": len(formatting_streak),
                    "description": f"{len(formatting_streak)} consecutive formatting-only differences",
                    "differences": [d for _, d in formatting_streak]
                })
                used_indices.update(i for i, _ in formatting_streak)
            formatting_streak = []

    # Don't forget last streak
    if len(formatting_streak) >= 3:
        groups.append({
            "type": "formatting_group",
            "count": len(formatting_streak),
            "description": f"{len(formatting_streak)} consecutive formatting-only differences",
            "differences": [d for _, d in formatting_streak]
        })
        used_indices.update(i for i, _ in formatting_streak)

    # Add ungrouped differences
    for i, diff in enumerate(differences):
        if i not in used_indices:
            groups.append({
                "type": "single",
                "count": 1,
                "description": None,
                "differences": [diff]
            })

    return groups


def generate_verdict(summary: Dict) -> Dict:
    """
    Generate overall verdict about document similarity
    Phase 3: Consider formatting-only differences separately
    """
    match_pct = summary["overall_match"]
    formatting_only = summary.get("formatting_only", 0)
    total_diffs = summary["significant_differences"]

    # Adjust verdict if most differences are formatting
    if total_diffs > 0 and formatting_only / total_diffs > 0.7:
        status = "identical_with_formatting"
        message = "Documents are identical except for formatting differences"
        color = "lightgreen"
    elif match_pct >= 98:
        status = "identical"
        message = "Documents are virtually identical"
        color = "green"
    elif match_pct >= 90:
        status = "very_similar"
        message = "Documents are very similar with minor differences"
        color = "green"
    elif match_pct >= 75:
        status = "similar"
        message = "Documents are similar but have notable differences"
        color = "yellow"
    elif match_pct >= 50:
        status = "different"
        message = "Documents have significant differences"
        color = "orange"
    else:
        status = "very_different"
        message = "Documents are substantially different"
        color = "red"

    return {
        "status": status,
        "message": message,
        "color": color,
        "confidence": "high" if summary["matched_sentences"] > 5 else "medium"
    }


def generate_recommendations(
    summary: Dict,
    differences: List[Dict],
    reorderings: List[Dict]
) -> List[str]:
    """
    Generate actionable recommendations based on analysis
    Phase 3: More specific, actionable recommendations
    """
    recommendations = []

    # PHASE 3: Formatting-only differences
    formatting_count = summary.get("formatting_only", 0)
    if formatting_count > 0:
        recommendations.append(
            f"{formatting_count} difference(s) are formatting-only (case, punctuation). "
            "These can be safely ignored if content accuracy is the priority."
        )

    # PHASE 2: Check for merged sentences
    total_merges = summary.get("merged_in_doc1", 0) + summary.get("merged_in_doc2", 0)
    if total_merges > 0:
        recommendations.append(
            f"Detected {total_merges} sentence(s) that were merged during OCR. "
            "This is common with scanned documents. Review merged sections for accuracy."
        )

    # PHASE 3: OCR errors specifically
    ocr_errors = summary.get("ocr_errors", 0)
    if ocr_errors > 2:
        recommendations.append(
            f"{ocr_errors} likely OCR character recognition errors detected (l/1, O/0, etc.). "
            "Consider rescanning at higher resolution or using OCR correction tools."
        )

    # Check for reorderings
    if reorderings:
        recommendations.append(
            f"Detected {len(reorderings)} sentences in different order. "
            "Verify if content was intentionally reorganized."
        )

    # Check for missing content (AFTER merge detection)
    if summary["missing_in_doc1"] > 0:
        recommendations.append(
            f"{summary['missing_in_doc1']} sentence(s) appear only in document 2. "
            "Check if content was added or if OCR missed these sections."
        )

    if summary["missing_in_doc2"] > 0:
        recommendations.append(
            f"{summary['missing_in_doc2']} sentence(s) appear only in document 1. "
            "Check if content was removed or if OCR failed."
        )

    # PHASE 3: Content vs formatting assessment
    total_diffs = len(differences)
    if total_diffs > 0:
        content_changes = total_diffs - formatting_count
        if content_changes == 0:
            recommendations.append(
                "All differences are formatting-only. Content is identical."
            )
        elif content_changes < formatting_count:
            recommendations.append(
                f"Most differences ({formatting_count}/{total_diffs}) are formatting. "
                f"Only {content_changes} content change(s) detected."
            )

    # Check overall match
    if summary["overall_match"] < 90 and total_merges == 0 and formatting_count == 0:
        recommendations.append(
            "Documents have notable content differences. Manual review recommended for important documents."
        )

    # If very similar
    if summary["overall_match"] >= 95 and summary["minor_differences"] > 0:
        recommendations.append(
            "Documents are very similar. Differences appear to be minor variations. "
            "Verify if these are acceptable."
        )

    # PHASE 2: If mostly merges, different recommendation
    if total_merges > 0 and len(reorderings) == 0 and summary["missing_in_doc1"] == 0 and summary["missing_in_doc2"] == 0:
        recommendations.append(
            "Main differences are due to sentence boundary detection. "
            "Content appears identical but segmented differently."
        )

    # If no recommendations yet
    if not recommendations and summary["overall_match"] >= 98:
        recommendations.append(
            "Documents match very closely. No significant issues detected."
        )

    return recommendations


def generate_html_report(report: Dict, file1_name: str, file2_name: str) -> str:
    """
    Generate a nicely formatted HTML report
    Phase 3: Enhanced with inline diffs and better visualization
    """
    from comparison_engine.diff_utils import generate_side_by_side_diff

    summary = report["summary"]
    verdict = report["verdict"]
    differences = report["differences"]
    grouped_differences = report.get("grouped_differences", [])
    merged_sentences = report.get("merged_sentences", {})

    # Color coding
    color = verdict["color"]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Document Comparison Report</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 40px;
                background: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 8px;
                margin-bottom: 30px;
            }}
            .header h1 {{ margin: 0 0 10px 0; }}
            .verdict {{
                background: {color};
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin: 30px 0;
                text-align: center;
            }}
            .verdict h2 {{ margin: 0 0 10px 0; }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat {{
                background: #f9f9f9;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                border-left: 4px solid #667eea;
            }}
            .stat h3 {{
                margin: 0 0 5px 0;
                font-size: 32px;
                color: #667eea;
            }}
            .stat p {{
                margin: 0;
                color: #666;
                font-size: 14px;
            }}
            .difference {{
                border: 1px solid #e0e0e0;
                padding: 20px;
                margin: 20px 0;
                background: #fafafa;
                border-radius: 8px;
                border-left: 4px solid #ddd;
            }}
            .severity-very_low {{ border-left-color: #90EE90; }}
            .severity-low {{ border-left-color: #44ff44; }}
            .severity-medium {{ border-left-color: #ffaa00; }}
            .severity-high {{ border-left-color: #ff4444; }}
            .diff-container {{
                margin: 15px 0;
                padding: 15px;
                background: white;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.6;
            }}
            .diff-label {{
                font-weight: bold;
                margin-bottom: 5px;
                color: #666;
                font-family: Arial, sans-serif;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                margin-left: 10px;
                text-transform: uppercase;
            }}
            .badge-merge {{ background: #2196F3; color: white; }}
            .badge-relocated {{ background: #9C27B0; color: white; }}
            .badge-formatting {{ background: #4CAF50; color: white; }}
            .badge-ocr {{ background: #FF9800; color: white; }}
            .group-header {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin: 25px 0 10px 0;
                border-left: 4px solid #2196F3;
            }}
            .recommendations {{
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 20px;
                border-radius: 8px;
                margin: 30px 0;
            }}
            .recommendations h2 {{
                margin-top: 0;
                color: #856404;
            }}
            .recommendations ul {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .recommendations li {{
                margin: 10px 0;
                color: #856404;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📄 Document Comparison Report</h1>
                <p><strong>Document 1:</strong> {file1_name}</p>
                <p><strong>Document 2:</strong> {file2_name}</p>
                <p style="margin-top:10px;opacity:0.9;">Generated: {get_timestamp()}</p>
            </div>

            <div class="verdict">
                <h2>{verdict['message']}</h2>
                <p style="font-size:24px;margin:10px 0;">Overall Match: {summary['overall_match']}%</p>
                <p style="opacity:0.9;">Confidence: {verdict['confidence'].title()}</p>
            </div>

            <h2>Summary Statistics</h2>
            <div class="stats">
                <div class="stat">
                    <h3>{summary['total_sentences_doc1']}</h3>
                    <p>Sentences in Doc 1</p>
                </div>
                <div class="stat">
                    <h3>{summary['total_sentences_doc2']}</h3>
                    <p>Sentences in Doc 2</p>
                </div>
                <div class="stat">
                    <h3>{summary['matched_sentences']}</h3>
                    <p>Matched Sentences</p>
                </div>
                <div class="stat">
                    <h3>{summary['exact_matches']}</h3>
                    <p>Exact Matches</p>
                </div>
                <div class="stat">
                    <h3>{summary.get('formatting_only', 0)}</h3>
                    <p>Formatting Only</p>
                </div>
                <div class="stat">
                    <h3>{summary.get('ocr_errors', 0)}</h3>
                    <p>OCR Errors</p>
                </div>
                <div class="stat">
                    <h3>{summary.get('merged_in_doc1', 0) + summary.get('merged_in_doc2', 0)}</h3>
                    <p>Merged Sentences</p>
                </div>
                <div class="stat">
                    <h3>{summary['significant_differences']}</h3>
                    <p>Significant Differences</p>
                </div>
            </div>
    """

    # Recommendations section
    if report["recommendations"]:
        html += """
            <div class="recommendations">
                <h2>💡 Recommendations</h2>
                <ul>
        """
        for rec in report["recommendations"]:
            html += f"<li>{rec}</li>"
        html += """
                </ul>
            </div>
        """

    html += f"<h2>Detailed Differences ({len(differences)})</h2>"

    # Show grouped differences if available
    if grouped_differences:
        for group in grouped_differences:
            if group["type"] == "merge_group":
                html += f"""
                <div class="group-header">
                    <strong>🔗 Merge Group ({group['count']} sentences)</strong><br>
                    {group['description']}
                </div>
                """
            elif group["type"] == "formatting_group":
                html += f"""
                <div class="group-header">
                    <strong>📝 Formatting Group ({group['count']} differences)</strong><br>
                    {group['description']}
                </div>
                """

            # Show differences in group (collapsed for formatting groups)
            if group["type"] != "formatting_group" or len(group["differences"]) <= 3:
                for diff in group["differences"]:
                    html += generate_difference_html(diff, show_inline_diff=True)

    else:
        # No grouping, show all differences
        for i, diff in enumerate(differences, 1):
            html += generate_difference_html(diff, diff_num=i, show_inline_diff=True)

    html += """
        </div>
    </body>
    </html>
    """

    return html


def generate_difference_html(diff: Dict, diff_num: int = None, show_inline_diff: bool = True) -> str:
    """Generate HTML for a single difference."""
    severity_class = f"severity-{diff['severity']}"
    diff_type = diff['type']
    classification = diff['classification']

    # Badges
    badges = ""
    if diff_type in ["merged_in_doc1", "merged_in_doc2"]:
        badges += '<span class="badge badge-merge">MERGED</span>'
    elif diff.get("relocated"):
        badges += '<span class="badge badge-relocated">RELOCATED</span>'

    if classification == "formatting_only":
        badges += '<span class="badge badge-formatting">FORMATTING</span>'
    elif classification == "ocr_error":
        badges += '<span class="badge badge-ocr">OCR ERROR</span>'

    num_str = f"#{diff_num} - " if diff_num else ""

    html = f"""
    <div class="difference {severity_class}">
        <h3>{num_str}{classification.replace('_', ' ').title()}{badges}</h3>
        <p><strong>Type:</strong> {diff_type.replace('_', ' ').title()}</p>
        <p><strong>Position:</strong>
            Doc1: {diff['position1'] or 'N/A'},
            Doc2: {diff['position2'] or 'N/A'}
        </p>
        <p><strong>Similarity:</strong> {diff['similarity']:.1%}</p>
    """

    # Show inline diff if available
    if show_inline_diff and diff.get('diff_html1') and diff.get('diff_html2'):
        html += f"""
        <div class="diff-container">
            <div class="diff-label">Document 1:</div>
            <div>{diff['diff_html1']}</div>
        </div>
        <div class="diff-container">
            <div class="diff-label">Document 2:</div>
            <div>{diff['diff_html2']}</div>
        </div>
        """
    else:
        # Fallback to plain text
        if diff['sentence1']:
            html += f'<p><strong>Document 1:</strong> {diff["sentence1"]}</p>'
        if diff['sentence2']:
            html += f'<p><strong>Document 2:</strong> {diff["sentence2"]}</p>'

    # Suggestions
    if diff['suggestions']:
        html += '<p><strong>Suggestions:</strong></p><ul>'
        for s in diff['suggestions']:
            html += f"<li>{s}</li>"
        html += '</ul>'

    if diff.get("explanation"):
        html += f"""
        <p style="background:#eef7ff;padding:10px;border-left:4px solid #2196F3;
                  border-radius:4px;">
            <strong>Note:</strong> {diff["explanation"]}
        </p>
        """
    html += '</div>'

    # ✅ Show OCR metadata in report
    if diff['sentence1']:
        sent1_meta = diff.get('sent1_metadata', {})
        confidence = sent1_meta.get('confidence', 'N/A')
        ocr_method = sent1_meta.get('ocr_method', 'N/A')

        html += f"""
        <div class="diff-container">
            <div class="diff-label">Document 1:</div>
            <div>{diff['diff_html1']}</div>
            <small class="metadata">
                OCR: {ocr_method} | Confidence: {confidence:.2f}
            </small>
        </div>
        """

    return html


def get_timestamp() -> str:
    """Get current timestamp for report."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def collapse_missing_sentences(differences: List[Dict]) -> List[Dict]:
    """
    Collapse consecutive missing sentences into grouped markers.

    Example:
        Instead of:
            - [Sentence 4] missing
            - [Sentence 5] missing
            - [Sentence 6] missing

        Returns:
            - [3 sentences missing: 4-6]

    Args:
        differences: List of difference objects

    Returns:
        Cleaned differences list with collapsed groups
    """
    if not differences:
        return []

    collapsed = []
    missing_buffer = []

    def flush_missing_buffer():
        """Convert buffered missing sentences to a single group marker."""
        if not missing_buffer:
            return

        if len(missing_buffer) == 1:
            # Single missing sentence - keep as is
            collapsed.append(missing_buffer[0])
        else:
            # Multiple consecutive missing - collapse
            first = missing_buffer[0]
            last = missing_buffer[-1]

            positions = [d['position1'] or d['position2'] for d in missing_buffer]
            min_pos = min(p for p in positions if p)
            max_pos = max(p for p in positions if p)

            collapsed.append({
                "type": "missing_group",
                "classification": "collapsed_missing",
                "severity": "medium",
                "position1": first['position1'],
                "position2": first['position2'],
                "sentence1": f"[{len(missing_buffer)} sentences missing or unreadable: {min_pos}-{max_pos}]",
                "sentence2": first['sentence2'],
                "similarity": 0.0,
                "suggestions": [
                    f"{len(missing_buffer)} consecutive sentences could not be read or matched",
                    "Consider rescanning document or checking source quality"
                ],
                "count": len(missing_buffer),
                "diff_html1": None,
                "diff_html2": None
            })

        missing_buffer.clear()

    # Process differences
    for diff in differences:
        is_missing = (
            diff['type'] in ['missing_in_doc1', 'missing_in_doc2'] or
            diff['classification'] == 'addition' or
            (not diff.get('sentence1') or not diff.get('sentence2'))
        )

        # Check if sentence text looks like placeholder
        sent1 = diff.get('sentence1', '')
        sent2 = diff.get('sentence2', '')

        is_placeholder = (
            '[Sentence' in sent1 or '[Sentence' in sent2 or
            '<unreadable>' in sent1.lower() or '<unreadable>' in sent2.lower()
        )

        if is_missing or is_placeholder:
            missing_buffer.append(diff)
        else:
            # Not missing - flush any buffered missing sentences first
            flush_missing_buffer()
            collapsed.append(diff)

    # Don't forget last group
    flush_missing_buffer()

    return collapsed


def clean_sentence_text(text: str) -> Optional[str]:
    """
    Clean sentence text by removing placeholder artifacts.

    Returns None if sentence should be skipped entirely.
    """
    if not text or text.strip() == '':
        return None

    # Remove placeholder patterns
    if text.startswith('[Sentence ') and text.endswith(']'):
        return None

    # Remove unreadable markers
    if '<unreadable>' in text.lower():
        return None

    # Clean OCR artifacts but keep the sentence
    cleaned = text.replace('<unreadable>', '').strip()

    # If too short after cleaning, skip it
    if len(cleaned) < 3:
        return None

    return cleaned
