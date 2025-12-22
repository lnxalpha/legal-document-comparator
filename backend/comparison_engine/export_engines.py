"""
Export Engines Module
Generate PDF and Word documents from comparison reports (Phase 5)
"""

from typing import Optional
from pathlib import Path
import logging
from datetime import datetime

from comparison_engine.report_schema import ComparisonReport, FlaggedItem
from comparison_engine.report_builder import generate_executive_summary

LOG = logging.getLogger(__name__)


# ============================================
# PDF EXPORT (using ReportLab)
# ============================================

def export_pdf(
    report: ComparisonReport,
    output_path: str,
    include_full_text: bool = True
) -> str:
    """
    Export comparison report as PDF.

    Args:
        report: ComparisonReport to export
        output_path: Path to save PDF
        include_full_text: Whether to include full sentence text

    Returns:
        Path to generated PDF file
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    except ImportError:
        raise ImportError(
            "ReportLab is required for PDF export. Install with: pip install reportlab"
        )

    LOG.info(f"Generating PDF report: {output_path}")

    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )

    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )

    # Build document content
    story = []

    # Title Page
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Document Comparison Report", title_style))
    story.append(Spacer(1, 0.3*inch))

    # Document names
    story.append(Paragraph(f"<b>Reference Document:</b> {report.reference_document}", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Target Document:</b> {report.target_document}", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Generated:</b> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        body_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Report ID:</b> {report.report_id}", body_style))

    story.append(PageBreak())

    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))

    stats = report.summary_stats

    # Overall match
    match_color = (
        colors.green if stats.overall_match >= 90 else
        colors.orange if stats.overall_match >= 75 else
        colors.red
    )

    story.append(Paragraph(
        f"<b>Overall Match:</b> <font color='{match_color}'>{stats.overall_match}%</font>",
        body_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Assessment:</b> {report.overall_assessment.replace('_', ' ').title()}",
        body_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Verdict:</b> {report.verdict_message}", body_style))

    story.append(Spacer(1, 0.2*inch))

    # Summary statistics table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Sentences (Doc 1)', str(stats.total_sentences_doc1)],
        ['Total Sentences (Doc 2)', str(stats.total_sentences_doc2)],
        ['Matched Sentences', str(stats.matched_sentences)],
        ['Exact Matches', str(stats.exact_matches)],
        ['Total Differences', str(stats.total_differences)],
        ['High Severity', str(stats.high_severity)],
        ['Medium Severity', str(stats.medium_severity)],
        ['Low Severity', str(stats.low_severity)],
    ]

    summary_table = Table(summary_data, colWidths=[3.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 0.2*inch))

    # Recommendations
    if report.recommendations:
        story.append(Paragraph("Recommendations", heading_style))
        for i, rec in enumerate(report.recommendations, 1):
            # Strip markdown formatting for PDF
            clean_rec = rec.replace('**', '').replace('*', '')
            story.append(Paragraph(f"{i}. {clean_rec}", body_style))
            story.append(Spacer(1, 6))

    story.append(PageBreak())

    # Detailed Differences
    story.append(Paragraph(f"Detailed Differences ({len(report.flagged_items)})", heading_style))

    for idx, item in enumerate(report.flagged_items, 1):
        # Create difference entry
        diff_elements = []

        # Header
        severity_color = {
            'high': colors.red,
            'medium': colors.orange,
            'low': colors.green,
            'very_low': colors.lightgreen
        }.get(item.severity, colors.grey)

        header_text = (
            f"<b>Difference #{idx}</b> - "
            f"<font color='{severity_color}'>{item.severity.upper()}</font> - "
            f"{item.difference_type.replace('_', ' ').title()}"
        )
        diff_elements.append(Paragraph(header_text, subheading_style))
        diff_elements.append(Spacer(1, 6))

        # Metadata
        diff_elements.append(Paragraph(
            f"<b>Position:</b> Doc1: {item.position1 or 'N/A'}, Doc2: {item.position2 or 'N/A'}",
            body_style
        ))
        diff_elements.append(Spacer(1, 4))
        diff_elements.append(Paragraph(
            f"<b>Similarity:</b> {item.similarity * 100:.1f}%",
            body_style
        ))
        diff_elements.append(Spacer(1, 4))
        diff_elements.append(Paragraph(
            f"<b>System Decision:</b> {item.system_decision.upper()} (confidence: {item.confidence:.2f})",
            body_style
        ))
        diff_elements.append(Spacer(1, 8))

        # Text comparison (if full text included)
        if include_full_text and item.reference_text and item.target_text:
            diff_elements.append(Paragraph("<b>Reference Text:</b>", body_style))
            diff_elements.append(Spacer(1, 4))
            diff_elements.append(Paragraph(
                f"<i>{item.reference_text[:200]}{'...' if len(item.reference_text) > 200 else ''}</i>",
                body_style
            ))
            diff_elements.append(Spacer(1, 6))

            diff_elements.append(Paragraph("<b>Target Text:</b>", body_style))
            diff_elements.append(Spacer(1, 4))
            diff_elements.append(Paragraph(
                f"<i>{item.target_text[:200]}{'...' if len(item.target_text) > 200 else ''}</i>",
                body_style
            ))
            diff_elements.append(Spacer(1, 8))

        # System rationale
        diff_elements.append(Paragraph("<b>Analysis:</b>", body_style))
        diff_elements.append(Spacer(1, 4))
        # Clean markdown from rationale
        clean_rationale = item.rationale.replace('**', '').replace('*', '').replace('\n', '<br/>')
        diff_elements.append(Paragraph(clean_rationale[:500], body_style))

        # User decision if present
        if item.user_decision:
            diff_elements.append(Spacer(1, 8))
            diff_elements.append(Paragraph(
                f"<b>User Decision:</b> {item.user_decision.upper()}",
                body_style
            ))
            if item.user_note:
                diff_elements.append(Spacer(1, 4))
                diff_elements.append(Paragraph(
                    f"<b>User Note:</b> {item.user_note}",
                    body_style
                ))

        # Keep difference entry together
        story.append(KeepTogether(diff_elements))
        story.append(Spacer(1, 0.15*inch))

        # Page break every 5 items
        if idx % 5 == 0 and idx < len(report.flagged_items):
            story.append(PageBreak())

    # Build PDF
    doc.build(story)

    LOG.info(f"PDF report generated: {output_path}")
    return output_path


# ============================================
# WORD EXPORT (using python-docx)
# ============================================

def export_word(
    report: ComparisonReport,
    output_path: str,
    include_full_text: bool = True
) -> str:
    """
    Export comparison report as Word document.

    Args:
        report: ComparisonReport to export
        output_path: Path to save DOCX
        include_full_text: Whether to include full sentence text

    Returns:
        Path to generated DOCX file
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.style import WD_STYLE_TYPE
    except ImportError:
        raise ImportError(
            "python-docx is required for Word export. Install with: pip install python-docx"
        )

    LOG.info(f"Generating Word report: {output_path}")

    doc = Document()

    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Title
    title = doc.add_heading('📄 Document Comparison Report', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Document metadata
    doc.add_paragraph(f"Reference Document: {report.reference_document}", style='Normal')
    doc.add_paragraph(f"Target Document: {report.target_document}", style='Normal')
    doc.add_paragraph(
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        style='Normal'
    )
    doc.add_paragraph(f"Report ID: {report.report_id}", style='Normal')

    doc.add_page_break()

    # Executive Summary
    doc.add_heading('Executive Summary', level=1)

    stats = report.summary_stats

    doc.add_paragraph(f"Overall Match: {stats.overall_match}%")
    doc.add_paragraph(f"Assessment: {report.overall_assessment.replace('_', ' ').title()}")
    doc.add_paragraph(f"Verdict: {report.verdict_message}")

    doc.add_paragraph()

    # Summary statistics table
    doc.add_heading('Summary Statistics', level=2)

    table = doc.add_table(rows=10, cols=2)
    table.style = 'Light Grid Accent 1'

    table_data = [
        ('Metric', 'Value'),
        ('Total Sentences (Doc 1)', str(stats.total_sentences_doc1)),
        ('Total Sentences (Doc 2)', str(stats.total_sentences_doc2)),
        ('Matched Sentences', str(stats.matched_sentences)),
        ('Exact Matches', str(stats.exact_matches)),
        ('Total Differences', str(stats.total_differences)),
        ('High Severity', str(stats.high_severity)),
        ('Medium Severity', str(stats.medium_severity)),
        ('Low Severity', str(stats.low_severity)),
    ]

    for i, (label, value) in enumerate(table_data):
        row = table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value

        # Bold header row
        if i == 0:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True

    doc.add_paragraph()

    # Recommendations
    if report.recommendations:
        doc.add_heading('Recommendations', level=2)
        for i, rec in enumerate(report.recommendations, 1):
            # Clean markdown
            clean_rec = rec.replace('**', '').replace('*', '')
            p = doc.add_paragraph(clean_rec, style='List Number')

    doc.add_page_break()

    # Detailed Differences
    doc.add_heading(f'Detailed Differences ({len(report.flagged_items)})', level=1)

    for idx, item in enumerate(report.flagged_items, 1):
        # Difference header
        header = doc.add_heading(
            f"Difference #{idx} - {item.severity.upper()} - {item.difference_type.replace('_', ' ').title()}",
            level=3
        )

        # Color code by severity
        severity_color = {
            'high': RGBColor(231, 76, 60),
            'medium': RGBColor(243, 156, 18),
            'low': RGBColor(39, 174, 96),
            'very_low': RGBColor(46, 204, 113)
        }.get(item.severity, RGBColor(127, 140, 141))

        for run in header.runs:
            run.font.color.rgb = severity_color

        # Metadata
        doc.add_paragraph(f"Position: Doc1: {item.position1 or 'N/A'}, Doc2: {item.position2 or 'N/A'}")
        doc.add_paragraph(f"Similarity: {item.similarity * 100:.1f}%")
        doc.add_paragraph(
            f"System Decision: {item.system_decision.upper()} (confidence: {item.confidence:.2f})"
        )

        # Text comparison
        if include_full_text and item.reference_text and item.target_text:
            doc.add_paragraph()
            doc.add_paragraph("Reference Text:", style='Intense Quote').bold = True
            ref_p = doc.add_paragraph(item.reference_text[:300], style='Intense Quote')
            ref_p.runs[0].italic = True

            doc.add_paragraph("Target Text:", style='Intense Quote').bold = True
            tar_p = doc.add_paragraph(item.target_text[:300], style='Intense Quote')
            tar_p.runs[0].italic = True

        # Analysis
        doc.add_paragraph()
        doc.add_paragraph("Analysis:", style='Normal').bold = True
        # Clean markdown
        clean_rationale = item.rationale.replace('**', '').replace('*', '')
        doc.add_paragraph(clean_rationale[:600])

        # User decision
        if item.user_decision:
            doc.add_paragraph()
            user_p = doc.add_paragraph(f"User Decision: {item.user_decision.upper()}")
            user_p.runs[0].font.bold = True
            user_p.runs[0].font.color.rgb = RGBColor(52, 152, 219)

            if item.user_note:
                doc.add_paragraph(f"User Note: {item.user_note}")

        doc.add_paragraph()
        doc.add_paragraph("_" * 80)
        doc.add_paragraph()

    # Save document
    doc.save(output_path)

    LOG.info(f"Word report generated: {output_path}")
    return output_path


# ============================================
# CONVENIENCE FUNCTION
# ============================================

def export_report(
    report: ComparisonReport,
    output_dir: str,
    format: str = "both",
    include_full_text: bool = True
) -> dict:
    """
    Export report in specified format(s).

    Args:
        report: ComparisonReport to export
        output_dir: Directory to save files
        format: "pdf", "word", or "both"
        include_full_text: Whether to include full sentence text

    Returns:
        Dict with paths: {"pdf": path, "word": path}
    """
    from pathlib import Path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"comparison_report_{report.report_id}_{timestamp}"

    result = {}

    if format in ["pdf", "both"]:
        pdf_path = output_dir / f"{base_name}.pdf"
        result["pdf"] = export_pdf(report, str(pdf_path), include_full_text)

    if format in ["word", "both"]:
        word_path = output_dir / f"{base_name}.docx"
        result["word"] = export_word(report, str(word_path), include_full_text)

    LOG.info(f"Export complete: {list(result.keys())}")
    return result


# Testing
if __name__ == "__main__":
    from comparison_engine.report_builder import build_comparison_report

    # Mock data
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
            "message": "Documents are very similar with minor differences"
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
                "suggestions": ["Possible OCR error"]
            }
        ],
        "recommendations": [
            "Documents match closely with minor OCR errors."
        ]
    }

    # Build report
    report = build_comparison_report(
        mock_comparison,
        "contract_original.pdf",
        "contract_signed.jpg"
    )

    # Export
    try:
        paths = export_report(report, "./output", format="both")
        print(f"✅ Export successful!")
        for fmt, path in paths.items():
            print(f"  {fmt.upper()}: {path}")
    except ImportError as e:
        print(f"❌ {e}")
        print("Install dependencies: pip install reportlab python-docx")
