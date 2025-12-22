"""
Configuration Management for Legal Document Comparator
Handles environment detection and settings
Phase 1: Added quality metrics and enhanced thresholds
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import logging

class Config:
    """Application configuration"""

    # Base paths
    BASE_DIR = Path(__file__).resolve().parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    STATIC_DIR = BASE_DIR / "static"
    REPORT_DIR = BASE_DIR / "reports"
    EXPORT_DIR = BASE_DIR / "exports"

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # File upload settings
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".doc", ".docx"}

    # Model settings
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
    SENTENCE_TRANSFORMER_MODEL: str = os.getenv(
        "SENTENCE_TRANSFORMER_MODEL",
        "all-MiniLM-L6-v2"
    )

    # OCR settings
    TESSERACT_PATH: Optional[str] = os.getenv("TESSERACT_PATH", None)

    # Comparison thresholds
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", 0.85))
    CONTEXT_WINDOW: int = int(os.getenv("CONTEXT_WINDOW", 2))

    # Performance settings
    MAX_PAGES_FREE_TIER: int = 10
    MAX_SENTENCE_LENGTH: int = 500  # Characters

    # Semantic matching thresholds
    SIMILARITY_THRESHOLD: float = 0.85
    MERGE_SIMILARITY_THRESHOLD: float = 0.92
    RELOCATED_SIMILARITY_THRESHOLD: float = 0.95
    CONTEXT_SUPPORT_THRESHOLD: float = 0.70
    WIDER_CONTEXT_THRESHOLD: float = 0.65

    HIGH_SIMILARITY_THRESHOLD: float = 0.95     # For detailed diff analysis
    REWORDING_THRESHOLD: float = 0.85           # Rewording vs significant change

     # ====== SUBSTRING DETECTION ======
    MIN_SUBSTRING_LENGTH: int = 20              # Minimum chars for substring match
    MIN_NORMALIZED_LENGTH: int = 15             # Minimum for normalized substring
    MERGE_LENGTH_RATIO: float = 1.3             # Target must be 1.3x longer

    # OCR thresholds
    OCR_CONFIDENCE_THRESHOLD: float = 0.70
    OCR_SIMILARITY_THRESHOLD: float = 0.90

    # ========== PHASE 1 ADDITIONS ==========
    # Quality thresholds for provenance tracking
    MIN_SENTENCE_CONFIDENCE: float = 0.5  # Flag sentences below this
    WARN_OVERALL_CONFIDENCE: float = 0.7  # Warn if doc confidence below this
    # =======================================

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        cls.STATIC_DIR.mkdir(exist_ok=True)

        # Create .gitkeep in uploads
        gitkeep = cls.UPLOAD_DIR / ".gitkeep"
        gitkeep.touch(exist_ok=True)

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return os.getenv("RENDER", False) or not cls.DEBUG

    @classmethod
    def get_frontend_url(cls) -> str:
        """Get the appropriate frontend URL"""
        if cls.is_production():
            # In production, frontend is served by same backend
            return ""
        else:
            # Local development
            return f"http://localhost:{cls.PORT}"

    @classmethod
    def validate_file(cls, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in cls.ALLOWED_EXTENSIONS

    @classmethod
    def get_temp_filepath(cls, filename: str) -> Path:
        """Generate temporary file path for uploads"""
        import uuid
        safe_filename = f"{uuid.uuid4()}_{filename}"
        return cls.UPLOAD_DIR / safe_filename

    @classmethod
    def cleanup_old_files(cls, max_age_hours: int = 24):
        """Remove old uploaded files"""
        import time
        current_time = time.time()

        for filepath in cls.UPLOAD_DIR.glob("*"):
            if filepath.name == ".gitkeep":
                continue

            file_age = current_time - filepath.stat().st_mtime
            if file_age > (max_age_hours * 3600):
                try:
                    filepath.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete {filepath}: {e}")


class ModelConfig:
    """ML Model configuration and lazy loading"""

    _spacy_nlp = None
    _sentence_model = None

    @classmethod
    def get_spacy(cls):
        """Lazy load spaCy model"""
        if cls._spacy_nlp is None:
            import spacy
            try:
                cls._spacy_nlp = spacy.load(Config.SPACY_MODEL)
                print(f"✓ Loaded spaCy model: {Config.SPACY_MODEL}")
            except OSError:
                print(f"⚠️  Model {Config.SPACY_MODEL} not found!")
                print("   Run: python -m spacy download en_core_web_sm")
                raise
        return cls._spacy_nlp

    @classmethod
    def get_sentence_transformer(cls):
        """Lazy load sentence transformer model"""
        if cls._sentence_model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {Config.SENTENCE_TRANSFORMER_MODEL}")
            print("(This may take a minute on first run...)")
            cls._sentence_model = SentenceTransformer(
                Config.SENTENCE_TRANSFORMER_MODEL
            )
            print(f"✓ Loaded embedding model")
        return cls._sentence_model

    @classmethod
    def preload_models(cls):
        """Preload all models (useful for production)"""
        print("Preloading ML models...")
        cls.get_spacy()
        cls.get_sentence_transformer()
        print("✓ All models loaded")


# ========== PHASE 1 ADDITIONS: LOGGING & QUALITY METRICS ==========

def setup_logging(level=logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Reduce noise from libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('easyocr').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)


@dataclass
class QualityMetrics:
    """Track quality metrics for provenance."""
    total_sentences: int = 0
    low_confidence_sentences: int = 0
    ocr_sentences: int = 0
    direct_sentences: int = 0
    failed_sentences: int = 0
    avg_confidence: float = 0.0

    def quality_score(self) -> float:
        """Calculate overall quality score (0-1)."""
        if self.total_sentences == 0:
            return 0.0

        # Penalize low confidence and failures
        penalty = (self.low_confidence_sentences + self.failed_sentences * 2) / self.total_sentences

        return max(0.0, self.avg_confidence - penalty * 0.2)

    def quality_label(self) -> str:
        """Get human-readable quality label."""
        score = self.quality_score()

        if score >= 0.9:
            return "excellent"
        elif score >= 0.75:
            return "good"
        elif score >= 0.6:
            return "fair"
        elif score >= 0.4:
            return "poor"
        else:
            return "very_poor"


# ========== PATHS FOR TESTS ==========
DICTIONARIES_DIR = Config.BASE_DIR / "unified_extractor" / "dictionaries"
TESTS_DIR = Config.BASE_DIR / "tests"
GOLDEN_SAMPLES_DIR = TESTS_DIR / "golden_samples"

# =====================================================

# Initialize directories on import
Config.ensure_directories()
