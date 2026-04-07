"""Step 1: Preprocess font.jpg into a clean binary image."""

import cv2
import numpy as np
import os


def preprocess(image_path: str) -> np.ndarray:
    """Load image, convert to clean binary (black text on white background).

    Returns the binary image as a numpy array (0=text, 255=background).
    Also saves to glyphs/preprocessed.png.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold — handles uneven scan lighting
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10
    )

    # Clean up noise with morphological operations
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Save output
    os.makedirs("glyphs", exist_ok=True)
    cv2.imwrite("glyphs/preprocessed.png", binary)

    return binary


if __name__ == "__main__":
    result = preprocess("font.jpg")
    h, w = result.shape
    print(f"Preprocessed image: {w}x{h}, saved to glyphs/preprocessed.png")
