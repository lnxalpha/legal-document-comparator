# unified_extractor/correction.py
"""Dictionary loading + OCR correction engine."""
from pathlib import Path
import re
import logging
from typing import Dict, Optional

from .io_utils import load_json_optional  # ← Change this line

LOG = logging.getLogger(__name__)

class DictionaryManager:
    _instance = None

    def __init__(self, base: Optional[Path] = None):
        self.base = base or Path(__file__).parent / "dictionaries"
        self._cache: Dict[str, dict] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self, name: str) -> dict:
        if name not in self._cache:
            self._cache[name] = load_json_optional(self.base / f"{name}.json")
            LOG.debug(f"Loaded {len(self._cache[name])} entries from {name}.json")
        return self._cache[name]

    @property
    def ocr_corrections(self):
        return self.load("ocr_corrections")

    @property
    def legal_terms(self):
        return self.load("legal_terms")

    @property
    def nigerian_terms(self):
        return self.load("nigerian_terms")

    @property
    def case_citations(self):
        return self.load("case_citations")


def apply_ocr_corrections(text: str, dm: DictionaryManager) -> str:
    if not text:
        return ""
    tokens = text.split()
    corr = dm.ocr_corrections or {}
    for i, tok in enumerate(tokens):
        key = str(tok).lower()
        if key in corr:
            rep = corr[key]
            if isinstance(rep, list) and rep:
                tokens[i] = str(rep[0])
            else:
                tokens[i] = str(rep)
    return " ".join(tokens)


def enhance_with_legal_context(text: str, dm: DictionaryManager) -> str:
    if not text:
        return ""
    terms = dm.legal_terms or {}
    if not terms:
        return str(text)
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, terms.keys())) + r")\b", re.IGNORECASE)
    return str(pattern.sub(lambda m: str(terms.get(m.group(0).lower(), m.group(0))), text))
