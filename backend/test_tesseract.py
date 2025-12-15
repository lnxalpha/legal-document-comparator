# backend/test_tesseract.py
import cv2
import pytesseract

img = cv2.imread("tests/test_sample.png")
print(pytesseract.image_to_string(img))
