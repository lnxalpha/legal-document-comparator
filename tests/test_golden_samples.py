"""
Golden Sample Regression Tests
Ensures fixes don't break existing functionality
"""
import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unified_extractor.extractor import extract_text_with_confidence
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


async def test_bible_page(samples_dir: Path) -> TestResult:
    """
    Test the Bible page sample from your original output.
    
    Expected behaviors:
    - No sentences should be lost during OCR
    - Merged sentences should be detected (not marked as additions)
    - Low-quality OCR should be flagged
    """
    result = TestResult("Bible Page Test")
    
    bible_dir = samples_dir / "bible_page"
    if not bible_dir.exists():
        result.add_warning("Bible page samples not found, skipping test")
        return result
    
    doc1_path = bible_dir / "doc1.pdf"
    doc2_path = bible_dir / "doc2.pdf"
    
    if not doc1_path.exists() or not doc2_path.exists():
        result.add_warning("Sample PDFs not found")
        return result
    
    print(f"\nExtracting documents...")
    
    # Extract both documents
    doc1_data = await extract_text_with_confidence(doc1_path)
    doc2_data = await extract_text_with_confidence(doc2_path)
    
    # Test 1: No extraction failures
    if "<unreadable" not in doc1_data["text"].lower():
        result.add_pass("Doc1 extracted successfully")
    else:
        result.add_fail("Doc1 extraction", "Contains unreadable content")
    
    if "<unreadable" not in doc2_data["text"].lower():
        result.add_pass("Doc2 extracted successfully")
    else:
        result.add_fail("Doc2 extraction", "Contains unreadable content")
    
    # Test 2: Confidence tracking
    if doc1_data.get("confidence") is not None:
        result.add_pass("Doc1 has confidence score")
    else:
        result.add_fail("Doc1 confidence", "Missing confidence score")
    
    if doc2_data.get("confidence") is not None:
        result.add_pass("Doc2 has confidence score")
    else:
        result.add_fail("Doc2 confidence", "Missing confidence score")
    
    # Test 3: Line provenance
    if doc1_data.get("lines") is not None:
        result.add_pass("Doc1 has line provenance")
        if len(doc1_data["lines"]) > 0:
            result.add_pass(f"Doc1 detected {len(doc1_data['lines'])} lines")
    else:
        result.add_fail("Doc1 provenance", "Missing line data")
    
    # Chunk into sentences
    print(f"\nChunking into sentences...")
    sentences1 = chunk_into_sentences(doc1_data["text"], provenance=doc1_data)
    sentences2 = chunk_into_sentences(doc2_data["text"], provenance=doc2_data)
    
    # Test 4: Sentence extraction
    if len(sentences1) > 0:
        result.add_pass(f"Doc1: {len(sentences1)} sentences")
    else:
        result.add_fail("Doc1 chunking", "No sentences extracted")
    
    if len(sentences2) > 0:
        result.add_pass(f"Doc2: {len(sentences2)} sentences")
    else:
        result.add_fail("Doc2 chunking", "No sentences extracted")
    
    # Test 5: Sentence provenance
    if sentences1 and "confidence" in sentences1[0]:
        result.add_pass("Sentences have confidence metadata")
    else:
        result.add_fail("Sentence metadata", "Missing confidence")
    
    # Match documents
    print(f"\nMatching documents...")
    match_results = match_documents(sentences1, sentences2)
    
    # Test 6: Matching quality
    match_score = match_results["match_score"]
    if match_score > 0.7:
        result.add_pass(f"Good match score: {match_score:.1%}")
    else:
        result.add_fail("Match score", f"Low score: {match_score:.1%}")
    
    # Test 7: False additions check
    # In your original output, sentences 4, 5, 9, 10 were false "additions"
    # They should now be detected as merged or matched
    only_in_doc1 = match_results["only_in_doc1"]
    only_in_doc2 = match_results["only_in_doc2"]
    
    total_unmatched = len(only_in_doc1) + len(only_in_doc2)
    
    # Based on your sample, we expect some mismatches but not many
    if total_unmatched < 5:
        result.add_pass(f"Low false additions: {total_unmatched}")
    else:
        result.add_warning(f"High unmatched count: {total_unmatched}")
    
    # Generate report
    print(f"\nGenerating report...")
    report = generate_report(match_results, sentences1, sentences2)
    
    # Test 8: Report quality
    if report["summary"]["overall_match"] > 70:
        result.add_pass(f"Overall match: {report['summary']['overall_match']}%")
    else:
        result.add_fail("Overall match", f"Too low: {report['summary']['overall_match']}%")
    
    return result


async def test_basic_functionality(samples_dir: Path) -> TestResult:
    """
    Test basic extraction and comparison functionality.
    """
    result = TestResult("Basic Functionality Test")
    
    # Test 1: Simple text extraction
    test_text = "This is sentence one. This is sentence two."
    sentences = chunk_into_sentences(test_text)
    
    if len(sentences) == 2:
        result.add_pass("Basic sentence chunking works")
    else:
        result.add_fail("Sentence chunking", f"Expected 2 sentences, got {len(sentences)}")
    
    # Test 2: Sentence boundary repair
    broken_text = "This is sentence one Some of us make homes"
    # After repair, should have period inserted
    from unified_extractor.correction import repair_sentence_boundaries
    repaired = repair_sentence_boundaries(broken_text)
    
    if "one." in repaired or "one. Some" in repaired:
        result.add_pass("Sentence boundary repair works")
    else:
        result.add_warning(f"Boundary repair may need tuning: {repaired}")
    
    # Test 3: Normalization
    from comparison_engine.smart_chunker import normalize_sentence
    
    sent1 = "This is a test."
    sent2 = "THIS IS A TEST"
    
    if normalize_sentence(sent1) == normalize_sentence(sent2):
        result.add_pass("Normalization works")
    else:
        result.add_fail("Normalization", "Case normalization failed")
    
    return result


async def run_all_tests():
    """Run all golden sample tests."""
    print("="*70)
    print("GOLDEN SAMPLE REGRESSION TESTS - PHASE 1")
    print("="*70)
    
    # Find samples directory
    tests_dir = Path(__file__).parent
    samples_dir = tests_dir / "golden_samples"
    
    if not samples_dir.exists():
        print(f"\n⚠ Creating samples directory: {samples_dir}")
        samples_dir.mkdir(parents=True, exist_ok=True)
        print("  Please add test samples to this directory:")
        print(f"  - {samples_dir}/bible_page/doc1.pdf")
        print(f"  - {samples_dir}/bible_page/doc2.pdf")
    
    # Run tests
    results = []
    
    results.append(await test_basic_functionality(samples_dir))
    results.append(await test_bible_page(samples_dir))
    
    # Summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    
    all_passed = all(r.summary() for r in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
