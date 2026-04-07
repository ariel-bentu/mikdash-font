"""Step 2: Segment preprocessed image into individual Hebrew glyph bitmaps.

Strategy:
1. Crop out just the Hebrew text area (exclude headers, line numbers, footnotes)
2. Find text lines via horizontal projection profile
3. Within each line, find character contours
4. Group nearby contours (base + diacritics)
5. Save each character as a separate bitmap

Since automatic character identification is unreliable, this script extracts
ALL detected characters as numbered bitmaps. The user then manually renames
each bitmap to its Hebrew letter name (e.g., "alef.png", "bet.png") to map
them to the correct Unicode codepoints.

Multiple instances of the same letter should be named like "alef_1.png",
"alef_2.png" — the best sample will be selected later.
"""

import cv2
import numpy as np
import os


def find_text_lines(binary: np.ndarray, min_gap: int = 15) -> list[tuple[int, int]]:
    """Find horizontal text line regions using projection profile.

    Returns list of (y_start, y_end) tuples for each line.
    """
    # Invert so text is white (255) on black (0) for projection
    inv = 255 - binary

    # Horizontal projection — sum of white pixels per row
    h_proj = np.sum(inv, axis=1)

    # Threshold: rows with significant ink
    threshold = np.max(h_proj) * 0.02
    in_line = h_proj > threshold

    lines = []
    start = None
    for i, active in enumerate(in_line):
        if active and start is None:
            start = i
        elif not active and start is not None:
            if i - start > min_gap:  # skip tiny noise
                lines.append((start, i))
            start = None
    if start is not None and len(binary) - start > min_gap:
        lines.append((start, len(binary)))

    return lines


def find_characters_in_line(
    line_img: np.ndarray, min_area: int = 50
) -> list[tuple[int, int, int, int]]:
    """Find individual character bounding boxes in a single text line.

    Returns list of (x, y, w, h) bounding boxes sorted right-to-left (Hebrew reading order).
    """
    inv = 255 - line_img
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        boxes.append((x, y, w, h))

    # Sort right-to-left for Hebrew reading order
    boxes.sort(key=lambda b: b[0], reverse=True)
    return boxes


def merge_overlapping_boxes(
    boxes: list[tuple[int, int, int, int]], x_overlap_threshold: int = 5
) -> list[tuple[int, int, int, int]]:
    """Merge vertically overlapping boxes (base letter + diacritical mark).

    If two boxes overlap horizontally within threshold, merge them into one.
    """
    if not boxes:
        return []

    # Sort by x position
    sorted_boxes = sorted(boxes, key=lambda b: b[0])
    merged = [sorted_boxes[0]]

    for box in sorted_boxes[1:]:
        prev = merged[-1]
        px, py, pw, ph = prev
        bx, by, bw, bh = box

        # Check horizontal overlap
        if bx < px + pw + x_overlap_threshold:
            # Merge: union of bounding boxes
            nx = min(px, bx)
            ny = min(py, by)
            nw = max(px + pw, bx + bw) - nx
            nh = max(py + ph, by + bh) - ny
            merged[-1] = (nx, ny, nw, nh)
        else:
            merged.append(box)

    return merged


def segment(preprocessed_path: str) -> list[str]:
    """Segment the preprocessed image into individual character bitmaps.

    Returns list of saved bitmap file paths.
    """
    binary = cv2.imread(preprocessed_path, cv2.IMREAD_GRAYSCALE)
    if binary is None:
        raise FileNotFoundError(f"Cannot read: {preprocessed_path}")

    os.makedirs("glyphs/bitmaps", exist_ok=True)

    lines = find_text_lines(binary)
    print(f"Found {len(lines)} text lines")

    saved_paths = []
    char_index = 0

    for line_idx, (y_start, y_end) in enumerate(lines):
        line_img = binary[y_start:y_end, :]
        boxes = find_characters_in_line(line_img)
        boxes = merge_overlapping_boxes(boxes)

        for bx, by, bw, bh in boxes:
            # Add padding around the character
            pad = 4
            y1 = max(0, y_start + by - pad)
            y2 = min(binary.shape[0], y_start + by + bh + pad)
            x1 = max(0, bx - pad)
            x2 = min(binary.shape[1], bx + bw + pad)

            char_img = binary[y1:y2, x1:x2]

            # Skip very small or very large detections (likely noise or merged chars)
            if char_img.shape[0] < 10 or char_img.shape[1] < 10:
                continue
            if char_img.shape[0] > (y_end - y_start) * 2:
                continue

            filename = f"glyphs/bitmaps/char_{line_idx:02d}_{char_index:03d}.png"
            cv2.imwrite(filename, char_img)
            saved_paths.append(filename)
            char_index += 1

    print(f"Extracted {len(saved_paths)} character bitmaps to glyphs/bitmaps/")
    return saved_paths


if __name__ == "__main__":
    segment("glyphs/preprocessed.png")
