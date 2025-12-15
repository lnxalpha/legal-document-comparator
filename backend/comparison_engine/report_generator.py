"""
Report Generation Module
Creates detailed comparison reports from match results
"""

from typing import List, Dict
from comparison_engine.semantic_matcher import (
    classify_difference, 
    analyze_match_quality,
    find_potential_reorderings,
    suggest_corrections
)


def generate_report(
    match_results: Dict,
    sentences1: List[Dict],
    sentences2: List[Dict]
) -> Dict:
    """
    Generate a comprehensive comparison report
    
    Returns structured report with:
    - Overall statistics
    - Detailed differences
    - Quality analysis
    - Recommendations
    """
    matches = match_results["matches"]
    only_in_doc1 = match_results["only_in_doc1"]
    only_in_doc2 = match_results["only_in_doc2"]
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
            
            differences.append({
                "type": "mismatch",
                "classification": diff_type,
                "severity": get_severity(diff_type),
                "position1": match["index1"] + 1,  # 1-indexed for users
                "position2": match["index2"] + 1,
                "sentence1": match["sent1"]["text"],
                "sentence2": match["sent2"]["text"],
                "similarity": match["similarity"],
                "suggestions": suggest_corrections(match)
            })
    
    # 2. Sentences only in document 1
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
            "suggestions": ["This sentence appears in document 1 but not in document 2"]
        })
    
    # 3. Sentences only in document 2
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
            "suggestions": ["This sentence appears in document 2 but not in document 1"]
        })
    
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
        "reorderings_detected": len(reorderings),
        "avg_similarity": round(quality["avg_similarity"], 3)
    }
    
    # Generate verdict
    verdict = generate_verdict(summary)
    
    # Generate recommendations
    recommendations = generate_recommendations(summary, differences, reorderings)
    
    return {
        "summary": summary,
        "verdict": verdict,
        "differences": differences,
        "reorderings": reorderings,
        "recommendations": recommendations,
        "quality_analysis": quality
    }


def get_severity(diff_type: str) -> str:
    """Map difference type to severity level"""
    severity_map = {
        "exact_match": "none",
        "minor_difference": "low",
        "rewording": "medium",
        "significant": "high"
    }
    return severity_map.get(diff_type, "medium")


def generate_verdict(summary: Dict) -> Dict:
    """
    Generate overall verdict about document similarity
    """
    match_pct = summary["overall_match"]
    
    if match_pct >= 98:
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
    """
    recommendations = []
    
    # Check for OCR issues
    ocr_suggestions = sum(
        1 for d in differences 
        if any("OCR" in s for s in d.get("suggestions", []))
    )
    if ocr_suggestions > 3:
        recommendations.append(
            "Multiple potential OCR errors detected. Consider rescanning document with higher quality settings."
        )
    
    # Check for reorderings
    if reorderings:
        recommendations.append(
            f"Detected {len(reorderings)} sentences that appear in different order. "
            "Verify if content was intentionally reorganized."
        )
    
    # Check for missing content
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
    
    # Check overall match
    if summary["overall_match"] < 90:
        recommendations.append(
            "Documents have notable differences. Manual review recommended for important documents."
        )
    
    # If very similar
    if summary["overall_match"] >= 95 and summary["minor_differences"] > 0:
        recommendations.append(
            "Documents are very similar. Differences appear to be minor (typos, punctuation). "
            "Verify if these are acceptable variations."
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
    (Can be used for downloadable reports)
    """
    summary = report["summary"]
    verdict = report["verdict"]
    differences = report["differences"]
    
    # Color coding
    color = verdict["color"]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Document Comparison Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background: #f0f0f0; padding: 20px; border-radius: 8px; }}
            .verdict {{ 
                background: {color}; 
                color: white; 
                padding: 15px; 
                border-radius: 8px; 
                margin: 20px 0;
            }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
            .stat {{ background: #f9f9f9; padding: 15px; border-radius: 8px; }}
            .difference {{ 
                border-left: 4px solid #ddd; 
                padding: 15px; 
                margin: 15px 0; 
                background: #f9f9f9;
            }}
            .severity-high {{ border-left-color: #ff4444; }}
            .severity-medium {{ border-left-color: #ffaa00; }}
            .severity-low {{ border-left-color: #44ff44; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📄 Document Comparison Report</h1>
            <p><strong>Document 1:</strong> {file1_name}</p>
            <p><strong>Document 2:</strong> {file2_name}</p>
        </div>
        
        <div class="verdict">
            <h2>{verdict['message']}</h2>
            <p>Overall Match: {summary['overall_match']}%</p>
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
                <h3>{summary['minor_differences']}</h3>
                <p>Minor Differences</p>
            </div>
            <div class="stat">
                <h3>{summary['significant_differences']}</h3>
                <p>Significant Differences</p>
            </div>
        </div>
        
        <h2>Detailed Differences ({len(differences)})</h2>
    """
    
    for i, diff in enumerate(differences, 1):
        severity_class = f"severity-{diff['severity']}"
        html += f"""
        <div class="difference {severity_class}">
            <h3>Difference #{i} - {diff['classification'].replace('_', ' ').title()}</h3>
            <p><strong>Type:</strong> {diff['type'].replace('_', ' ').title()}</p>
            <p><strong>Position:</strong> 
                Doc1: {diff['position1'] or 'N/A'}, 
                Doc2: {diff['position2'] or 'N/A'}
            </p>
            <p><strong>Similarity:</strong> {diff['similarity']:.1%}</p>
            
            {f'<p><strong>Document 1:</strong> {diff["sentence1"]}</p>' if diff['sentence1'] else ''}
            {f'<p><strong>Document 2:</strong> {diff["sentence2"]}</p>' if diff['sentence2'] else ''}
            
            {f'<p><strong>Suggestions:</strong></p><ul>{"".join(f"<li>{s}</li>" for s in diff["suggestions"])}</ul>' if diff['suggestions'] else ''}
        </div>
        """
    
    html += """
        <h2>Recommendations</h2>
        <ul>
    """
    
    for rec in report["recommendations"]:
        html += f"<li>{rec}</li>"
    
    html += """
        </ul>
    </body>
    </html>
    """
    
    return html


# For testing
if __name__ == "__main__":
    # Mock data for testing
    mock_matches = [
        {
            "sent1": {"id": 0, "text": "This is sentence one."},
            "sent2": {"id": 0, "text": "This is sentence one."},
            "similarity": 1.0,
            "index1": 0,
            "index2": 0,
            "exact_match": True,
            "normalized_match": True
        },
        {
            "sent1": {"id": 1, "text": "This is sentence two."},
            "sent2": {"id": 1, "text": "This is sentnce two."},
            "similarity": 0.92,
            "index1": 1,
            "index2": 1,
            "exact_match": False,
            "normalized_match": False
        }
    ]
    
    mock_results = {
        "matches": mock_matches,
        "only_in_doc1": [],
        "only_in_doc2": [{"id": 2, "text": "Extra sentence in doc 2."}],
        "match_score": 0.85
    }
    
    sentences1 = [m["sent1"] for m in mock_matches]
    sentences2 = [m["sent2"] for m in mock_matches] + mock_results["only_in_doc2"]
    
    report = generate_report(mock_results, sentences1, sentences2)
    
    print("Report Summary:")
    print("="*60)
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    
    print("\nVerdict:")
    print(report["verdict"]["message"])
    
    print(f"\nDifferences: {len(report['differences'])}")
    print(f"Recommendations: {len(report['recommendations'])}")
