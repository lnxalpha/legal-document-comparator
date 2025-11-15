"""
Lightweight Semantic Matching Module
Uses TF-IDF instead of heavy transformers - fits in 512MB RAM
Still provides good accuracy for document comparison
"""

from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config
from comparison_engine.smart_chunker import normalize_sentence


def match_documents(
    sentences1: List[Dict],
    sentences2: List[Dict]
) -> Dict:
    """
    Match sentences between two documents using TF-IDF similarity
    Memory efficient - no heavy ML models needed
    
    Returns:
        {
            "matches": [...],
            "only_in_doc1": [...],
            "only_in_doc2": [...],
            "match_score": 0.95
        }
    """
    if not sentences1 or not sentences2:
        return {
            "matches": [],
            "only_in_doc1": sentences1,
            "only_in_doc2": sentences2,
            "match_score": 0.0
        }
    
    print(f"   Computing TF-IDF vectors for {len(sentences1)} + {len(sentences2)} sentences...")
    
    # Get sentence texts
    texts1 = [s["text"] for s in sentences1]
    texts2 = [s["text"] for s in sentences2]
    
    # Create TF-IDF vectors (lightweight!)
    vectorizer = TfidfVectorizer(
        max_features=1000,  # Limit features for memory
        ngram_range=(1, 2),  # Unigrams and bigrams
        lowercase=True,
        stop_words='english'
    )
    
    # Fit on all sentences
    all_texts = texts1 + texts2
    vectorizer.fit(all_texts)
    
    # Transform to vectors
    vectors1 = vectorizer.transform(texts1)
    vectors2 = vectorizer.transform(texts2)
    
    print(f"   Finding best matches...")
    
    # Find matches
    matches, unmatched1, unmatched2 = find_best_matches(
        sentences1, sentences2,
        vectors1, vectors2
    )
    
    # Calculate overall match score
    total_sentences = len(sentences1) + len(sentences2)
    matched_count = len(matches) * 2
    match_score = matched_count / total_sentences if total_sentences > 0 else 0.0
    
    return {
        "matches": matches,
        "only_in_doc1": unmatched1,
        "only_in_doc2": unmatched2,
        "match_score": match_score
    }


def find_best_matches(
    sentences1: List[Dict],
    sentences2: List[Dict],
    vectors1,
    vectors2
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Find optimal sentence matches using TF-IDF cosine similarity
    """
    # Compute similarity matrix
    similarity_matrix = cosine_similarity(vectors1, vectors2)
    
    matches = []
    used_indices1 = set()
    used_indices2 = set()
    
    # Greedy matching: find best matches first
    similarity_scores = []
    for i in range(len(sentences1)):
        for j in range(len(sentences2)):
            similarity_scores.append((similarity_matrix[i, j], i, j))
    
    # Sort by similarity (highest first)
    similarity_scores.sort(reverse=True)
    
    for similarity, i, j in similarity_scores:
        # Skip if below threshold
        if similarity < Config.SIMILARITY_THRESHOLD:
            break
        
        # Skip if already matched
        if i in used_indices1 or j in used_indices2:
            continue
        
        # Check context validity
        context_valid = check_context_validity(
            i, j, similarity_matrix, used_indices1, used_indices2
        )
        
        if context_valid:
            matches.append({
                "sent1": sentences1[i],
                "sent2": sentences2[j],
                "similarity": float(similarity),
                "index1": i,
                "index2": j,
                "exact_match": sentences1[i]["text"] == sentences2[j]["text"],
                "normalized_match": normalize_sentence(sentences1[i]["text"]) == 
                                   normalize_sentence(sentences2[j]["text"])
            })
            used_indices1.add(i)
            used_indices2.add(j)
    
    # Get unmatched sentences
    unmatched1 = [s for i, s in enumerate(sentences1) if i not in used_indices1]
    unmatched2 = [s for i, s in enumerate(sentences2) if i not in used_indices2]
    
    return matches, unmatched1, unmatched2


def check_context_validity(
    idx1: int,
    idx2: int,
    similarity_matrix: np.ndarray,
    used1: set,
    used2: set
) -> bool:
    """
    Check if a match makes sense in context
    """
    window = Config.CONTEXT_WINDOW
    
    context_support = 0
    context_checks = 0
    
    for offset in range(-window, window + 1):
        if offset == 0:
            continue
        
        i = idx1 + offset
        j = idx2 + offset
        
        if 0 <= i < similarity_matrix.shape[0] and 0 <= j < similarity_matrix.shape[1]:
            if i not in used1 and j not in used2:
                context_checks += 1
                if similarity_matrix[i, j] > 0.7:
                    context_support += 1
    
    if context_checks >= 2 and context_support == 0:
        return False
    
    return True


def classify_difference(match: Dict) -> str:
    """
    Classify the type of difference between matched sentences
    """
    similarity = match["similarity"]
    
    if match["exact_match"]:
        return "exact_match"
    elif match["normalized_match"]:
        return "minor_difference"
    elif similarity > 0.95:
        return "minor_difference"
    elif similarity > 0.85:
        return "rewording"
    else:
        return "significant"


def analyze_match_quality(matches: List[Dict]) -> Dict:
    """
    Analyze the quality of matches
    """
    if not matches:
        return {
            "total_matches": 0,
            "exact_matches": 0,
            "minor_differences": 0,
            "rewordings": 0,
            "significant_differences": 0,
            "avg_similarity": 0.0
        }
    
    classifications = {
        "exact_match": 0,
        "minor_difference": 0,
        "rewording": 0,
        "significant": 0
    }
    
    for match in matches:
        classification = classify_difference(match)
        classifications[classification] += 1
    
    avg_similarity = sum(m["similarity"] for m in matches) / len(matches)
    
    return {
        "total_matches": len(matches),
        "exact_matches": classifications["exact_match"],
        "minor_differences": classifications["minor_difference"],
        "rewordings": classifications["rewording"],
        "significant_differences": classifications["significant"],
        "avg_similarity": avg_similarity
    }


def find_potential_reorderings(matches: List[Dict]) -> List[Dict]:
    """
    Detect sentences that appear in different order
    """
    reorderings = []
    
    for match in matches:
        expected_order = match["index1"]
        actual_order = match["index2"]
        
        if abs(expected_order - actual_order) > Config.CONTEXT_WINDOW * 2:
            reorderings.append({
                "sentence": match["sent1"]["text"],
                "expected_position": expected_order,
                "actual_position": actual_order,
                "displacement": actual_order - expected_order
            })
    
    return reorderings


def suggest_corrections(match: Dict) -> List[str]:
    """
    Suggest what might have caused the difference
    """
    sent1 = match["sent1"]["text"]
    sent2 = match["sent2"]["text"]
    
    suggestions = []
    
    # Check for common OCR errors
    common_ocr_errors = [
        ("l", "1"), ("O", "0"), ("S", "5"),
        ("I", "1"), ("Z", "2"), ("B", "8")
    ]
    
    for char1, char2 in common_ocr_errors:
        if char1 in sent1 and char2 in sent2:
            suggestions.append(f"Possible OCR error: '{char1}' → '{char2}'")
        if char2 in sent1 and char1 in sent2:
            suggestions.append(f"Possible OCR error: '{char2}' → '{char1}'")
    
    # Check length difference
    len_diff = abs(len(sent1) - len(sent2))
    if len_diff > 10:
        suggestions.append(f"Length difference: {len_diff} characters")
    
    # Check word count difference
    words1 = len(sent1.split())
    words2 = len(sent2.split())
    if abs(words1 - words2) > 3:
        suggestions.append(f"Word count difference: {words1} vs {words2} words")
    
    return suggestions
