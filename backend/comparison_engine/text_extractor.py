"""
Text Extraction Module
Handles PDF text extraction and OCR for images
"""

from pathlib import Path
from typing import Optional
import asyncio


async def extract_text(file_path: Path) -> str:
    """
    Extract text from a file (PDF or image)
    
    Args:
        file_path: Path to the file
    
    Returns:
        Extracted text as string
    """
    suffix = file_path.suffix.lower()
    
    if suffix == '.pdf':
        return await extract_from_pdf(file_path)
    elif suffix in ['.png', '.jpg', '.jpeg']:
        return await extract_from_image(file_path)
    elif suffix == '.txt':
        return file_path.read_text(encoding='utf-8')
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


async def extract_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from PDF using PyMuPDF
    Falls back to OCR if no text found
    """
    try:
        import fitz  # PyMuPDF
        
        text_parts = []
        doc = fitz.open(str(pdf_path))
        
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text()
            
            # If page has no text, it might be a scanned PDF
            if not page_text.strip():
                print(f"   Page {page_num}: No text found, attempting OCR...")
                page_text = await ocr_pdf_page(page)
            
            text_parts.append(page_text)
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        return clean_extracted_text(full_text)
    
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


async def ocr_pdf_page(page) -> str:
    """
    OCR a single PDF page using Tesseract
    """
    try:
        # Convert page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
        img_data = pix.tobytes("png")
        
        # OCR the image data
        from PIL import Image
        import io
        import pytesseract
        
        img = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(img)
        
        return text
    
    except Exception as e:
        print(f"   OCR failed: {e}")
        return ""


async def extract_from_image(image_path: Path) -> str:
    """
    Extract text from image using Tesseract OCR
    """
    try:
        from PIL import Image
        import pytesseract
        
        # Open and preprocess image
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Perform OCR
        text = pytesseract.image_to_string(img)
        
        return clean_extracted_text(text)
    
    except Exception as e:
        raise Exception(f"Image OCR failed: {str(e)}")


def clean_extracted_text(text: str) -> str:
    """
    Clean up extracted text
    - Remove excessive whitespace
    - Normalize line breaks
    - Remove page numbers and headers (basic)
    """
    import re
    
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove multiple newlines (keep paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove common page artifacts
    text = re.sub(r'\n\d+\n', '\n', text)  # Standalone page numbers
    text = re.sub(r'\f', '\n\n', text)  # Form feed characters
    
    # Trim
    text = text.strip()
    
    return text


def estimate_ocr_quality(text: str) -> float:
    """
    Estimate OCR quality based on text characteristics
    Returns: 0.0 to 1.0 (higher is better)
    """
    if not text:
        return 0.0
    
    import re
    
    # Count various issues
    total_chars = len(text)
    
    # Check for common OCR errors
    weird_chars = len(re.findall(r'[^\w\s.,!?;:\-\'\"()]', text))
    isolated_chars = len(re.findall(r'\s\w\s', text))
    number_letter_mix = len(re.findall(r'\d[a-zA-Z]|[a-zA-Z]\d', text))
    
    # Calculate quality score
    error_ratio = (weird_chars + isolated_chars + number_letter_mix) / max(total_chars, 1)
    quality = max(0.0, 1.0 - (error_ratio * 10))
    
    return quality


async def extract_with_confidence(file_path: Path) -> dict:
    """
    Extract text and estimate confidence
    Useful for showing OCR quality warnings
    """
    text = await extract_text(file_path)
    
    # Determine if OCR was used
    is_ocr = file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']
    
    confidence = 1.0
    if is_ocr:
        confidence = estimate_ocr_quality(text)
    
    return {
        "text": text,
        "confidence": confidence,
        "method": "ocr" if is_ocr else "direct",
        "warnings": [] if confidence > 0.7 else ["Low OCR quality detected"]
    }


# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python text_extractor.py <file_path>")
        sys.exit(1)
    
    async def test():
        file_path = Path(sys.argv[1])
        print(f"Extracting text from: {file_path}")
        
        result = await extract_with_confidence(file_path)
        
        print(f"\nMethod: {result['method']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Text length: {len(result['text'])} characters")
        print("\n" + "="*60)
        print(result['text'][:500])
        print("="*60)
    
    asyncio.run(test())
