"""
Legal Document Comparator - Main Application
FastAPI backend with smart document comparison and export
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from pathlib import Path
import json
import logging
import time
import uuid
from datetime import datetime

from config import Config, ModelConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

# --------------------------------------------------
# Path setup
# --------------------------------------------------
FRONTEND_DIR = Config.STATIC_DIR

# Create directories
Config.UPLOAD_DIR.mkdir(exist_ok=True)
Config.REPORT_DIR.mkdir(exist_ok=True)
Config.EXPORT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# Initialize FastAPI app
# --------------------------------------------------
app = FastAPI(
    title="Legal Document Comparator",
    description="Smart context-aware document verification with AI",
    version="1.0.0"
)

# --------------------------------------------------
# CORS middleware
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if Config.DEBUG else [Config.get_frontend_url()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Static files
# --------------------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# --------------------------------------------------
# Lifecycle events
# --------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 60)
    print("🚀 Legal Document Comparator Starting...")
    print("=" * 60 + "\n")

    if Config.is_production():
        print("Production mode: Preloading ML models...")
        ModelConfig.preload_models()
    else:
        print("Development mode: Models will load on first use")

    print(f"Upload directory: {Config.UPLOAD_DIR}")
    print(f"Report directory: {Config.REPORT_DIR}")
    print(f"Export directory: {Config.EXPORT_DIR}")
    print(f"Max file size: {Config.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB")
    print("\n" + "=" * 60)
    print(f"✅ Server ready at http://{Config.HOST}:{Config.PORT}")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    print("\n🛑 Shutting down...")
    for path in Config.UPLOAD_DIR.glob("*"):
        try:
            path.unlink()
        except Exception:
            pass


# --------------------------------------------------
# Frontend route
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    comparison_path = FRONTEND_DIR / "comparison_view.html"
    if not comparison_path.exists():
        raise HTTPException(404, "comparison_view.html not found")
    return FileResponse(comparison_path)


# --------------------------------------------------
# API endpoints
# --------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": "production" if Config.is_production() else "development",
        "models_loaded": {
            "spacy": ModelConfig._spacy_nlp is not None,
            "sentence_transformer": ModelConfig._sentence_model is not None,
        },
        "directories": {
            "reports": str(Config.REPORT_DIR),
            "exports": str(Config.EXPORT_DIR)
        }
    }


# ============================================
# 2️⃣ MODIFY /api/compare ENDPOINT
# ============================================
# Replace your existing /api/compare function starting around line 200

@app.post("/api/compare")
async def compare_documents(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    start_time = time.time()

    if not Config.validate_file(file1.filename):
        raise HTTPException(400, f"Invalid file type: {file1.filename}")
    if not Config.validate_file(file2.filename):
        raise HTTPException(400, f"Invalid file type: {file2.filename}")

    file1_path = None
    file2_path = None

    try:
        # Save uploaded files
        filename1 = Path(file1.filename).name
        filename2 = Path(file2.filename).name

        safe_name1 = f"{uuid.uuid4()}_{filename1}"
        safe_name2 = f"{uuid.uuid4()}_{filename2}"

        file1_path = Config.UPLOAD_DIR / safe_name1
        file2_path = Config.UPLOAD_DIR / safe_name2

        for upload, path in [(file1, file1_path), (file2, file2_path)]:
            content = await upload.read()
            if len(content) > Config.MAX_UPLOAD_SIZE:
                raise HTTPException(400, f"File too large: {upload.filename}")
            path.write_bytes(content)

        # Import processing modules
        from unified_extractor.extractor import extract_text_with_confidence
        from comparison_engine.smart_chunker import chunk_into_sentences
        from comparison_engine.semantic_matcher import match_documents
        from comparison_engine.report_generator import generate_report

        # Extract text (OCR still runs - this is important!)
        LOG.info(f"Extracting text from {file1.filename} and {file2.filename}")

        extraction1 = await extract_text_with_confidence(file1_path)
        extraction2 = await extract_text_with_confidence(file2_path)

        text1 = extraction1["text"]
        text2 = extraction2["text"]

        if not text1 or not text2:
            raise HTTPException(400, "Could not extract text from one or both documents")

        # =====================================================
        # 🔍 FAST IDENTITY PRE-CHECK (NEW - PHASE 7)
        # =====================================================
        LOG.info("Running fast identity pre-check...")

        normalized1 = normalize_for_identity(text1)
        normalized2 = normalize_for_identity(text2)

        if normalized1 == normalized2:
            LOG.info("✅ Exact match detected after normalization — skipping semantic comparison")

            processing_time = round(time.time() - start_time, 2)
            report_id = f"report_{uuid.uuid4().hex[:16]}"

            # Create minimal report for identical documents
            response_data = {
                "report_id": report_id,
                "summary": {
                    "overall_match": 100.0,
                    "total_sentences_doc1": len(text1.split('.')),
                    "total_sentences_doc2": len(text2.split('.')),
                    "matched_sentences": len(text1.split('.')),
                    "exact_matches": len(text1.split('.')),
                    "minor_differences": 0,
                    "significant_differences": 0,
                    "formatting_only": 0,
                    "ocr_errors": 0,
                    "avg_similarity": 1.0,
                    # 🆕 Identity flag
                    "exact_match": True,
                    "identity_check": True
                },
                "verdict": {
                    "status": "identical",
                    "message": "Documents are textually identical after normalization",
                    "color": "green"
                },
                "differences": [],
                "recommendations": [
                    "✅ Documents are textually identical after normalization.",
                    "No differences detected - documents can be considered equivalent.",
                    f"Processing completed in {processing_time}s using fast identity check."
                ],
                "file1_name": file1.filename,
                "file2_name": file2.filename,
                "processing_time": processing_time,
                "sentences1": [],  # Empty - no need to chunk
                "sentences2": []   # Empty - no need to chunk
            }

            # Save minimal report for export consistency
            report_path = Config.REPORT_DIR / f"{report_id}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(
                    make_json_safe(response_data),
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            LOG.info(f"Identity match report saved: {report_path}")

            # Schedule cleanup
            background_tasks.add_task(cleanup_files, [file1_path, file2_path])

            return make_json_safe(response_data)

        # =====================================================
        # 📊 NORMAL SEMANTIC COMPARISON (Documents differ)
        # =====================================================
        LOG.info("Documents differ - proceeding with full semantic analysis...")

        # Continue with your existing comparison logic
        LOG.info("Chunking sentences...")
        sentences1 = chunk_into_sentences(text1, provenance=extraction1)
        sentences2 = chunk_into_sentences(text2, provenance=extraction2)

        LOG.info("Matching documents...")
        matches = match_documents(sentences1, sentences2)

        LOG.info("Generating report...")
        report = generate_report(matches, sentences1, sentences2)

        # Generate unique report ID
        report_id = f"report_{uuid.uuid4().hex[:16]}"

        # Save full report data for later export
        report_data = {
            "id": report_id,
            "timestamp": datetime.now().isoformat(),
            "file1_name": file1.filename,
            "file2_name": file2.filename,
            "summary": report["summary"],
            "differences": report["differences"],
            "recommendations": report.get("recommendations", []),
            "sentences1": serialize_sentences(sentences1),
            "sentences2": serialize_sentences(sentences2),
            "full_report": report
        }

        # Save to disk
        report_path = Config.REPORT_DIR / f"{report_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(
                make_json_safe(report_data),
                f,
                ensure_ascii=False,
                indent=2
            )

        LOG.info(f"Report saved: {report_path}")

        # Prepare response
        processing_time = round(time.time() - start_time, 2)

        response_data = {
            "report_id": report_id,
            "summary": report["summary"],
            "differences": report["differences"],
            "recommendations": report.get("recommendations", []),
            "file1_name": file1.filename,
            "file2_name": file2.filename,
            "processing_time": processing_time,
            "sentences1": serialize_sentences(sentences1),
            "sentences2": serialize_sentences(sentences2)
        }

        # Schedule cleanup
        background_tasks.add_task(cleanup_files, [file1_path, file2_path])

        return make_json_safe(response_data)

    except Exception as e:
        LOG.error(f"Comparison failed: {e}", exc_info=True)
        cleanup_files([p for p in (file1_path, file2_path) if p])
        raise HTTPException(500, f"Comparison failed: {str(e)}")


@app.post("/api/export-report")
async def export_report_endpoint(
    format: str = Form(...),
    comparison_id: str = Form(...),
    export_data: Optional[str] = Form(None)
):
    """
    Export a comparison report to PDF or Word with user comments/decisions
    """
    try:
        LOG.info(f"Export request: format={format}, comparison_id={comparison_id}")

        # Validate format
        if format not in ("pdf", "word"):
            raise HTTPException(400, "Invalid format: must be 'pdf' or 'word'")

        # Load report data
        report_path = Config.REPORT_DIR / f"{comparison_id}.json"
        if not report_path.exists():
            LOG.error(f"Report not found: {report_path}")
            # List available reports for debugging
            available = list(Config.REPORT_DIR.glob("*.json"))
            LOG.error(f"Available reports: {[f.name for f in available]}")
            raise HTTPException(404, f"Report not found: {comparison_id}")

        LOG.info(f"Loading report from {report_path}")
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        # Parse user data
        user_comments = {}
        user_decisions = {}
        global_notes = ""

        if export_data:
            try:
                parsed_data = json.loads(export_data)
                user_comments = parsed_data.get('user_comments', {})
                user_decisions = parsed_data.get('user_decisions', {})
                global_notes = parsed_data.get('global_notes', '')
                LOG.info(f"User data: {len(user_comments)} comments, {len(user_decisions)} decisions")
            except json.JSONDecodeError as e:
                LOG.warning(f"Failed to parse export_data: {e}")

        # Generate export file
        LOG.info(f"Generating {format} report...")
        try:
            if format == "pdf":
                output_path = generate_pdf_report(
                    report_data,
                    user_comments,
                    user_decisions,
                    global_notes
                )
                media_type = "application/pdf"
            else:
                output_path = generate_word_report(
                    report_data,
                    user_comments,
                    user_decisions,
                    global_notes
                )
                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except Exception as gen_error:
            LOG.error(f"Report generation failed: {gen_error}", exc_info=True)
            raise HTTPException(500, f"Report generation failed: {str(gen_error)}")

        LOG.info(f"Export generated: {output_path}")

        if not output_path.exists():
            raise HTTPException(500, "Export file generation failed - file not created")

        # Check file size
        file_size = output_path.stat().st_size
        LOG.info(f"Generated file size: {file_size} bytes")
        if file_size == 0:
            raise HTTPException(500, "Export file is empty - generation failed")

        return FileResponse(
            path=str(output_path),
            media_type=media_type,
            filename=output_path.name,
            headers={"Content-Disposition": f"attachment; filename={output_path.name}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        LOG.exception("Export failed with unexpected error")
        raise HTTPException(500, f"Export failed: {str(e)}")

# --------------------------------------------------
# Export Generation Functions
# --------------------------------------------------
def normalize_user_decisions(user_decisions: dict) -> dict:
    """
    Ensures every decision entry is a dict with keys:
    - decision
    - note
    """
    normalized = {}

    for idx, value in (user_decisions or {}).items():
        if isinstance(value, dict):
            normalized[idx] = {
                "decision": value.get("decision", "not reviewed"),
                "note": value.get("note", "")
            }
        else:
            # value is a string like "accept" / "flag"
            normalized[idx] = {
                "decision": value,
                "note": ""
            }

    return normalized

def generate_pdf_report(
    report_data: Dict,
    user_comments: Dict,
    user_decisions: Dict,
    global_notes: str
) -> Path:
    """Generate PDF report with user annotations"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        user_decisions = normalize_user_decisions(user_decisions)
        report_id = report_data.get('id', 'unknown')
        output_path = Config.EXPORT_DIR / f"{report_id}.pdf"

        # Create document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=12
        )

        # Build content
        story = []

        # Title
        story.append(Paragraph("Document Comparison Report", title_style))
        story.append(Spacer(1, 0.3*inch))

        # Metadata
        metadata = [
            ["Report ID:", report_id],
            ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Document 1:", report_data.get('file1_name', 'N/A')],
            ["Document 2:", report_data.get('file2_name', 'N/A')]
        ]

        t = Table(metadata, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*inch))

        # Global Notes
        if global_notes:
            story.append(Paragraph("📋 Document Notes", heading_style))
            story.append(Paragraph(global_notes.replace('\n', '<br/>'), styles['Normal']))
            story.append(Spacer(1, 0.2*inch))

        # Summary Statistics
        summary = report_data.get('summary', {})
        story.append(Paragraph("📊 Summary Statistics", heading_style))

        summary_data = [
            ["Overall Match", f"{summary.get('overall_match', 0)}%"],
            ["Total Differences", str(summary.get('significant_differences', 0))],
            ["Exact Matches", str(summary.get('exact_matches', 0))],
            ["Formatting Only", str(summary.get('formatting_only', 0))],
            ["OCR Errors", str(summary.get('ocr_errors', 0))],
            ["User Decisions", f"{len(user_decisions)} reviewed"]
        ]

        t = Table(summary_data, colWidths=[2.5*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*inch))

        # Differences
        differences = report_data.get('differences', [])
        if differences:
            story.append(PageBreak())
            story.append(Paragraph(f"🔍 Detailed Differences ({len(differences)})", heading_style))
            story.append(Spacer(1, 0.2*inch))

            for idx, diff in enumerate(differences):
                # 🔒 FIX: Safely extract decision
                decision_obj = user_decisions.get(str(idx), {})

                if isinstance(decision_obj, dict):
                    decision = decision_obj.get('decision') or 'not reviewed'
                else:
                    decision = str(decision_obj) if decision_obj else 'not reviewed'

                # Ensure it's a string
                decision = str(decision) if decision else 'not reviewed'

                decision_emoji = "✅" if decision == "accept" else "⚠️" if decision == "flag" else "⭐"

                diff_title = f"{decision_emoji} Difference #{idx + 1} - {diff.get('classification', 'Unknown').replace('_', ' ').title()}"
                story.append(Paragraph(diff_title, styles['Heading2']))

                # Difference details
                diff_data = [
                    ["Severity", diff.get('severity', 'unknown').upper()],
                    ["Similarity", f"{diff.get('similarity', 0):.1%}"],
                    ["Position", f"Doc1: {diff.get('position1', 'N/A')}, Doc2: {diff.get('position2', 'N/A')}"],
                    ["User Decision", decision.upper()]
                ]

                t = Table(diff_data, colWidths=[1.5*inch, 4.5*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.1*inch))

                # Texts
                if diff.get('sentence1'):
                    story.append(Paragraph("<b>Document 1:</b>", styles['Normal']))
                    story.append(Paragraph(diff['sentence1'], styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

                if diff.get('sentence2'):
                    story.append(Paragraph("<b>Document 2:</b>", styles['Normal']))
                    story.append(Paragraph(diff['sentence2'], styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

                # User comment
                comment = user_comments.get(str(idx))
                if comment:
                    story.append(Paragraph("<b>📝 Your Comment:</b>", styles['Normal']))
                    story.append(Paragraph(comment.replace('\n', '<br/>'), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

                story.append(Spacer(1, 0.2*inch))

        # Build PDF
        doc.build(story)
        LOG.info(f"PDF generated: {output_path}")
        return output_path

    except Exception as e:
        LOG.error(f"PDF generation failed: {e}", exc_info=True)
        raise


def generate_word_report(
    report_data: Dict,
    user_comments: Dict,
    user_decisions: Dict,
    global_notes: str
) -> Path:
    """Generate Word document report with user annotations"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        user_decisions = normalize_user_decisions(user_decisions)
        report_id = report_data.get('id', 'unknown')
        output_path = Config.EXPORT_DIR / f"{report_id}.docx"

        doc = Document()

        # Title
        title = doc.add_heading('Document Comparison Report', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata
        doc.add_heading('Report Information', level=1)
        table = doc.add_table(rows=4, cols=2)
        table.style = 'Light Grid Accent 1'

        table.cell(0, 0).text = "Report ID:"
        table.cell(0, 1).text = report_id
        table.cell(1, 0).text = "Generated:"
        table.cell(1, 1).text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        table.cell(2, 0).text = "Document 1:"
        table.cell(2, 1).text = report_data.get('file1_name', 'N/A')
        table.cell(3, 0).text = "Document 2:"
        table.cell(3, 1).text = report_data.get('file2_name', 'N/A')

        # Global notes
        if global_notes:
            doc.add_heading('Document Notes', level=1)
            doc.add_paragraph(global_notes)

        # Summary
        doc.add_heading('Summary Statistics', level=1)
        summary = report_data.get('summary', {})

        summary_table = doc.add_table(rows=6, cols=2)
        summary_table.style = 'Light List Accent 1'

        summary_table.cell(0, 0).text = "Overall Match"
        summary_table.cell(0, 1).text = f"{summary.get('overall_match', 0)}%"
        summary_table.cell(1, 0).text = "Total Differences"
        summary_table.cell(1, 1).text = str(summary.get('significant_differences', 0))
        summary_table.cell(2, 0).text = "Exact Matches"
        summary_table.cell(2, 1).text = str(summary.get('exact_matches', 0))
        summary_table.cell(3, 0).text = "Formatting Only"
        summary_table.cell(3, 1).text = str(summary.get('formatting_only', 0))
        summary_table.cell(4, 0).text = "OCR Errors"
        summary_table.cell(4, 1).text = str(summary.get('ocr_errors', 0))
        summary_table.cell(5, 0).text = "User Decisions"
        summary_table.cell(5, 1).text = f"{len(user_decisions)} reviewed"

        # Differences
        differences = report_data.get('differences', [])
        if differences:
            doc.add_page_break()
            doc.add_heading(f'Detailed Differences ({len(differences)})', level=1)

            for idx, diff in enumerate(differences):
                # 🔒 FIX: Safely extract decision
                decision_obj = user_decisions.get(str(idx), {})

                if isinstance(decision_obj, dict):
                    decision = decision_obj.get('decision') or 'not reviewed'
                else:
                    decision = str(decision_obj) if decision_obj else 'not reviewed'

                # Ensure it's a string
                decision = str(decision) if decision else 'not reviewed'

                decision_emoji = "✅" if decision == "accept" else "⚠️" if decision == "flag" else "⭐"

                diff_heading = doc.add_heading(
                    f"{decision_emoji} Difference #{idx + 1}",
                    level=2
                )

                # Details
                p = doc.add_paragraph()
                p.add_run(f"Type: ").bold = True
                p.add_run(f"{diff.get('classification', 'Unknown').replace('_', ' ').title()}\n")
                p.add_run(f"Severity: ").bold = True
                p.add_run(f"{diff.get('severity', 'unknown').upper()}\n")
                p.add_run(f"Similarity: ").bold = True
                p.add_run(f"{diff.get('similarity', 0):.1%}\n")
                p.add_run(f"User Decision: ").bold = True
                p.add_run(f"{decision.upper()}\n")

                # Texts
                if diff.get('sentence1'):
                    p = doc.add_paragraph()
                    p.add_run("Document 1:\n").bold = True
                    p.add_run(diff['sentence1'])

                if diff.get('sentence2'):
                    p = doc.add_paragraph()
                    p.add_run("Document 2:\n").bold = True
                    p.add_run(diff['sentence2'])

                # User comment
                comment = user_comments.get(str(idx))
                if comment:
                    p = doc.add_paragraph()
                    p.add_run("📝 Your Comment:\n").bold = True
                    p.add_run(comment)

                doc.add_paragraph()  # Spacing

        # Save
        doc.save(str(output_path))
        LOG.info(f"Word document generated: {output_path}")
        return output_path

    except Exception as e:
        LOG.error(f"Word generation failed: {e}", exc_info=True)
        raise

# --------------------------------------------------
# Utilities
# --------------------------------------------------
def normalize_for_identity(text: str) -> str:
    """
    Normalize text for identity comparison.

    This is intentionally conservative:
    - Removes case differences
    - Collapses whitespace
    - Preserves punctuation, numbers, and ordering

    Args:
        text: Raw extracted text

    Returns:
        Normalized text suitable for identity comparison
    """
    if not text:
        return ""

    # Lowercase and collapse all whitespace to single spaces
    normalized = " ".join(text.lower().split())

    LOG.debug(f"Normalized text length: {len(text)} -> {len(normalized)}")
    return normalized


def serialize_sentences(sentences: List[Dict]) -> List[Dict]:
    """Convert sentence objects to JSON-safe format"""
    serialized = []
    for sent in sentences:
        serialized.append({
            "id": int(sent.get("id", 0)),
            "text": sent["text"],
            "start_char": int(sent.get("start_char", 0)),
            "end_char": int(sent.get("end_char", 0)),
            "length": int(sent.get("length", len(sent["text"]))),
            "confidence": float(sent.get("confidence", 1.0)),
            "source": sent.get("source", "unknown"),
            "line_id": sent.get("line_id"),
            "collapsed_count": sent.get("collapsed_count", 1)
        })
    return serialized


def make_json_safe(obj):
    """Convert numpy types to Python native types"""
    import numpy as np

    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def cleanup_files(file_paths: List[Path]):
    """Delete temporary files"""
    for path in file_paths:
        if path and path.exists():
            try:
                path.unlink()
                LOG.info(f"Cleaned up: {path}")
            except Exception as e:
                LOG.warning(f"Could not delete {path}: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info" if Config.DEBUG else "warning"
    )
