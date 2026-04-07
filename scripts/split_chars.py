"""Split multi-character bitmap pieces into individual characters.

Uses vertical projection profiles to find gaps between characters,
then splits at those gaps. Outputs individual character images into
a target directory.
"""

import sys
from pathlib import Path

import cv2
import numpy as np


def split_image(img_path: str, output_dir: str, min_gap: int = 3) -> list[str]:
    """Split a multi-character image into individual characters.

    Parameters
    ----------
    img_path : str
        Path to the multi-character bitmap PNG.
    output_dir : str
        Directory to write individual character images.
    min_gap : int
        Minimum number of consecutive blank columns to consider as a gap.

    Returns
    -------
    list[str]
        Paths to the output character images.
    """
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Could not read {img_path}")
        return []

    # Binarize: dark ink on white background
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Vertical projection: sum of ink pixels per column
    v_proj = np.sum(binary, axis=0) / 255  # count of ink pixels per column

    # Find gaps (columns with no or very little ink)
    threshold = max(2, img.shape[0] * 0.02)  # 2% of height
    is_gap = v_proj < threshold

    # Find gap regions
    gaps = []
    in_gap = False
    gap_start = 0
    for col in range(len(is_gap)):
        if is_gap[col] and not in_gap:
            gap_start = col
            in_gap = True
        elif not is_gap[col] and in_gap:
            gap_end = col
            if gap_end - gap_start >= min_gap:
                gaps.append((gap_start, gap_end))
            in_gap = False

    if not gaps:
        print(f"No gaps found in {img_path} — may be a single character or touching chars")
        return []

    # Split at gap midpoints
    split_points = [0]
    for gap_start, gap_end in gaps:
        mid = (gap_start + gap_end) // 2
        split_points.append(mid)
    split_points.append(img.shape[1])

    # Extract individual characters
    stem = Path(img_path).stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_paths = []
    char_idx = 0
    for i in range(len(split_points) - 1):
        left = split_points[i]
        right = split_points[i + 1]

        char_img = img[:, left:right]

        # Trim top/bottom whitespace
        binary_slice = binary[:, left:right]
        row_sums = np.sum(binary_slice, axis=1)
        ink_rows = np.where(row_sums > 0)[0]
        if len(ink_rows) == 0:
            continue

        top = max(0, ink_rows[0] - 2)
        bottom = min(img.shape[0], ink_rows[-1] + 3)
        char_img = img[top:bottom, left:right]

        # Also trim left/right whitespace
        col_sums = np.sum(binary_slice[top:bottom, :], axis=0)
        ink_cols = np.where(col_sums > 0)[0]
        if len(ink_cols) == 0:
            continue
        cleft = max(0, ink_cols[0] - 2)
        cright = min(right - left, ink_cols[-1] + 3)
        char_img = char_img[:, cleft:cright]

        # Skip very small fragments (noise)
        if char_img.shape[0] < 10 or char_img.shape[1] < 10:
            continue

        out_path = out_dir / f"{stem}_char{char_idx:02d}.png"
        cv2.imwrite(str(out_path), char_img)
        output_paths.append(str(out_path))
        char_idx += 1

    return output_paths


def main():
    input_dir = "glyphs/multiple-chars"
    output_dir = "glyphs/split-chars"

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Input directory {input_dir} not found")
        sys.exit(1)

    total = 0
    for img_file in sorted(input_path.glob("*.png")):
        print(f"\nProcessing: {img_file.name}")
        results = split_image(str(img_file), output_dir)
        for r in results:
            print(f"  -> {Path(r).name}")
        total += len(results)

    print(f"\nDone. Split into {total} individual character images in {output_dir}/")


if __name__ == "__main__":
    main()
