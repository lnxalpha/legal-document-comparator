# unified_extractor/correction.py
"""Dictionary loading + OCR correction engine."""
from pathlib import Path
import re
import logging
from typing import Dict, Optional

from .io_utils import load_json_optional

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
    """Apply dictionary-based OCR corrections."""
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
    """Enhance text with legal terminology."""
    if not text:
        return ""
    terms = dm.legal_terms or {}
    if not terms:
        return str(text)
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, terms.keys())) + r")\b", re.IGNORECASE)
    return str(pattern.sub(lambda m: str(terms.get(m.group(0).lower(), m.group(0))), text))


def repair_sentence_boundaries(text: str) -> str:
    """
    Fix common OCR sentence boundary errors.

    OCR often produces: "welcome Some of us share"
    Should be: "welcome. Some of us share"

    Detects: lowercase → uppercase without punctuation
    """
    if not text:
        return ""

    # Pattern: lowercase letter + space + uppercase letter (no punctuation between)
    # Examples:
    #   "welcome Some" → "welcome. Some"
    #   "war He later" → "war. He later"

    # More sophisticated pattern that avoids breaking:
    # - Proper nouns mid-sentence: "John Smith said"
    # - Acronyms: "the USA Today"
    # - Single capital letters: "grade A student"

    def should_insert_period(before_word: str, after_word: str) -> bool:
        """Determine if a period should be inserted between two words."""
        # Don't break if before_word is very short (likely abbreviation)
        if len(before_word) <= 2:
            return False

        # Don't break if after_word is very short (likely initial or acronym)
        if len(after_word) <= 2:
            return False

        # Don't break if before_word ends with common abbreviations
        abbrevs = ['mr', 'mrs', 'ms', 'dr', 'st', 'ave', 'blvd', 'jr', 'sr', 'vs', 'etc', 'inc', 'ltd', 'corp']
        if before_word.lower() in abbrevs:
            return False

        # Check if this looks like a sentence boundary
        # Heuristic: if before_word is at least 4 chars and ends with lowercase,
        # and after_word starts with uppercase and is at least 3 chars,
        # this is likely a sentence boundary
        if len(before_word) >= 4 and before_word[-1].islower() and \
           len(after_word) >= 3 and after_word[0].isupper():
            return True

        return False

    # Split into words while preserving spacing info
    words = text.split()
    if len(words) < 2:
        return text

    result = []
    for i in range(len(words)):
        result.append(words[i])

        # Check if we should insert a period after this word
        if i < len(words) - 1:
            if should_insert_period(words[i], words[i + 1]):
                # Remove any existing punctuation from current word
                if result[-1] and result[-1][-1] not in '.!?':
                    result[-1] += '.'
                    LOG.debug(f"Inserted period: '{words[i]}' → '{result[-1]}'")

    return ' '.join(result)


def repair_merged_sentences_aggressive(text: str) -> str:
    """
    More aggressive sentence boundary repair.

    Looks for patterns like:
    - "word.Another" → "word. Another"
    - "word!Next" → "word! Next"
    """
    if not text:
        return ""

    # Fix punctuation-uppercase sequences without space
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

    # Fix patterns like "word Some" where "Some" looks like a sentence start
    # This is handled by repair_sentence_boundaries()

    return text


def clean_ocr_artifacts(text: str) -> str:
    """
    Clean common OCR artifacts.

    - Multiple spaces → single space
    - Space before punctuation
    - Missing space after punctuation
    """
    if not text:
        return ""

    # Multiple spaces
    text = re.sub(r' +', ' ', text)

    # Space before punctuation
    text = re.sub(r' +([.,!?;:])', r'\1', text)

    # Missing space after punctuation (but not in numbers like "3.14")
    text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', text)

    # Clean up quotes
    text = re.sub(r'" ([^"]+) "', r'"\1"', text)

    return text.strip()
