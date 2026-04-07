"""Step 3: Convert glyph bitmaps to SVG vector outlines using potrace.

Potrace requires BMP or PBM input. We convert PNGs to PBM, run potrace,
and get SVG output with clean Bezier curves.
"""

import glob
import os
import subprocess
import tempfile

import cv2
import numpy as np


def png_to_pbm(png_path: str, pbm_path: str) -> None:
    """Convert a PNG bitmap to PBM (Portable Bitmap) format for potrace.

    Potrace expects: 1 = black (foreground), 0 = white (background).
    Our PNGs have 0 = black text, 255 = white background, so we invert.
    """
    img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Cannot read: {png_path}")

    # Ensure binary
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    # Invert: potrace PBM format uses 1=black, our images have 0=black
    # PBM P4 format: 1-bits are black, 0-bits are white
    # So we need to invert our image before saving
    inverted = 255 - binary

    h, w = inverted.shape

    # Write PBM P1 (ASCII) format — simple and reliable
    with open(pbm_path, "w") as f:
        f.write(f"P1\n{w} {h}\n")
        for row in inverted:
            line = " ".join("1" if pixel > 127 else "0" for pixel in row)
            f.write(line + "\n")


def vectorize_glyph(png_path: str, svg_path: str) -> str:
    """Convert a single glyph bitmap to SVG using potrace.

    Returns the path to the created SVG file.
    """
    with tempfile.NamedTemporaryFile(suffix=".pbm", delete=False) as tmp:
        pbm_path = tmp.name

    try:
        png_to_pbm(png_path, pbm_path)

        result = subprocess.run(
            [
                "potrace",
                pbm_path,
                "-b", "svg",        # SVG output
                "-o", svg_path,
                "--flat",            # no grouping, simpler SVG
                "--turdsize", "3",   # remove small noise blobs
                "-a", "1.0",         # corner threshold (smoother curves)
                "-O", "0.2",         # optimization tolerance
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"potrace failed: {result.stderr}")

    finally:
        os.unlink(pbm_path)

    return svg_path


def vectorize_all(bitmaps_dir: str, svg_dir: str) -> list[str]:
    """Vectorize all PNG bitmaps in a directory to SVGs.

    Returns list of created SVG file paths.
    """
    os.makedirs(svg_dir, exist_ok=True)

    png_files = sorted(glob.glob(os.path.join(bitmaps_dir, "*.png")))
    if not png_files:
        print(f"No PNG files found in {bitmaps_dir}")
        return []

    svg_paths = []
    for png_path in png_files:
        name = os.path.splitext(os.path.basename(png_path))[0]
        svg_path = os.path.join(svg_dir, f"{name}.svg")
        try:
            vectorize_glyph(png_path, svg_path)
            svg_paths.append(svg_path)
            print(f"  {name}.png -> {name}.svg")
        except RuntimeError as e:
            print(f"  WARNING: Failed to vectorize {name}: {e}")

    print(f"Vectorized {len(svg_paths)}/{len(png_files)} glyphs to {svg_dir}/")
    return svg_paths


if __name__ == "__main__":
    vectorize_all("glyphs/bitmaps", "glyphs/svg")
