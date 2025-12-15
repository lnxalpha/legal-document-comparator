# backend/test_easyocr.py
import cv2
import easyocr

reader = easyocr.Reader(["en"], gpu=False)
img = cv2.imread("tests/test_sample.png")
results = reader.readtext(img)

for r in results:
    print(r)
