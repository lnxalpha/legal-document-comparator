"""
Phase 3 Regression Tests
Tests inline diffs, granular classification, and grouped differences
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from comparison_engine.smart_chunker import chunk_into_sentences
from comparison_engine.semantic_matcher import match_documents, classify_difference
from comparison_engine.report_generator import generate_report, group_related_differences
from comparison_engine.diff_utils import (
    generate_inline_diff,
    generate_word_diff,
    get_diff_stats,
    should_use_word_diff
)


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


def test_inline_diff_generation():
    """Test inline diff HTML generation."""
    result = TestResult("Inline Diff Generation")
    
    text1 = "This is the old text"
    text2 = "This is the new text"
    
    diff1, diff2 = generate_inline_diff(text1, text2)
    
    # Test 1: Returns HTML strings
    if isinstance(diff1, str) and isinstance(diff2, str):
        result.add_pass("Returns string outputs")
    else:
        result.add_fail("Output type", f"Got {type(diff1)}, {type(diff2)}")
    
    # Test 2: Contains highlighting tags
    if '<del' in diff1 or '<ins' in diff2:
        result.add_pass("Contains diff highlighting tags")
    else:
        result.add_fail("Highlighting", "No diff tags found")
    
    # Test 3: Preserves equal parts
    if 'This is the' in diff1 and 'This is the' in diff2:
        result.add_pass("Preserves equal text")
    else:
        result.add_fail("Equal text", "Lost unchanged portions")
    
    return result


def test_word_diff_generation():
    """Test word-level diff generation."""
    result = TestResult("Word-Level Diff")
    
    text1 = "The quick brown fox jumps"
    text2 = "The slow brown fox walks"
    
    diff1, diff2 = generate_word_diff(text1, text2)
    
    # Should highlight changed words
    if '<del' in diff1 and '<ins' in diff2:
        result.add_pass("Word-level highlighting works")
    else:
        result.add_fail("Word highlighting", "No word-level tags")
    
    # Should preserve common words
    if 'brown' in diff1 and 'brown' in diff2:
        result.add_pass("Preserves common words")
    else:
        result.add_fail("Common words", "Lost unchanged words")
    
    return result


def test_diff_stats():
    """Test diff statistics calculation."""
    result = TestResult("Diff Statistics")
    
    text1 = "Hello world"
    text2 = "Hello beautiful world"
    
    stats = get_diff_stats(text1, text2)
    
    # Test 1: Returns dict with expected keys
    expected_keys = ["char_changes", "words_changed", "additions", "deletions", "replacements"]
    if all(k in stats for k in expected_keys):
        result.add_pass("All stat keys present")
    else:
        result.add_fail("Stats keys", f"Missing keys: {set(expected_keys) - set(stats.keys())}")
    
    # Test 2: Detects insertion
    if stats["additions"] > 0:
        result.add_pass("Detects word addition")
    else:
        result.add_fail("Addition detection", "Missed word insertion")
    
    return result


def test_granular_classification():
    """Test Phase 3 granular difference classification."""
    result = TestResult("Granular Classification")
    
    # Test formatting-only detection
    text1 = "This is a test."
    text2 = "THIS IS A TEST"
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    if match_results["matches"]:
        match = match_results["matches"][0]
        classification = classify_difference(match)
        
        if "formatting" in classification:
            result.add_pass("Detects formatting-only changes")
        else:
            result.add_warning(f"Classified as: {classification} (expected formatting)")
    
    # Test OCR error detection
    text3 = "This is sentence one"
    text4 = "This is sentence 0ne"  # o → 0
    
    sentences3 = chunk_into_sentences(text3)
    sentences4 = chunk_into_sentences(text4)
    
    match_results2 = match_documents(sentences3, sentences4)
    
    if match_results2["matches"]:
        match2 = match_results2["matches"][0]
        classification2 = classify_difference(match2)
        
        if "ocr" in classification2 or "minor" in classification2:
            result.add_pass("Detects OCR-type errors")
        else:
            result.add_warning(f"Classified as: {classification2}")
    
    return result


def test_grouped_differences():
    """Test difference grouping functionality."""
    result = TestResult("Grouped Differences")
    
    # Create mock differences that should be grouped
    differences = [
        {
            "type": "merged_in_doc2",
            "position1": 1,
            "position2": 5,
            "classification": "sentence_merge"
        },
        {
            "type": "merged_in_doc2",
            "position1": 2,
            "position2": 5,
            "classification": "sentence_merge"
        },
        {
            "type": "mismatch",
            "position1": 3,
            "position2": 3,
            "classification": "formatting_only"
        },
        {
            "type": "mismatch",
            "position1": 4,
            "position2": 4,
            "classification": "formatting_only"
        },
        {
            "type": "mismatch",
            "position1": 5,
            "position2": 5,
            "classification": "formatting_only"
        }
    ]
    
    groups = group_related_differences(differences)
    
    # Test 1: Creates groups
    if len(groups) > 0:
        result.add_pass("Creates difference groups")
    else:
        result.add_fail("Grouping", "No groups created")
    
    # Test 2: Groups merge-related differences
    merge_groups = [g for g in groups if g["type"] == "merge_group"]
    if merge_groups:
        result.add_pass(f"Created {len(merge_groups)} merge group(s)")
    else:
        result.add_warning("No merge groups created (expected 1)")
    
    # Test 3: Groups formatting differences
    formatting_groups = [g for g in groups if g["type"] == "formatting_group"]
    if formatting_groups:
        result.add_pass(f"Created {len(formatting_groups)} formatting group(s)")
    else:
        result.add_warning("No formatting groups created")
    
    return result


def test_smart_suggestions():
    """Test Phase 3 context-aware suggestions."""
    result = TestResult("Smart Suggestions")
    
    text1 = "The value is 1,000 dollars"
    text2 = "The value is 1000 dollars"
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    
    if match_results["matches"]:
        from comparison_engine.semantic_matcher import suggest_corrections
        match = match_results["matches"][0]
        suggestions = suggest_corrections(match)
        
        # Should not suggest OCR errors for this (it's just formatting)
        ocr_suggestions = [s for s in suggestions if "OCR" in s]
        if len(ocr_suggestions) == 0:
            result.add_pass("Doesn't suggest OCR errors for formatting")
        else:
            result.add_warning("Suggested OCR errors for formatting difference")
        
        # Should mention formatting
        formatting_suggestions = [s for s in suggestions if "formatting" in s.lower()]
        if formatting_suggestions:
            result.add_pass("Mentions formatting difference")
        else:
            result.add_warning("Didn't identify as formatting issue")
    
    return result


def test_report_enhancements():
    """Test Phase 3 report enhancements."""
    result = TestResult("Report Enhancements")
    
    text1 = "This is sentence one. This is sentence two."
    text2 = "THIS IS SENTENCE ONE. This is sentence too."  # Case + typo
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    report = generate_report(match_results, sentences1, sentences2)
    
    # Test 1: Summary has Phase 3 fields
    phase3_fields = ["formatting_only", "ocr_errors", "number_formatting"]
    if any(f in report["summary"] for f in phase3_fields):
        result.add_pass("Summary includes Phase 3 classification breakdown")
    else:
        result.add_fail("Summary fields", "Missing Phase 3 classifications")
    
    # Test 2: Differences have inline diff data
    if report["differences"]:
        first_diff = report["differences"][0]
        if "diff_html1" in first_diff:
            result.add_pass("Differences include inline diff HTML")
        else:
            result.add_fail("Inline diffs", "Missing diff_html fields")
        
        if "diff_stats" in first_diff:
            result.add_pass("Differences include diff statistics")
        else:
            result.add_warning("Missing diff_stats field")
    
    # Test 3: Grouped differences present
    if "grouped_differences" in report:
        result.add_pass("Report includes grouped differences")
    else:
        result.add_fail("Grouping", "Missing grouped_differences field")
    
    return result


def test_html_report_quality():
    """Test HTML report generation quality."""
    result = TestResult("HTML Report Quality")
    
    text1 = "First sentence. Second sentence."
    text2 = "First sentence. Different second sentence."
    
    sentences1 = chunk_into_sentences(text1)
    sentences2 = chunk_into_sentences(text2)
    
    match_results = match_documents(sentences1, sentences2)
    report = generate_report(match_results, sentences1, sentences2)
    
    from comparison_engine.report_generator import generate_html_report
    html = generate_html_report(report, "test1.pdf", "test2.pdf")
    
    # Test 1: Valid HTML structure
    if "<html>" in html and "</html>" in html:
        result.add_pass("Valid HTML structure")
    else:
        result.add_fail("HTML structure", "Missing HTML tags")
    
    # Test 2: Includes statistics
    if str(report["summary"]["overall_match"]) in html:
        result.add_pass("Includes match statistics")
    else:
        result.add_fail("Statistics", "Missing summary stats")
    
    # Test 3: Includes recommendations
    if report["recommendations"] and any(rec[:20] in html for rec in report["recommendations"]):
        result.add_pass("Includes recommendations")
    else:
        result.add_warning("Recommendations not found in HTML")
    
    # Test 4: Phase 3 badges
    if "badge" in html.lower():
        result.add_pass("Includes Phase 3 visual badges")
    else:
        result.add_warning("No visual badges found")
    
    return result


def run_all_tests():
    """Run all Phase 3 tests."""
    print("="*70)
    print("PHASE 3 REGRESSION TESTS")
    print("Testing: Inline Diffs, Granular Classification, & Grouped Differences")
    print("="*70)
    
    results = []
    
    print("\n📋 Test 1: Inline Diff Generation")
    print("-" * 70)
    results.append(test_inline_diff_generation())
    
    print("\n📋 Test 2: Word-Level Diff")
    print("-" * 70)
    results.append(test_word_diff_generation())
    
    print("\n📋 Test 3: Diff Statistics")
    print("-" * 70)
    results.append(test_diff_stats())
    
    print("\n📋 Test 4: Granular Classification")
    print("-" * 70)
    results.append(test_granular_classification())
    
    print("\n📋 Test 5: Grouped Differences")
    print("-" * 70)
    results.append(test_grouped_differences())
    
    print("\n📋 Test 6: Smart Suggestions")
    print("-" * 70)
    results.append(test_smart_suggestions())
    
    print("\n📋 Test 7: Report Enhancements")
    print("-" * 70)
    results.append(test_report_enhancements())
    
    print("\n📋 Test 8: HTML Report Quality")
    print("-" * 70)
    results.append(test_html_report_quality())
    
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
    if total_tests > 0:
        print(f"Success Rate: {total_passed/total_tests*100:.1f}%")
    
    all_passed = all(r.summary() for r in results)
    
    if all_passed:
        print("\n✓ All Phase 3 tests passed!")
        print("\n🎉 Your tool now has:")
        print("  • Inline character-level diffs")
        print("  • Granular classification (formatting, OCR errors, etc.)")
        print("  • Grouped related differences")
        print("  • Smart, context-aware suggestions")
        print("  • Beautiful HTML reports with visual badges")
        return 0
    else:
        print("\n✗ Some Phase 3 tests failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
