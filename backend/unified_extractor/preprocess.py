# ----------------------------
# file: unified_extractor/preprocess.py
# ----------------------------
"""Image preprocessing and line segmentation."""
import cv2
import numpy as np
from typing import List

def preprocess_image_array(img_array: np.ndarray) -> np.ndarray:
    """Accepts a BGR numpy image (as read by cv2) or a grayscale array.
    Returns a binarized image suitable for line segmentation.
    """
    if img_array is None or img_array.size == 0:
        return np.array([])

    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_array

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    if np.sum(binary == 0) > np.sum(binary == 255):
        binary = cv2.bitwise_not(binary)

    return binary

def detect_text_lines(image_array: np.ndarray) -> List[np.ndarray]:
    if image_array.size == 0:
        return []

    horizontal = np.sum(image_array == 0, axis=1)
    lines = []
    in_line = False
    start = 0
    thresh = max(5, image_array.shape[1] * 0.01)

    for y, v in enumerate(horizontal):
        if v > thresh and not in_line:
            start = y
            in_line = True
        elif v <= thresh and in_line:
            end = y
            if end - start > 5:
                line = image_array[max(0, start-3):min(image_array.shape[0], end+3)]
                col = np.sum(line == 0, axis=0)
                nz = np.where(col > 0)[0]
                if nz.size:
                    left, right = max(0, nz[0]-5), min(line.shape[1], nz[-1]+5)
                    seg = line[:, left:right]
                    if seg.shape[0] > 5 and seg.shape[1] > 10:
                        lines.append(seg)
            in_line = False

    return lines
