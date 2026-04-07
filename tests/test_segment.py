import os
import glob
import pytest


def test_segment_produces_bitmap_files():
    """Segmentation should produce individual glyph bitmap PNGs."""
    from scripts.segment import segment

    segment("glyphs/preprocessed.png")
    bitmaps = glob.glob("glyphs/bitmaps/*.png")
    assert len(bitmaps) > 0, "Should produce at least some glyph bitmaps"


def test_segment_bitmaps_are_valid_images():
    """Each bitmap should be a valid non-empty image."""
    import cv2

    from scripts.segment import segment

    segment("glyphs/preprocessed.png")
    for path in glob.glob("glyphs/bitmaps/*.png"):
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Invalid image: {path}"
        assert img.shape[0] > 5 and img.shape[1] > 5, f"Image too small: {path} {img.shape}"
