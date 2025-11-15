"""
Legal Document Comparator - Main Application
FastAPI backend with smart document comparison
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import asyncio
from pathlib import Path

from config import Config, ModelConfig

# Initialize FastAPI app
app = FastAPI(
    title="Legal Document Comparator",
    description="Smart context-aware document verification with AI",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if Config.DEBUG else [Config.get_frontend_url()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
if Config.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(Config.STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("\n" + "="*60)
    print("🚀 Legal Document Comparator Starting...")
    print("="*60 + "\n")

    # Preload models in production for faster first request
    if Config.is_production():
        print("Production mode: Preloading ML models...")
        ModelConfig.preload_models()
    else:
        print("Development mode: Models will load on first use")

    # Schedule periodic cleanup
    print(f"Upload directory: {Config.UPLOAD_DIR}")
    print(f"Max file size: {Config.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB")
    print(f"Allowed extensions: {', '.join(Config.ALLOWED_EXTENSIONS)}")
    print("\n" + "="*60)
    print(f"✓ Server ready at http://{Config.HOST}:{Config.PORT}")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\n🛑 Shutting down...")
    Config.cleanup_old_files(max_age_hours=1)  # Clean recent files on shutdown


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    index_path = Config.STATIC_DIR / "index.html"

    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    else:
        return """
        <html>
            <head><title>Legal Document Comparator</title></head>
            <body style="font-family: Arial; padding: 50px; text-align: center;">
                <h1>📄 Legal Document Comparator</h1>
                <p>Frontend files not found in static directory.</p>
                <p>API is running. Check <a href="/docs">/docs</a> for API documentation.</p>
            </body>
        </html>
        """


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": "production" if Config.is_production() else "development",
        "models_loaded": {
            "spacy": ModelConfig._spacy_nlp is not None,
            "sentence_transformer": ModelConfig._sentence_model is not None
        }
    }


@app.get("/api/config")
async def get_config():
    """Get client configuration"""
    return {
        "max_upload_size": Config.MAX_UPLOAD_SIZE,
        "allowed_extensions": list(Config.ALLOWED_EXTENSIONS),
        "max_pages_free": Config.MAX_PAGES_FREE_TIER,
        "similarity_threshold": Config.SIMILARITY_THRESHOLD
    }


@app.post("/api/compare")
async def compare_documents(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(..., description="First document (digital/OCR)"),
    file2: UploadFile = File(..., description="Second document (digital/OCR)")
):
    """
    Compare two documents using smart semantic matching

    Returns:
        - overall_match: Percentage match (0-100)
        - matched_sentences: Number of matching sentences
        - total_sentences: Total unique sentences
        - differences: List of mismatches with context
        - processing_time: Time taken in seconds
    """
    import time
    start_time = time.time()

    # Validate files
    if not Config.validate_file(file1.filename):
        raise HTTPException(400, f"Invalid file type: {file1.filename}")
    if not Config.validate_file(file2.filename):
        raise HTTPException(400, f"Invalid file type: {file2.filename}")

    # Save uploaded files temporarily
    try:
        file1_path = Config.get_temp_filepath(file1.filename)
        file2_path = Config.get_temp_filepath(file2.filename)

        # Save files
        with open(file1_path, "wb") as f:
            content = await file1.read()
            if len(content) > Config.MAX_UPLOAD_SIZE:
                raise HTTPException(400, f"File too large: {file1.filename}")
            f.write(content)

        with open(file2_path, "wb") as f:
            content = await file2.read()
            if len(content) > Config.MAX_UPLOAD_SIZE:
                raise HTTPException(400, f"File too large: {file2.filename}")
            f.write(content)

        # Import comparison engine (lazy import to speed up startup)
        from comparison_engine.text_extractor import extract_text
        from comparison_engine.smart_chunker import chunk_into_sentences
        from comparison_engine.semantic_matcher import match_documents
        from comparison_engine.report_generator import generate_report

        # Step 1: Extract text
        print(f"📄 Extracting text from {file1.filename}...")
        text1 = await extract_text(file1_path)

        print(f"📄 Extracting text from {file2.filename}...")
        text2 = await extract_text(file2_path)

        if not text1 or not text2:
            raise HTTPException(400, "Could not extract text from one or both documents")

        # Step 2: Chunk into sentences
        print("✂️  Chunking into sentences...")
        sentences1 = chunk_into_sentences(text1)
        sentences2 = chunk_into_sentences(text2)

        print(f"   Document 1: {len(sentences1)} sentences")
        print(f"   Document 2: {len(sentences2)} sentences")

        # Step 3: Semantic matching
        print("🧠 Performing semantic matching...")
        matches = match_documents(sentences1, sentences2)

        # Step 4: Generate report
        print("📊 Generating report...")
        report = generate_report(matches, sentences1, sentences2)

        processing_time = time.time() - start_time
        report["processing_time"] = round(processing_time, 2)
        report["file1_name"] = file1.filename
        report["file2_name"] = file2.filename

        print(f"✓ Comparison complete in {processing_time:.2f}s")
        report["overall_match"] = report["summary"]["overall_match"]
        print(f"  Match: {report['overall_match']:.1f}%")

        # Schedule cleanup of uploaded files
        background_tasks.add_task(cleanup_files, [file1_path, file2_path])

        return JSONResponse(content=report)

    except Exception as e:
        # Clean up files on error
        for path in [file1_path, file2_path]:
            if path.exists():
                path.unlink()

        print(f"❌ Error: {str(e)}")
        raise HTTPException(500, f"Comparison failed: {str(e)}")


@app.post("/api/extract-text")
async def extract_text_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document to extract text from")
):
    """
    Extract text from a document (useful for testing OCR)
    """
    if not Config.validate_file(file.filename):
        raise HTTPException(400, f"Invalid file type: {file.filename}")

    try:
        file_path = Config.get_temp_filepath(file.filename)

        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            if len(content) > Config.MAX_UPLOAD_SIZE:
                raise HTTPException(400, "File too large")
            f.write(content)

        # Extract text
        from comparison_engine.text_extractor import extract_text
        text = await extract_text(file_path)

        # Cleanup
        background_tasks.add_task(cleanup_files, [file_path])

        return {
            "filename": file.filename,
            "text": text,
            "length": len(text),
            "preview": text[:500] + "..." if len(text) > 500 else text
        }

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(500, f"Text extraction failed: {str(e)}")

def cleanup_files(file_paths: List[Path]):
    """Background task to clean up temporary files"""
    for path in file_paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete {path}: {e}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info" if Config.DEBUG else "warning"
    )
