"""
Smart Chunking Module
Intelligently segments text into sentences with provenance tracking
"""

from typing import List, Dict, Optional
from config import ModelConfig, Config
import re

def chunk_into_sentences(
    text: str,
    provenance: Optional[Dict] = None
) -> List[Dict[str, any]]:
    """
    Break text into sentences using spaCy, preserving provenance.

    Args:
        text: Input text to chunk
        provenance: Optional provenance data from extractor
            {
                "confidence": 0.85,
                "method": "ocr",
                "lines": [...],
                "warnings": [...]
            }

    Returns list of sentence objects with metadata:
    [
        {
            "id": 0,
            "text": "This is sentence one.",
            "start_char": 0,
            "end_char": 21,
            "length": 21,
            "is_split": False,
            "source": "ocr",  # NEW
            "confidence": 0.85,  # NEW
            "line_id": 0,  # NEW (if from OCR line)
        },
        ...
    ]
    """
    if not text or not text.strip():
        return []

    # Load spaCy model
    nlp = ModelConfig.get_spacy()

    # Process text
    doc = nlp(text)

    sentences = []
    for idx, sent in enumerate(doc.sents):
        sentence_text = sent.text.strip()

        # Skip empty or very short sentences
        if len(sentence_text) < 3:
            continue

        # Skip if too long (likely extraction error)
        if len(sentence_text) > Config.MAX_SENTENCE_LENGTH:
            # Split long sentences
            sub_sentences = split_long_sentence(sentence_text)
            for sub_sent in sub_sentences:
                sentence_dict = {
                    "id": len(sentences),
                    "text": sub_sent,
                    "start_char": sent.start_char,
                    "end_char": sent.end_char,
                    "length": len(sub_sent),
                    "is_split": True
                }

                # Add provenance if available
                if provenance:
                    sentence_dict.update(_add_provenance_to_sentence(
                        sentence_dict, provenance, sent.start_char
                    ))

                sentences.append(sentence_dict)
        else:
            sentence_dict = {
                "id": idx,
                "text": sentence_text,
                "start_char": sent.start_char,
                "end_char": sent.end_char,
                "length": len(sentence_text),
                "is_split": False
            }

            # Add provenance if available
            if provenance:
                sentence_dict.update(_add_provenance_to_sentence(
                    sentence_dict, provenance, sent.start_char
                ))

            sentences.append(sentence_dict)

    sentences = collapse_name_lists(sentences)
    return sentences


def _add_provenance_to_sentence(
    sentence: Dict,
    provenance: Dict,
    char_position: int
) -> Dict:
    """
    Add provenance metadata to a sentence.

    Tries to match sentence to specific OCR line if available.
    """
    metadata = {
        "source": provenance.get("method", "unknown"),
        "confidence": provenance.get("confidence", 1.0),
        "line_id": None,
        "ocr_method": None
    }

    # Try to match to specific line
    lines = provenance.get("lines", [])
    if lines:
        # Find which line this sentence likely came from
        # (Simple heuristic: find line whose text is contained in sentence or vice versa)
        for line in lines:
            line_text = line.get("text", "")
            if line_text and (line_text in sentence["text"] or sentence["text"] in line_text):
                metadata["line_id"] = line.get("line_id")
                metadata["confidence"] = line.get("confidence", metadata["confidence"])
                metadata["ocr_method"] = line.get("ocr_method")
                break

    return metadata


def split_long_sentence(sentence: str) -> List[str]:
    """
    Split abnormally long sentences (likely OCR errors)
    at natural break points
    """
    import re

    # First try semicolons
    if ';' in sentence:
        parts = [p.strip() for p in sentence.split(';') if p.strip()]
        if all(len(p) < Config.MAX_SENTENCE_LENGTH for p in parts):
            return parts

    # Then try colons
    if ':' in sentence:
        parts = [p.strip() for p in sentence.split(':') if p.strip()]
        if all(len(p) < Config.MAX_SENTENCE_LENGTH for p in parts):
            return parts

    # Last resort: chunk by character limit
    max_len = Config.MAX_SENTENCE_LENGTH
    return [sentence[i:i+max_len] for i in range(0, len(sentence), max_len)]


def get_sentence_context(
    sentences: List[Dict],
    index: int,
    window: int = 1
) -> Dict[str, List[str]]:
    """
    Get surrounding sentences for context analysis

    Args:
        sentences: List of sentence dicts
        index: Target sentence index
        window: Number of sentences before/after

    Returns:
        {
            "before": ["sentence before", ...],
            "target": "target sentence",
            "after": ["sentence after", ...]
        }
    """
    before = []
    after = []

    # Get sentences before
    for i in range(max(0, index - window), index):
        before.append(sentences[i]["text"])

    # Get sentences after
    for i in range(index + 1, min(len(sentences), index + window + 1)):
        after.append(sentences[i]["text"])

    return {
        "before": before,
        "target": sentences[index]["text"],
        "after": after
    }


def normalize_sentence(sentence: str) -> str:
    """
    Normalize sentence for better matching
    - Convert to lowercase
    - Remove extra whitespace
    - Strip punctuation from ends
    """
    import re

    # Lowercase
    text = sentence.lower()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Strip punctuation from ends
    text = text.strip(' .,!?;:\'"')

    return text


def are_sentences_similar_simple(sent1: str, sent2: str) -> float:
    """
    Quick similarity check without ML (for pre-filtering)
    Uses Jaccard similarity on words

    Returns: 0.0 to 1.0
    """
    import re

    # Tokenize into words
    words1 = set(re.findall(r'\w+', sent1.lower()))
    words2 = set(re.findall(r'\w+', sent2.lower()))

    if not words1 or not words2:
        return 0.0

    # Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)


def group_sentences_by_paragraph(sentences: List[Dict]) -> List[List[Dict]]:
    """
    Group sentences into paragraphs based on character positions
    Useful for understanding document structure
    """
    if not sentences:
        return []

    paragraphs = []
    current_paragraph = [sentences[0]]

    for i in range(1, len(sentences)):
        prev_sent = sentences[i-1]
        curr_sent = sentences[i]

        # Check gap between sentences
        gap = curr_sent["start_char"] - prev_sent["end_char"]

        # New paragraph if gap > 2 characters (likely double newline)
        if gap > 2:
            paragraphs.append(current_paragraph)
            current_paragraph = [curr_sent]
        else:
            current_paragraph.append(curr_sent)

    # Add last paragraph
    if current_paragraph:
        paragraphs.append(current_paragraph)

    return paragraphs


def get_statistics(sentences: List[Dict]) -> Dict:
    """
    Get statistics about the chunked text
    """
    if not sentences:
        return {
            "total_sentences": 0,
            "avg_length": 0,
            "min_length": 0,
            "max_length": 0,
            "avg_confidence": 0.0,
            "low_confidence_count": 0
        }

    lengths = [s["length"] for s in sentences]
    confidences = [s.get("confidence", 1.0) for s in sentences]

    return {
        "total_sentences": len(sentences),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "total_chars": sum(lengths),
        "avg_confidence": sum(confidences) / len(confidences),
        "low_confidence_count": sum(1 for c in confidences if c < 0.7)
    }


# For testing
if __name__ == "__main__":
    # Test text
    test_text = """
    This is the first sentence. This is the second sentence.

    This is a new paragraph. It has multiple sentences. Like this one.

    And a final paragraph here.
    """

    print("Testing smart chunking...")
    print("="*60)

    # Test with mock provenance
    mock_provenance = {
        "confidence": 0.85,
        "method": "ocr",
        "lines": [
            {"text": "This is the first sentence.", "confidence": 0.9, "line_id": 0, "ocr_method": "tesseract"},
            {"text": "This is the second sentence.", "confidence": 0.8, "line_id": 1, "ocr_method": "easyocr"}
        ]
    }

    sentences = chunk_into_sentences(test_text, provenance=mock_provenance)

    print(f"\nFound {len(sentences)} sentences:\n")
    for sent in sentences:
        conf = sent.get("confidence", "N/A")
        method = sent.get("ocr_method", "N/A")
        print(f"[{sent['id']}] {sent['text']}")
        print(f"  Confidence: {conf}, Method: {method}")

    print("\n" + "="*60)
    print("Statistics:")
    stats = get_statistics(sentences)
    for key, value in stats.items():
        print(f"  {key}: {value}")

def _is_name_list_line(sentence: Dict) -> bool:
    """
    Heuristic to detect legal name / party list lines.
    """
    text = sentence["text"].strip()

    # Mostly uppercase
    if text.upper() != text:
        return False

    # Short-ish lines
    if len(text) > 80:
        return False

    # Ends with number or period (common in counsel lists)
    if not re.search(r'\d+\.?$', text):
        return False

    # No verbs (very rough but effective)
    if re.search(r'\b(is|was|were|are|has|have|held|finds)\b', text.lower()):
        return False

    return True


def collapse_name_lists(sentences: List[Dict]) -> List[Dict]:
    """
    Merge consecutive name-list sentences into a single sentence.
    """
    collapsed = []
    buffer = []

    for sent in sentences:
        if _is_name_list_line(sent):
            buffer.append(sent)
        else:
            if buffer:
                merged_text = " ".join(s["text"] for s in buffer)
                first = buffer[0]
                last = buffer[-1]

                collapsed.append({
                    **first,
                    "text": merged_text,
                    "end_char": last["end_char"],
                    "length": len(merged_text),
                    "is_split": True,
                    "collapsed_count": len(buffer)
                })
                buffer = []

            collapsed.append(sent)

    # Flush buffer
    if buffer:
        merged_text = " ".join(s["text"] for s in buffer)
        first = buffer[0]
        last = buffer[-1]

        collapsed.append({
            **first,
            "text": merged_text,
            "end_char": last["end_char"],
            "length": len(merged_text),
            "is_split": True,
            "collapsed_count": len(buffer)
        })

    return collapsed
