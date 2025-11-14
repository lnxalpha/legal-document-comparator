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
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS: set = {
        "pdf", "png", "jpg", "jpeg", "txt"
    }
    
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
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS
    
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


# Initialize directories on import
Config.ensure_directories()
