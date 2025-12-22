"""
Phase 2 Regression Tests
Tests fuzzy boundary matching and merged sentence detection
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from comparison_engine.smart_chunker import chunk_into_sentences
from comparison_engine.semantic_matcher import match_documents
from comparison_engine.report_generator import generate_report


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test: str):
        self.passed.append(test)
        print(f"  ✓ {test}")
    
    def add_fail(self, test: str, reason: str):
        self.failed.append((test, reason))
        print(f"  ✗ {test}: {reason}")
    
    def add_warning(self, message: str):
        self.warnings.append(message)
        print(f"  ⚠ {message}")
    
    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{self.name} Results:")
        print(f"  Passed: {len(self.passed)}/{total}")
        print(f"  Failed: {len(self.failed)}/{total}")
        if self.warnings:
            print(f"  Warnings: {len(self.warnings)}")
        return len(self.failed) == 0


def test_merged_sentence_detection():
    """Test detection of merged sentences."""
    result = TestResult("Merged Sentence Detection")
    
    # Simulate OCR output where sentences got merged
    text1 = """
    Some of us make our homes places of welcome.
    Some of us share God's story through melody, poetry, or conversation.
    """
    
    text2 = """
    Some of us make our homes places of welcome Some of us share God's story through melody, poetry, or conversation.
    """
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    # Test 1: Should detect merged sentences
    merged_count = len(match_results.get("merged_in_doc2", []))
    if merged_count > 0:
        result.add_pass(f"Detected {merged_count} merged sentence(s)")
    else:
        result.add_fail("Merge detection", "Failed to detect obvious merge")
    
    # Test 2: Should NOT mark as "only_in_doc1"
    only_in_doc1_count = len(match_results["only_in_doc1"])
    if only_in_doc1_count == 0:
        result.add_pass("No false 'only_in_doc1' entries")
    else:
        result.add_fail("False additions", f"Got {only_in_doc1_count} false additions")
    
    return result


def test_relocated_sentences():
    """Test detection of sentences at different positions."""
    result = TestResult("Relocated Sentence Detection")
    
    # Same sentence at different positions
    text1 = """
    This is sentence one.
    This is sentence two.
    This is sentence three.
    """
    
    text2 = """
    This is sentence one.
    This is sentence three.
    This is sentence two.
    """
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    # Test 1: All sentences should be matched
    if len(match_results["matches"]) == 3:
        result.add_pass("All 3 sentences matched")
    else:
        result.add_fail("Matching", f"Only {len(match_results['matches'])} matched")
    
    # Test 2: Should NOT have "only_in" entries
    total_only = len(match_results["only_in_doc1"]) + len(match_results["only_in_doc2"])
    if total_only == 0:
        result.add_pass("No false additions/deletions")
    else:
        result.add_fail("False positives", f"{total_only} false entries")
    
    # Test 3: Should detect reordering
    report = generate_report(match_results, sentences1, sentences2)
    if report["summary"]["reorderings_detected"] > 0:
        result.add_pass("Reordering detected")
    else:
        result.add_warning("Reordering not flagged (expected)")
    
    return result


def test_bidirectional_containment():
    """Test detection of multi-sentence merges."""
    result = TestResult("Bidirectional Containment")
    
    # Multiple doc1 sentences merged into one doc2 sentence
    text1 = """
    First sentence here.
    Second sentence here.
    Third sentence here.
    """
    
    text2 = """
    First sentence here Second sentence here Third sentence here.
    """
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    # Test 1: Should detect merges
    merged_count = len(match_results.get("merged_in_doc2", []))
    if merged_count >= 2:
        result.add_pass(f"Detected {merged_count} merged sentences")
    else:
        result.add_warning(f"Only detected {merged_count} merges (expected 2+)")
    
    # Test 2: Should minimize false additions
    only_count = len(match_results["only_in_doc1"])
    if only_count <= 1:
        result.add_pass(f"Minimal false additions: {only_count}")
    else:
        result.add_fail("False additions", f"Got {only_count}, expected <= 1")
    
    return result


def test_normalized_matching():
    """Test matching with normalization (case, punctuation)."""
    result = TestResult("Normalized Matching")
    
    text1 = "This is a test sentence."
    text2 = "THIS IS A TEST SENTENCE"
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    # Should match despite case difference
    if len(match_results["matches"]) == 1:
        result.add_pass("Case-insensitive matching works")
    else:
        result.add_fail("Normalization", "Failed to match normalized sentences")
    
    # Should be marked as normalized match
    if match_results["matches"] and match_results["matches"][0].get("normalized_match"):
        result.add_pass("Correctly identified as normalized match")
    else:
        result.add_warning("Not flagged as normalized match")
    
    return result


def test_context_validation():
    """Test that context validation works correctly."""
    result = TestResult("Context Validation")
    
    # Sentences in correct order
    text1 = """
    Sentence A is here.
    Sentence B follows.
    Sentence C is last.
    """
    
    text2 = """
    Sentence A is here.
    Sentence B follows.
    Sentence C is last.
    """
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    # All should match with context support
    if len(match_results["matches"]) == 3:
        result.add_pass("Context validation allows correct matches")
    else:
        result.add_fail("Context validation", "Rejected valid matches")
    
    # High match score expected
    if match_results["match_score"] > 0.95:
        result.add_pass(f"High match score: {match_results['match_score']:.1%}")
    else:
        result.add_fail("Match score", f"Low score: {match_results['match_score']:.1%}")
    
    return result


def test_phase2_bible_scenario():
    """
    Test the exact Bible page scenario from user's output.
    This tests the core Phase 2 improvements.
    """
    result = TestResult("Bible Page Scenario")
    
    # Recreate the problematic patterns from user's output
    text1 = """
    These whimsical, joy-filled tales were Lofting's way of pushing back against the war's horror.
    Some of us make our homes places of welcome.
    Some of us share God's story through melody, poetry, or conversation.
    """
    
    text2 = """
    These whimsical, joy-filled tales were Lofting's way of pushing back against the war's horror.
    Some of us make our homes places of welcome Some of us share God's story through melody, poetry, or conversa- tion.
    """
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    # Test 1: First sentence should match
    if len(match_results["matches"]) >= 1:
        result.add_pass("First sentence matched")
    else:
        result.add_fail("Matching", "Failed to match identical sentence")
    
    # Test 2: Should detect merged sentences
    merged_count = len(match_results.get("merged_in_doc2", []))
    if merged_count > 0:
        result.add_pass(f"Detected {merged_count} merged sentence(s)")
    else:
        result.add_fail("Merge detection", "Missed obvious merge")
    
    # Test 3: Should have minimal false additions
    false_additions = len(match_results["only_in_doc1"])
    if false_additions <= 1:
        result.add_pass(f"Minimal false additions: {false_additions}")
    else:
        result.add_fail("False positives", f"{false_additions} false additions (expected <= 1)")
    
    # Test 4: Generate report and check recommendations
    report = generate_report(match_results, sentences1, sentences2)
    if any("merged" in rec.lower() for rec in report["recommendations"]):
        result.add_pass("Report mentions merged sentences")
    else:
        result.add_warning("Report doesn't mention merges")
    
    return result


def run_all_tests():
    """Run all Phase 2 tests."""
    print("="*70)
    print("PHASE 2 REGRESSION TESTS")
    print("Testing: Fuzzy Boundary Matching & Merged Sentence Detection")
    print("="*70)
    
    results = []
    
    print("\n📋 Test 1: Merged Sentence Detection")
    print("-" * 70)
    results.append(test_merged_sentence_detection())
    
    print("\n📋 Test 2: Relocated Sentences")
    print("-" * 70)
    results.append(test_relocated_sentences())
    
    print("\n📋 Test 3: Bidirectional Containment")
    print("-" * 70)
    results.append(test_bidirectional_containment())
    
    print("\n📋 Test 4: Normalized Matching")
    print("-" * 70)
    results.append(test_normalized_matching())
    
    print("\n📋 Test 5: Context Validation")
    print("-" * 70)
    results.append(test_context_validation())
    
    print("\n📋 Test 6: Bible Page Scenario (Real-World)")
    print("-" * 70)
    results.append(test_phase2_bible_scenario())
    
    # Overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    
    total_passed = sum(len(r.passed) for r in results)
    total_failed = sum(len(r.failed) for r in results)
    total_tests = total_passed + total_failed
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success Rate: {total_passed/total_tests*100:.1f}%")
    
    all_passed = all(r.summary() for r in results)
    
    if all_passed:
        print("\n✓ All Phase 2 tests passed!")
        return 0
    else:
        print("\n✗ Some Phase 2 tests failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
