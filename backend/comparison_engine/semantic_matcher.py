"""
Semantic Matching Module
Uses AI embeddings to match sentences between documents
Phase 2: Added fuzzy boundary matching and bidirectional containment
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
import re

from config import ModelConfig, Config
from comparison_engine.smart_chunker import normalize_sentence
from unified_extractor.correction import DictionaryManager

LOG = logging.getLogger(__name__)

# ======================================================
# Model Cache (PERFORMANCE FIX)
# ======================================================
_EMBEDDING_MODEL = None

def get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = ModelConfig.get_sentence_transformer()
    return _EMBEDDING_MODEL


def match_documents(
    sentences1: List[Dict],
    sentences2: List[Dict]
) -> Dict:
    """
    Match sentences between two documents using semantic similarity

    Phase 2: Now includes fuzzy boundary matching to detect merged sentences

    Returns:
        {
            "matches": [...],  # List of matched sentence pairs
            "only_in_doc1": [...],  # Sentences only in document 1 (after fuzzy check)
            "only_in_doc2": [...],  # Sentences only in document 2 (after fuzzy check)
            "merged_in_doc1": [...],  # Sentences merged from doc2 into doc1
            "merged_in_doc2": [...],  # Sentences merged from doc1 into doc2
            "match_score": 0.95  # Overall match percentage
        }
    """
    if not sentences1 or not sentences2:
        return {
            "matches": [],
            "only_in_doc1": sentences1,
            "only_in_doc2": sentences2,
            "merged_in_doc1": [],
            "merged_in_doc2": [],
            "multi_merges_doc1": [],  # NEW
            "multi_merges_doc2": [],  # NEW
            "match_score": 0.0
        }

    LOG.info(f"Computing embeddings for {len(sentences1)} + {len(sentences2)} sentences...")

    # Get sentence texts
    texts1 = [s["text"] for s in sentences1]
    texts2 = [s["text"] for s in sentences2]

    # Get embeddings
    model = get_embedding_model()
    embeddings1 = model.encode(texts1, show_progress_bar=False)
    embeddings2 = model.encode(texts2, show_progress_bar=False)

    LOG.info(f"Finding best matches...")

    # Find matches using Hungarian algorithm approach
    matches, unmatched1, unmatched2 = find_best_matches(
        sentences1, sentences2,
        embeddings1, embeddings2
    )

    # PHASE 2: Check for merged sentences before marking as "only_in"
    LOG.info("Checking for merged sentences...")

    merged_in_doc2, still_unmatched1 = find_merged_sentences(
        unmatched1, sentences2, embeddings2
    )

    merged_in_doc1, still_unmatched2 = find_merged_sentences(
        unmatched2, sentences1, embeddings1
    )

    # Check for multi-sentence merges
    multi_merges_doc2 = find_bidirectional_merges(merged_in_doc2, sentences1)
    multi_merges_doc1 = find_bidirectional_merges(merged_in_doc1, sentences2)

    LOG.info(f"Found {len(multi_merges_doc2)} multi-merges in doc2")
    LOG.info(f"Found {len(multi_merges_doc1)} multi-merges in doc1")

    # PHASE 2: Cross-document search for identical content at different positions
    LOG.info("Cross-document search for relocated sentences...")

    relocated_matches1, truly_only_in_doc1 = find_relocated_sentences(
        still_unmatched1, sentences2, embeddings2
    )

    relocated_matches2, truly_only_in_doc2 = find_relocated_sentences(
        still_unmatched2, sentences1, embeddings1
    )

    # Add relocated matches to main matches list
    matches.extend(relocated_matches1)
    matches.extend(relocated_matches2)

    # Calculate overall match score
    total_sentences = len(sentences1) + len(sentences2)
    matched_doc1 = {m["index1"] for m in matches if "index1" in m}
    matched_doc2 = {m["index2"] for m in matches if "index2" in m}
    matched_count = len(matched_doc1) + len(matched_doc2)
    # Each match counts for both documents
    match_score = matched_count / total_sentences if total_sentences > 0 else 0.0

    return {
        "matches": matches,
        "only_in_doc1": truly_only_in_doc1,
        "only_in_doc2": truly_only_in_doc2,
        "merged_in_doc1": merged_in_doc1,
        "merged_in_doc2": merged_in_doc2,
        "multi_merges_doc1": multi_merges_doc1,
        "multi_merges_doc2": multi_merges_doc2,
        "match_score": match_score
    }

def is_statute_reference(text: str, statutes: dict) -> bool:
    """Check if text matches statute reference patterns"""
    for pattern in statutes.get("patterns", []):
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def find_best_matches(
    sentences1: List[Dict],
    sentences2: List[Dict],
    embeddings1: np.ndarray,
    embeddings2: np.ndarray
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Find optimal sentence matches between documents

    Returns:
        (matches, unmatched_from_doc1, unmatched_from_doc2)
    """
    # Compute similarity matrix
    similarity_matrix = cosine_similarity(embeddings1, embeddings2)

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

        # Check context (are surrounding sentences also matching?)
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
    Check if a match makes sense in context.
    Sentences should appear in roughly the same order.

    Phase 2: Enhanced with fallback check for larger reorderings.
    """
    window = Config.CONTEXT_WINDOW

    # Check if nearby sentences also have high similarity
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
                if similarity_matrix[i, j] > Config.CONTEXT_SUPPORT_THRESHOLD:
                    context_support += 1

    # PHASE 2: Fallback check - if no local context, check ANY surrounding sentences
    if context_checks == 0 or context_support / context_checks < 0.3:
        wider_window = Config.CONTEXT_WINDOW * 2
        wider_support = 0
        wider_checks = 0

        for offset in range(-wider_window, wider_window + 1):
            if offset == 0:
                continue

            i = idx1 + offset
            j = idx2 + offset

            if 0 <= i < similarity_matrix.shape[0] and 0 <= j < similarity_matrix.shape[1]:
                if i not in used1 and j not in used2:
                    wider_checks += 1
                    if similarity_matrix[i, j] > Config.WIDER_CONTEXT_THRESHOLD:
                        wider_support += 1

        # If we find some support in wider area, allow the match
        if wider_checks > 0 and wider_support > 0:
            return True

        return False

    return True


# ========== PHASE 2: NEW FUNCTIONS ==========

def find_merged_sentences(
    unmatched_sentences: List[Dict],
    target_doc_sentences: List[Dict],
    target_embeddings: np.ndarray
) -> Tuple[List[Dict], List[Dict]]:
    """
    Detect if unmatched sentences are actually merged into sentences in the other document.

    Example:
        unmatched: "Some of us make our homes places of welcome."
        target: "Some of us make our homes places of welcome Some of us share..."
        Result: Detected as merged

    Returns:
        (merged_info_list, still_unmatched)
    """
    if not unmatched_sentences or not target_doc_sentences:
        return [], unmatched_sentences

    # ✅ BATCH EMBEDDINGS UPFRONT (PERFORMANCE FIX)
    model = get_embedding_model()
    unmatch_texts = [s["text"] for s in unmatched_sentences]
    unmatch_embeddings = model.encode(unmatch_texts, show_progress_bar=False)

    merged = []
    still_unmatched = []

    for idx, unmatch_sent in enumerate(unmatched_sentences):
        unmatch_text = unmatch_sent["text"]
        unmatch_embedding = unmatch_embeddings[idx]  # ✅ Use pre-computed embedding
        found_merge = False

        # Check if this sentence is a substring of any target sentence
        # 1️⃣ Substring check
        for target_idx, target_sent in enumerate(target_doc_sentences):
            if len(unmatch_text) >= Config.MIN_SUBSTRING_LENGTH and unmatch_text in target_sent["text"]:
                merged.append({
                    "source_sentence": unmatch_sent,
                    "merged_into": target_sent,
                    "merged_into_index": target_idx,
                    "merge_type": "direct_substring",
                    "similarity": 1.0
                })
                found_merge = True
                break

        # 2️⃣ Normalized containment
        if not found_merge:
            similarities = cosine_similarity([unmatch_embedding], target_embeddings)[0]
            best_idx = np.argmax(similarities)
            best_sim = similarities[best_idx]

            if best_sim > Config.MERGE_SIMILARITY_THRESHOLD:
                target_sent = target_doc_sentences[best_idx]

                norm_unmatch = normalize_sentence(unmatch_text)
                norm_target = normalize_sentence(target_sent["text"])

                if norm_unmatch in norm_target:
                    merged.append({
                        "source_sentence": unmatch_sent,
                        "merged_into": target_sent,
                        "merged_into_index": best_idx,
                        "merge_type": "normalized_containment",
                        "similarity": float(best_sim)
                    })
                    found_merge = True
                    break

        if not found_merge:
            # PHASE 2: Semantic containment check
            # Check if unmatch sentence is semantically contained in any target

            similarities = cosine_similarity([unmatch_embedding], target_embeddings)[0]
            best_idx = np.argmax(similarities)
            best_sim = similarities[best_idx]

            # If very high similarity but not exact match, might be merged with changes
            if best_sim > Config.MERGE_SIMILARITY_THRESHOLD:
                target_sent = target_doc_sentences[best_idx]
                # Check if target is significantly longer (sign of merge)
                if len(target_sent["text"]) > len(unmatch_text) * Config.MERGE_LENGTH_RATIO:
                    merged.append({
                        "source_sentence": unmatch_sent,
                        "merged_into": target_sent,
                        "merged_into_index": best_idx,
                        "merge_type": "semantic_containment",
                        "similarity": float(best_sim)
                    })
                    found_merge = True

        if not found_merge:
            still_unmatched.append(unmatch_sent)

    LOG.info(f"Found {len(merged)} merged sentences, {len(still_unmatched)} still unmatched")
    return merged, still_unmatched


def find_relocated_sentences(
    unmatched_sentences: List[Dict],
    target_doc_sentences: List[Dict],
    target_embeddings: np.ndarray
) -> Tuple[List[Dict], List[Dict]]:
    """
    Find sentences that appear in different positions (not missing, just moved).

    Example:
        Doc1 Position 4: "These whimsical tales..."
        Doc2 Position 13: "These whimsical tales..." (same content, different position)

    Returns:
        (relocated_matches, truly_unmatched)
    """
    if not unmatched_sentences or not target_doc_sentences:
        return [], unmatched_sentences

    relocated = []
    truly_unmatched = []
    used_targets = set()

    model = get_embedding_model()
    unmatch_texts = [s["text"] for s in unmatched_sentences]
    unmatch_embeddings = model.encode(unmatch_texts, show_progress_bar=False)

    for idx, unmatch_sent in enumerate(unmatched_sentences):
        unmatch_embedding = unmatch_embeddings[idx]

        # Find best match in target document
        similarities = cosine_similarity([unmatch_embedding], target_embeddings)[0]
        best_target_idx = np.argmax(similarities)
        best_sim = similarities[best_target_idx]

        # High similarity threshold for "relocated" (should be nearly identical)
        if best_sim > Config.RELOCATED_SIMILARITY_THRESHOLD:
            target_sent = target_doc_sentences[best_target_idx]

            relocated.append({
                "sent1": unmatch_sent,
                "sent2": target_sent,
                "similarity": float(best_sim),
                "index1": unmatch_sent.get("index"),
                "index2": best_target_idx,
                "exact_match": unmatch_sent["text"] == target_sent["text"],
                "normalized_match": normalize_sentence(unmatch_sent["text"]) ==
                                   normalize_sentence(target_sent["text"]),
                "relocated": True  # Flag as relocated
            })
        else:
            truly_unmatched.append(unmatch_sent)

    LOG.info(f"Found {len(relocated)} relocated sentences, {len(truly_unmatched)} truly missing")
    return relocated, truly_unmatched


def find_bidirectional_merges(
    merged_in_doc2: List[Dict],
    sentences1: List[Dict]
) -> List[Dict]:
    """
    PHASE 2: Bidirectional containment check.

    Check if a sentence in doc2 is actually a merge of MULTIPLE sentences from doc1.

    Example:
        Doc1 Sentence 9: "Some of us make our homes places of welcome."
        Doc1 Sentence 10: "Some of us share God's story through melody..."
        Doc2 Sentence 14: "Some of us make our homes places of welcome Some of us share..."

    This would be detected as: Doc2[14] = merge of Doc1[9] + Doc1[10]
    """
    multi_merges = []

    for merge_info in merged_in_doc2:
        merged_target = merge_info["merged_into"]["text"]

        # Find all sentences from doc1 that are contained in this merged sentence
        contained_sentences = []

        for sent1 in sentences1:
            sent1_text = sent1["text"]
            norm_sent1 = normalize_sentence(sent1_text)
            norm_target = normalize_sentence(merged_target)

            if len(norm_sent1) >= Config.MIN_NORMALIZED_LENGTH and norm_sent1 in norm_target:
                contained_sentences.append(sent1)

        # If multiple sentences are contained, this is a multi-merge
        if len(contained_sentences) >= 2:
            multi_merges.append({
                "target_sentence": merge_info["merged_into"],
                "source_sentences": contained_sentences,
                "count": len(contained_sentences)
            })

    return multi_merges


def classify_difference(match: Dict) -> str:
    dm = DictionaryManager.get_instance()
    """
    Unified difference classifier
    Phase 3.1: Legal-aware + OCR-confidence–aware
    """

    sent1_obj = match["sent1"]
    sent2_obj = match["sent2"]

    sent1 = sent1_obj["text"]
    sent2 = sent2_obj["text"]
    similarity = match["similarity"]

    # --- Metadata (safe defaults) ---
    conf1 = sent1_obj.get("confidence", 1.0)
    conf2 = sent2_obj.get("confidence", 1.0)

    source1 = sent1_obj.get("source", "direct")
    source2 = sent2_obj.get("source", "direct")

    dm = DictionaryManager.get_instance()

    # ======================================================
    # 1️⃣ DOMAIN-SPECIFIC LEGAL NORMALIZATION (highest priority)
    # ======================================================

    if (
        is_case_citation(sent1, dm.case_citations) or
        is_case_citation(sent2, dm.case_citations)
    ):
        return "citation_format"

    if (
        contains_latin_maxim(sent1, dm.load("latin_maxims")) or
        contains_latin_maxim(sent2, dm.load("latin_maxims"))
    ):
        return "latin_terminology"

    if (
        is_statute_reference(sent1, dm.load("statutes")) or
        is_statute_reference(sent2, dm.load("statutes"))
    ):
        return "statute_format"

    # ======================================================
    # 2️⃣ EXACT / FORMATTING MATCHES
    # ======================================================

    if match.get("exact_match"):
        return "exact_match"

    if match.get("normalized_match"):
        return is_formatting_only_change(sent1, sent2)

    # ======================================================
    # 3️⃣ OCR-CONFIDENCE–AWARE DETECTION
    # ======================================================

    if (
        similarity > Config.OCR_SIMILARITY_THRESHOLD and
        (conf1 < Config.OCR_CONFIDENCE_THRESHOLD or conf2 < Config.OCR_CONFIDENCE_THRESHOLD)
    ):
        return "ocr_error"

    # ======================================================
    # 4️⃣ SOURCE-AWARE SEMANTIC CLASSIFICATION
    # ======================================================

    if source1 == "direct" and source2 == "direct":
        if similarity < Config.REWORDING_THRESHOLD:
            return "significant"

    # ======================================================
    # 5️⃣ SIMILARITY-BASED FALLBACKS
    # ======================================================

    if similarity > Config.HIGH_SIMILARITY_THRESHOLD:
        return analyze_difference_type(sent1, sent2)

    if similarity > Config.REWORDING_THRESHOLD:
        return "rewording"

    return "significant"


def is_formatting_only_change(sent1: str, sent2: str) -> str:
    """
    PHASE 3: Determine if difference is only formatting.

    Returns specific type: formatting_only, number_formatting, citation_format, etc.
    """
    # Remove all whitespace, case, and punctuation for comparison
    def strip_all(text):
        return re.sub(r'[^\w]', '', text.lower())

    if strip_all(sent1) == strip_all(sent2):
        # Check what type of formatting difference

        # Check for number formatting (commas, decimals)
        if re.search(r'\d', sent1) and re.search(r'\d', sent2):
            # Extract numbers
            nums1 = re.findall(r'[\d,\.]+', sent1)
            nums2 = re.findall(r'[\d,\.]+', sent2)
            if nums1 != nums2:
                return "number_formatting"

        # Check for citation differences (v. vs V., parentheses, etc.)
        citation_patterns = [r'\(\w+\.?\s*\d+\)', r'\[\d{4}\]', r'v\.\s*\d+', r'V\.\s*\d+']
        has_citation1 = any(re.search(p, sent1) for p in citation_patterns)
        has_citation2 = any(re.search(p, sent2) for p in citation_patterns)

        if has_citation1 or has_citation2:
            return "citation_format"

        return "formatting_only"

    return "minor_difference"


def analyze_difference_type(sent1: str, sent2: str) -> str:
    """
    PHASE 3: Analyze what type of difference exists between very similar sentences.
    """
    from difflib import SequenceMatcher

    matcher = SequenceMatcher(None, sent1, sent2)
    opcodes = matcher.get_opcodes()

    # Common OCR character swaps
    ocr_swaps = [
        ('l', '1'), ('I', '1'), ('O', '0'), ('S', '5'),
        ('Z', '2'), ('B', '8'), ('o', '0'), ('i', 'l')
    ]

    ocr_error_count = 0
    total_changes = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag in ['replace', 'insert', 'delete']:
            total_changes += 1

            if tag == 'replace':
                old = sent1[i1:i2]
                new = sent2[j1:j2]

                # Check if this is a known OCR error
                for char1, char2 in ocr_swaps:
                    if (char1 in old and char2 in new) or (char2 in old and char1 in new):
                        ocr_error_count += 1
                        break

    # If most changes are OCR errors
    if total_changes > 0 and ocr_error_count / total_changes > 0.5:
        return "ocr_error"

    return "minor_difference"


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
        "formatting_only": 0,
        "number_formatting": 0,
        "citation_format": 0,
        "ocr_error": 0,
        "minor_difference": 0,
        "rewording": 0,
        "significant": 0,
    }

    for match in matches:
        classification = classify_difference(match)
        classifications.setdefault(classification, 0)
        classifications[classification] += 1


    avg_similarity = sum(m["similarity"] for m in matches) / len(matches)

    return {
        "total_matches": len(matches),
        "exact_matches": classifications["exact_match"],
        "formatting_only": classifications["formatting_only"],
        "number_formatting": classifications["number_formatting"],
        "citation_format": classifications["citation_format"],
        "ocr_errors": classifications["ocr_error"],
        "minor_differences": classifications["minor_difference"],
        "rewordings": classifications["rewording"],
        "significant_differences": classifications["significant"],
        "avg_similarity": avg_similarity
    }



def find_potential_reorderings(
    matches: List[Dict]
) -> List[Dict]:
    """
    Detect sentences that appear in different order
    """
    reorderings = []

    for i, match in enumerate(matches):
        expected_order = match["index1"]
        actual_order = match["index2"]


        if expected_order is None or actual_order is None:
            LOG.debug(
                f"Skipping reorder check (missing order): "
                f"expected={expected_order}, actual={actual_order}"
            )
            continue

        # Check if significantly out of order
        if abs(expected_order - actual_order) > Config.CONTEXT_WINDOW * 2:
            # existing logic
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
    PHASE 3: Context-aware, precise suggestions
    """
    sent1 = match["sent1"]["text"]
    sent2 = match["sent2"]["text"]

    suggestions = []

    # PHASE 3: Use edit distance to find actual character differences
    from difflib import SequenceMatcher

    matcher = SequenceMatcher(None, sent1, sent2)
    opcodes = matcher.get_opcodes()

    # Track what types of changes occurred
    has_replacements = False
    has_insertions = False
    has_deletions = False
    ocr_errors = []

    # Check for common OCR character swaps
    common_ocr_errors = [
        ("l", "1"), ("O", "0"), ("S", "5"),
        ("I", "1"), ("Z", "2"), ("B", "8"),
        ("o", "0"), ("i", "l")
    ]

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'replace':
            has_replacements = True
            old_chars = sent1[i1:i2]
            new_chars = sent2[j1:j2]

            # Check if this is a known OCR error
            for char1, char2 in common_ocr_errors:
                if (char1 in old_chars and char2 in new_chars):
                    ocr_errors.append(f"'{char1}' → '{char2}' at position {i1}")
                elif (char2 in old_chars and char1 in new_chars):
                    ocr_errors.append(f"'{char2}' → '{char1}' at position {i1}")

        elif tag == 'insert':
            has_insertions = True

        elif tag == 'delete':
            has_deletions = True

    # Only suggest OCR errors if we found specific instances
    if ocr_errors:
        for error in ocr_errors[:3]:  # Limit to top 3
            suggestions.append(f"Possible OCR error: {error}")

    # Length difference
    len_diff = abs(len(sent1) - len(sent2))
    if len_diff > 10:
        suggestions.append(f"Length difference: {len_diff} characters")

    # Word count difference
    words1 = len(sent1.split())
    words2 = len(sent2.split())
    word_diff = abs(words1 - words2)
    if word_diff > 3:
        suggestions.append(f"Word count difference: {words1} vs {words2} words")

    # PHASE 3: Specific change types
    if has_replacements and not has_insertions and not has_deletions:
        suggestions.append("Character substitutions only (likely OCR)")

    if has_insertions and not has_deletions:
        suggestions.append("Text added in Doc2")

    if has_deletions and not has_insertions:
        suggestions.append("Text removed in Doc2")

    # PHASE 3: Check if sentences might be merged
    if len(sent2) > len(sent1) * 1.5:
        suggestions.append("Doc2 sentence may contain additional merged content")
    elif len(sent1) > len(sent2) * 1.5:
        suggestions.append("Doc1 sentence may contain additional merged content")

    # PHASE 3: Check for formatting-only changes
    strip_format = lambda s: re.sub(r'[^\w]', '', s.lower())
    if strip_format(sent1) == strip_format(sent2):
        suggestions.append("Only formatting differs (case, punctuation, spacing)")

    return suggestions if suggestions else ["Minor textual variation"]

def is_case_citation(text: str, citations: dict) -> bool:
    """Check if text matches known case citation patterns"""
    for pattern in citations.get("patterns", []):
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def contains_latin_maxim(text: str, maxims: dict) -> bool:
    """Check if text contains Latin legal phrases"""
    text_lower = text.lower()
    for maxim in maxims.keys():
        if maxim.lower() in text_lower:
            return True
    return False


# For testing
if __name__ == "__main__":
    from comparison_engine.smart_chunker import chunk_into_sentences

    # Test texts
    text1 = """
    This is the first sentence. This is the second sentence.
    This is the third sentence.
    """

    text2 = """
    This is the first sentence. This is the seccond sentence.
    This is an added sentence. This is the third sentence.
    """

    print("Testing semantic matching with Phase 2 enhancements...")
    print("="*60)

    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)

    print(f"\nDocument 1: {len(sentences1)} sentences")
    print(f"Document 2: {len(sentences2)} sentences")

    results = match_documents(sentences1, sentences2)

    print(f"\nOverall match score: {results['match_score']:.1%}")
    print(f"Matches: {len(results['matches'])}")
    print(f"Only in doc1: {len(results['only_in_doc1'])}")
    print(f"Only in doc2: {len(results['only_in_doc2'])}")
    print(f"Merged in doc1: {len(results['merged_in_doc1'])}")
    print(f"Merged in doc2: {len(results['merged_in_doc2'])}")

    print("\n" + "="*60)
    print("Matches:")
    for match in results['matches']:
        print(f"\n[{match['similarity']:.2%}] {classify_difference(match)}")
        print(f"  Doc1: {match['sent1']['text']}")
        print(f"  Doc2: {match['sent2']['text']}")
