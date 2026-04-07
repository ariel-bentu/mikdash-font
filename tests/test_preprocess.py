import os
import cv2
import numpy as np
import pytest


def test_preprocess_produces_binary_image():
    """Preprocessing should produce a clean binary image."""
    from scripts.preprocess import preprocess

    result = preprocess("font.jpg")
    assert result is not None
    assert len(result.shape) == 2, "Should be grayscale (2D array)"
    unique_vals = set(np.unique(result))
    assert unique_vals.issubset({0, 255}), f"Should be binary, got values: {unique_vals}"


def test_preprocess_saves_output():
    """Preprocessing should save the result to glyphs/preprocessed.png."""
    from scripts.preprocess import preprocess

    preprocess("font.jpg")
    assert os.path.exists("glyphs/preprocessed.png")
    img = cv2.imread("glyphs/preprocessed.png", cv2.IMREAD_GRAYSCALE)
    assert img is not None
