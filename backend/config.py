"""
Configuration Management for Legal Document Comparator
Handles environment detection and settings
"""

import os
from pathlib import Path
from typing import Optional

class Config:
    """Application configuration"""

    # Base paths
    BASE_DIR = Path(__file__).parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    STATIC_DIR = BASE_DIR / "static"

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

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        cls.STATIC_DIR.mkdir(exist_ok=True)

        gitkeep = cls.UPLOAD_DIR / ".gitkeep"
        gitkeep.touch(exist_ok=True)

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        # Render sets RENDER=true
        return os.getenv("RENDER", "").lower() == "true"

    @classmethod
    def get_frontend_url(cls) -> str:
        if cls.is_production():
            return ""
        else:
            return f"http://localhost:{cls.PORT}"

    @classmethod
    def validate_file(cls, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in cls.ALLOWED_EXTENSIONS

    @classmethod
    def get_temp_filepath(cls, filename: str) -> Path:
        import uuid
        safe_filename = f"{uuid.uuid4()}_{filename}"
        return cls.UPLOAD_DIR / safe_filename

    @classmethod
    def cleanup_old_files(cls, max_age_hours: int = 24):
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


# -------------------------
# MODEL CONFIG
# -------------------------

import spacy
from sentence_transformers import SentenceTransformer

class ModelConfig:
    _sentence_model = None
    _spacy_model = None

    @staticmethod
    def get_spacy_model(model_name="en_core_web_sm"):
        """
        Load spaCy model.
        IMPORTANT: No auto-install here! Render cannot install packages at runtime.
        The model MUST be listed explicitly in requirements.txt.
        """
        try:
            return spacy.load(model_name)
        except Exception as e:
            print(f"❌ spaCy model '{model_name}' failed to load: {e}")
            print("➡ Make sure it is listed in requirements.txt!")
            return None

    @classmethod
    def get_sentence_transformer(cls):
        """Lazy load sentence transformer model"""
        if cls._sentence_model is None:
            print(f"Loading embedding model: {Config.SENTENCE_TRANSFORMER_MODEL}")
            cls._sentence_model = SentenceTransformer(Config.SENTENCE_TRANSFORMER_MODEL)
            print("✓ Loaded embedding model")
        return cls._sentence_model

    @classmethod
    def preload_models(cls):
        """Preload all models in production"""
        print("Preloading ML models...")
        cls._spacy_model = cls.get_spacy_model(Config.SPACY_MODEL)
        cls.get_sentence_transformer()
        print("✓ All models loaded")


# Initialize directories
Config.ensure_directories()
