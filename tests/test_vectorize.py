import os
import glob
import pytest


@pytest.fixture
def sample_bitmap(tmp_path):
    """Create a simple test bitmap for vectorization."""
    import cv2
    import numpy as np

    # Create a simple black square on white background
    img = np.ones((100, 80), dtype=np.uint8) * 255
    img[20:80, 15:65] = 0  # black rectangle
    path = str(tmp_path / "test_char.png")
    cv2.imwrite(path, img)
    return path


def test_vectorize_single_glyph(sample_bitmap, tmp_path):
    """Vectorizing a bitmap should produce an SVG file."""
    from scripts.vectorize import vectorize_glyph

    svg_path = str(tmp_path / "test_char.svg")
    result = vectorize_glyph(sample_bitmap, svg_path)
    assert os.path.exists(svg_path)
    with open(svg_path) as f:
        content = f.read()
    assert "<svg" in content or "<path" in content


def test_vectorize_all_produces_svgs():
    """Vectorizing all bitmaps should produce matching SVGs."""
    from scripts.vectorize import vectorize_all

    svgs = vectorize_all("glyphs/bitmaps", "glyphs/svg")
    bitmaps = glob.glob("glyphs/bitmaps/*.png")
    assert len(svgs) > 0
    for svg in svgs:
        assert os.path.exists(svg)
