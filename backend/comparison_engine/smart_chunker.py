"""
Smart Chunking Module
Intelligently segments text into sentences for comparison
"""

from typing import List, Dict
from backend.config import ModelConfig, Config


def chunk_into_sentences(text: str) -> List[Dict[str, any]]:
    """
    Break text into sentences using spaCy
    
    Returns list of sentence objects with metadata:
    [
        {
            "id": 0,
            "text": "This is sentence one.",
            "start_char": 0,
            "end_char": 21,
            "length": 21
        },
        ...
    ]
    """
    if not text or not text.strip():
        return []
    
    # Load spaCy model
    nlp = ModelConfig.get_spacy_model()
    
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
                sentences.append({
                    "id": len(sentences),
                    "text": sub_sent,
                    "start_char": sent.start_char,
                    "end_char": sent.end_char,
                    "length": len(sub_sent),
                    "is_split": True
                })
        else:
            sentences.append({
                "id": idx,
                "text": sentence_text,
                "start_char": sent.start_char,
                "end_char": sent.end_char,
                "length": len(sentence_text),
                "is_split": False
            })
    
    return sentences


def split_long_sentence(sentence: str) -> List[str]:
    """
    Split abnormally long sentences (likely OCR errors)
    at natural break points
    """
    # Try splitting at semicolons, colons, or multiple spaces
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
    text = text.strip(' .,!?;:')
    
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
            "max_length": 0
        }
    
    lengths = [s["length"] for s in sentences]
    
    return {
        "total_sentences": len(sentences),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "total_chars": sum(lengths)
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
    
    sentences = chunk_into_sentences(test_text)
    
    print(f"\nFound {len(sentences)} sentences:\n")
    for sent in sentences:
        print(f"[{sent['id']}] {sent['text']}")
    
    print("\n" + "="*60)
    print("Statistics:")
    stats = get_statistics(sentences)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("Paragraph grouping:")
    paragraphs = group_sentences_by_paragraph(sentences)
    for i, para in enumerate(paragraphs, 1):
        print(f"\nParagraph {i} ({len(para)} sentences):")
        for sent in para:
            print(f"  - {sent['text'][:50]}...")
