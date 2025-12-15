import asyncio
from pathlib import Path
from unified_extractor.extractor import extract_text

async def test_image_ocr(image_path):
    path = Path(image_path)
    text = await extract_text(path)
    print("----- OCR OUTPUT -----")
    print(text)
    print("----------------------")

if __name__ == "__main__":
    # Replace with a sample image containing text
    image_file = "tests/test_sample.png"
    asyncio.run(test_image_ocr(image_file))
