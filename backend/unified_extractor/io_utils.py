# unified_extractor/io_utils.py
"""Pure I/O utilities with zero internal dependencies."""
import json
import logging
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)

def load_json_optional(path: Path) -> dict:
    """Load JSON file, return {} on any error."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        LOG.warning(f"Failed to load {path}: {e}")
    return {}

def validate_file_path(path: Path, allowed: Optional[set] = None):
    """Validate file exists and has allowed extension."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if allowed and path.suffix.lower() not in allowed:
        raise ValueError(f"Unsupported file type: {path.suffix}")
