"""
Diff Utilities Module
Generate inline character-level diffs for better visualization
Phase 3: New module for visual diff generation
"""

from typing import List, Tuple
from difflib import SequenceMatcher
import html


def generate_inline_diff(text1: str, text2: str) -> Tuple[str, str]:
    """
    Generate inline diff with HTML highlighting.
    
    Returns:
        (highlighted_text1, highlighted_text2)
        
    Example:
        text1 = "This is the old text"
        text2 = "This is the new text"
        
        Returns:
            ("This is the <del>old</del> text", 
             "This is the <ins>new</ins> text")
    """
    matcher = SequenceMatcher(None, text1, text2)
    opcodes = matcher.get_opcodes()
    
    html1_parts = []
    html2_parts = []
    
    for tag, i1, i2, j1, j2 in opcodes:
        text1_part = html.escape(text1[i1:i2])
        text2_part = html.escape(text2[j1:j2])
        
        if tag == 'equal':
            html1_parts.append(text1_part)
            html2_parts.append(text2_part)
        
        elif tag == 'replace':
            html1_parts.append(f'<del style="background:#ffe6e6;text-decoration:line-through;">{text1_part}</del>')
            html2_parts.append(f'<ins style="background:#e6ffe6;text-decoration:none;">{text2_part}</ins>')
        
        elif tag == 'delete':
            html1_parts.append(f'<del style="background:#ffe6e6;text-decoration:line-through;">{text1_part}</del>')
        
        elif tag == 'insert':
            html2_parts.append(f'<ins style="background:#e6ffe6;text-decoration:none;">{text2_part}</ins>')
    
    return ''.join(html1_parts), ''.join(html2_parts)


def generate_word_diff(text1: str, text2: str) -> Tuple[str, str]:
    """
    Generate word-level diff (cleaner for long sentences).
    
    Returns:
        (highlighted_text1, highlighted_text2)
    """
    words1 = text1.split()
    words2 = text2.split()
    
    matcher = SequenceMatcher(None, words1, words2)
    opcodes = matcher.get_opcodes()
    
    html1_parts = []
    html2_parts = []
    
    for tag, i1, i2, j1, j2 in opcodes:
        words1_part = ' '.join(html.escape(w) for w in words1[i1:i2])
        words2_part = ' '.join(html.escape(w) for w in words2[j1:j2])
        
        if tag == 'equal':
            html1_parts.append(words1_part)
            html2_parts.append(words2_part)
        
        elif tag == 'replace':
            if words1_part:
                html1_parts.append(f'<del style="background:#ffe6e6;">{words1_part}</del>')
            if words2_part:
                html2_parts.append(f'<ins style="background:#e6ffe6;">{words2_part}</ins>')
        
        elif tag == 'delete':
            html1_parts.append(f'<del style="background:#ffe6e6;">{words1_part}</del>')
        
        elif tag == 'insert':
            html2_parts.append(f'<ins style="background:#e6ffe6;">{words2_part}</ins>')
    
    return ' '.join(html1_parts), ' '.join(html2_parts)


def get_diff_stats(text1: str, text2: str) -> dict:
    """
    Get statistics about the differences.
    
    Returns:
        {
            "char_changes": 5,
            "words_changed": 2,
            "additions": 3,
            "deletions": 1,
            "replacements": 1
        }
    """
    matcher = SequenceMatcher(None, text1, text2)
    opcodes = matcher.get_opcodes()
    
    stats = {
        "char_changes": 0,
        "words_changed": 0,
        "additions": 0,
        "deletions": 0,
        "replacements": 0
    }
    
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'replace':
            stats["char_changes"] += max(i2 - i1, j2 - j1)
            stats["replacements"] += 1
        elif tag == 'insert':
            stats["char_changes"] += j2 - j1
            stats["additions"] += 1
        elif tag == 'delete':
            stats["char_changes"] += i2 - i1
            stats["deletions"] += 1
    
    # Word-level stats
    words1 = set(text1.split())
    words2 = set(text2.split())
    stats["words_changed"] = len(words1.symmetric_difference(words2))
    
    return stats


def generate_side_by_side_diff(text1: str, text2: str) -> str:
    """
    Generate side-by-side HTML diff view.
    
    Returns HTML string with both texts side-by-side with highlighting.
    """
    diff1, diff2 = generate_inline_diff(text1, text2)
    
    html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;font-family:monospace;">
        <div style="border:1px solid #ddd;padding:10px;border-radius:4px;">
            <div style="background:#f0f0f0;padding:5px;margin-bottom:10px;font-weight:bold;">
                Document 1
            </div>
            <div>{diff1}</div>
        </div>
        <div style="border:1px solid #ddd;padding:10px;border-radius:4px;">
            <div style="background:#f0f0f0;padding:5px;margin-bottom:10px;font-weight:bold;">
                Document 2
            </div>
            <div>{diff2}</div>
        </div>
    </div>
    """
    
    return html


def should_use_word_diff(text1: str, text2: str) -> bool:
    """
    Determine if word-level diff is better than character-level.
    
    Use word diff when:
    - Texts are long (>100 chars)
    - Changes are whole-word based
    """
    if len(text1) > 100 or len(text2) > 100:
        return True
    
    # Check if changes are word-based
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    # If more than 30% of words differ, use word diff
    total_words = len(words1.union(words2))
    diff_words = len(words1.symmetric_difference(words2))
    
    if total_words > 0 and diff_words / total_words > 0.3:
        return True
    
    return False


def generate_smart_diff(text1: str, text2: str) -> Tuple[str, str]:
    """
    Automatically choose between character and word diff.
    
    Returns:
        (highlighted_text1, highlighted_text2)
    """
    if should_use_word_diff(text1, text2):
        return generate_word_diff(text1, text2)
    else:
        return generate_inline_diff(text1, text2)


# For testing
if __name__ == "__main__":
    # Test character-level diff
    text1 = "This is the old text with some changes"
    text2 = "This is the new text with some changes"
    
    print("Character-level diff:")
    print("=" * 60)
    diff1, diff2 = generate_inline_diff(text1, text2)
    print("Text 1:", diff1)
    print("Text 2:", diff2)
    
    # Test word-level diff
    print("\n" + "=" * 60)
    print("Word-level diff:")
    print("=" * 60)
    diff1, diff2 = generate_word_diff(text1, text2)
    print("Text 1:", diff1)
    print("Text 2:", diff2)
    
    # Test stats
    print("\n" + "=" * 60)
    print("Diff statistics:")
    print("=" * 60)
    stats = get_diff_stats(text1, text2)
    for key, value in stats.items():
        print(f"  {key}: {value}")
