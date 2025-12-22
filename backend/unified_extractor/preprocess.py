# ----------------------------
# file: unified_extractor/preprocess.py
# ----------------------------
"""Image preprocessing and line segmentation with improved detection."""
import cv2
import numpy as np
from typing import List, Tuple
import logging

LOG = logging.getLogger(__name__)


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


def detect_text_line_coordinates(image_array: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect text lines and return their coordinates.

    Returns:
        List of (y_start, y_end, x_start, x_end) tuples

    This allows cropping from the ORIGINAL image, not the preprocessed one.
    """
    if image_array.size == 0:
        return []

    horizontal = np.sum(image_array == 0, axis=1)

    # IMPROVED: Use median-based adaptive threshold
    active_rows = horizontal[horizontal > 0]
    if len(active_rows) == 0:
        return []

    median_density = np.median(active_rows)
    thresh = max(3, median_density * 0.3)  # 30% of median active row

    lines = []
    in_line = False
    start = 0

    for y, v in enumerate(horizontal):
        if v > thresh and not in_line:
            start = y
            in_line = True
        elif v <= thresh and in_line:
            end = y

            # IMPROVED: Minimum line height check (skip noise)
            if end - start < 8:
                in_line = False
                continue

            # Extract line region for validation
            line_region = image_array[start:end, :]

            # IMPROVED: Check if this is actually text
            if is_likely_text_region(line_region):
                # Find horizontal bounds (left/right edges)
                vertical = np.sum(line_region == 0, axis=0)
                nz = np.where(vertical > 0)[0]

                if nz.size > 0:
                    x_start = max(0, nz[0] - 5)
                    x_end = min(image_array.shape[1], nz[-1] + 5)
                    y_start = max(0, start - 3)
                    y_end = min(image_array.shape[0], end + 3)

                    lines.append((y_start, y_end, x_start, x_end))

            in_line = False

    # POST-PROCESS: Split merged lines
    refined_lines = []
    for coords in lines:
        y_start, y_end, x_start, x_end = coords
        height = y_end - y_start

        # If line is abnormally tall, try to split it
        if height > 40:  # Typical line is 15-30px
            line_region = image_array[y_start:y_end, x_start:x_end]
            sub_lines = split_tall_line(line_region, y_start, x_start, x_end)
            refined_lines.extend(sub_lines)
        else:
            refined_lines.append(coords)

    LOG.debug(f"Detected {len(refined_lines)} text lines")
    return refined_lines


def is_likely_text_region(region: np.ndarray) -> bool:
    """
    Distinguish text from horizontal lines/borders.

    Text has:
    - Variation in horizontal density
    - Multiple connected components
    """
    if region.size == 0 or region.shape[0] < 5:
        return False

    # Text has variation in horizontal density
    horizontal_density = np.sum(region == 0, axis=1)
    variation = np.std(horizontal_density)

    # Horizontal lines have uniform density
    if variation < 2:  # Too uniform = line, not text
        return False

    # Text has multiple connected components
    try:
        num_labels, labels = cv2.connectedComponents(region)
        if num_labels < 3:  # Too few components = not text
            return False
    except Exception as e:
        LOG.warning(f"Connected components check failed: {e}")
        return True  # Assume it's text if check fails

    return True


def split_tall_line(
    line_region: np.ndarray,
    base_y: int,
    base_x_start: int,
    base_x_end: int
) -> List[Tuple[int, int, int, int]]:
    """
    Split merged lines by finding internal gaps (valleys).

    This handles cases where two sentences are detected as one tall line.
    """
    if line_region.size == 0:
        return []

    horizontal = np.sum(line_region == 0, axis=1)

    # Find valleys (gaps between lines)
    valleys = []
    for i in range(1, len(horizontal) - 1):
        # Valley = significantly lower density than neighbors
        if horizontal[i] < horizontal[i-1] * 0.5 and horizontal[i] < horizontal[i+1] * 0.5:
            valleys.append(i)

    if not valleys:
        # Can't split, return as-is
        height = line_region.shape[0]
        return [(base_y, base_y + height, base_x_start, base_x_end)]

    # Split at deepest valleys
    split_points = [0] + valleys + [line_region.shape[0]]
    sub_lines = []

    for i in range(len(split_points) - 1):
        y1, y2 = split_points[i], split_points[i+1]

        # Minimum line height
        if y2 - y1 > 8:
            sub_lines.append((
                base_y + y1,
                base_y + y2,
                base_x_start,
                base_x_end
            ))

    LOG.debug(f"Split tall line ({line_region.shape[0]}px) into {len(sub_lines)} sub-lines")
    return sub_lines


# Keep old function for backward compatibility, but deprecate it
def detect_text_lines(image_array: np.ndarray) -> List[np.ndarray]:
    """
    DEPRECATED: Returns image crops instead of coordinates.
    Use detect_text_line_coordinates() instead.
    """
    LOG.warning("detect_text_lines() is deprecated. Use detect_text_line_coordinates()")

    coords = detect_text_line_coordinates(image_array)

    # Convert coordinates back to crops for backward compatibility
    crops = []
    for (y_start, y_end, x_start, x_end) in coords:
        crop = image_array[y_start:y_end, x_start:x_end]
        crops.append(crop)

    return crops
