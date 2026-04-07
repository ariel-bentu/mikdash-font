# Mikdash Font Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reverse-engineer the Hebrew typeface from `font.jpg` into a TTF font family (Mikdash-Regular = hollow, Mikdash-Bold = filled) with combining diacritical marks (diamond, circle) and borrowed Latin/numbers from EB Garamond.

**Architecture:** A 4-stage Python pipeline: (1) preprocess the scanned image, (2) segment and extract individual Hebrew glyphs as bitmaps, (3) vectorize bitmaps to SVG via potrace, (4) assemble SVGs into TTF fonts using fontTools with pyclipper for hollow glyph generation. Each stage is a standalone script that reads from the previous stage's output directory.

**Tech Stack:** Python 3.10+, OpenCV, Pillow, potrace CLI, fontTools, pyclipper, EB Garamond (OFL)

---

## File Structure

```
fontMikdash/
├── font.jpg                          # Source image (existing)
├── requirements.txt                  # Python dependencies
├── scripts/
│   ├── preprocess.py                 # Image cleanup → glyphs/preprocessed.png
│   ├── segment.py                    # Glyph extraction → glyphs/bitmaps/*.png
│   ├── vectorize.py                  # Bitmap → SVG → glyphs/svg/*.svg
│   ├── assemble.py                   # SVG → TTF → output/*.ttf
│   └── helpers.py                    # Shared constants (glyph names, Unicode mappings)
├── glyphs/
│   ├── bitmaps/                      # Cropped glyph PNGs (one per character)
│   └── svg/                          # Vectorized SVGs (one per character)
├── donor/
│   └── EBGaramond-Regular.ttf        # Downloaded EB Garamond for Latin/numbers
├── output/
│   ├── Mikdash-Regular.ttf
│   └── Mikdash-Bold.ttf
└── tests/
    ├── test_preprocess.py
    ├── test_segment.py
    ├── test_vectorize.py
    └── test_assemble.py
```

---

### Task 1: Project Setup and Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `scripts/helpers.py`

- [ ] **Step 1: Create requirements.txt**

```
opencv-python>=4.10
Pillow>=10.0
fonttools[ufo,lxml,woff,unicode]>=4.50
pyclipper>=1.3
pytest>=7.0
```

- [ ] **Step 2: Install system dependency potrace**

Run: `brew install potrace`
Expected: potrace installed, verify with `potrace --version`

- [ ] **Step 3: Download EB Garamond**

Run:
```bash
mkdir -p donor
curl -L -o donor/EBGaramond-Regular.ttf "https://github.com/georgd/EB-Garamond/raw/master/otf/EBGaramond12-Regular.otf"
```

Note: If the above URL doesn't work, download EB Garamond from Google Fonts:
```bash
curl -L -o /tmp/eb-garamond.zip "https://fonts.google.com/download?family=EB+Garamond"
unzip /tmp/eb-garamond.zip -d /tmp/eb-garamond
cp /tmp/eb-garamond/static/EBGaramond-Regular.ttf donor/
cp /tmp/eb-garamond/static/EBGaramond-Bold.ttf donor/
```

- [ ] **Step 4: Create virtual environment and install**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: all packages install without errors.

- [ ] **Step 5: Create helpers.py with shared constants**

```python
"""Shared constants for the Mikdash font pipeline."""

# Hebrew letter names and their Unicode codepoints
HEBREW_LETTERS = {
    "alef": 0x05D0,
    "bet": 0x05D1,
    "gimel": 0x05D2,
    "dalet": 0x05D3,
    "he": 0x05D4,
    "vav": 0x05D5,
    "zayin": 0x05D6,
    "chet": 0x05D7,
    "tet": 0x05D8,
    "yod": 0x05D9,
    "kaf": 0x05DB,
    "final_kaf": 0x05DA,
    "lamed": 0x05DC,
    "mem": 0x05DE,
    "final_mem": 0x05DD,
    "nun": 0x05E0,
    "final_nun": 0x05DF,
    "samekh": 0x05E1,
    "ayin": 0x05E2,
    "pe": 0x05E4,
    "final_pe": 0x05E3,
    "tsade": 0x05E6,
    "final_tsade": 0x05E5,
    "qof": 0x05E7,
    "resh": 0x05E8,
    "shin": 0x05E9,
    "tav": 0x05EA,
}

# Special marks — Private Use Area codepoints
COMBINING_DIAMOND = 0xE001  # combining mark above
COMBINING_CIRCLE = 0xE002   # combining mark above
STANDALONE_CIRCLE = 0x25CB  # WHITE CIRCLE — standalone glyph

# Font metrics (will be calibrated from image measurements)
UNITS_PER_EM = 1000
ASCENDER = 800
DESCENDER = -200
LINE_GAP = 0

# Stroke width for hollow (Regular) glyphs, as fraction of UPM
HOLLOW_STROKE_RATIO = 0.06  # 6% of em — will calibrate from image

FONT_FAMILY = "Mikdash"
```

- [ ] **Step 6: Create directory structure**

Run:
```bash
mkdir -p glyphs/bitmaps glyphs/svg output tests scripts
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt scripts/helpers.py
git commit -m "feat: add project dependencies and shared constants"
```

---

### Task 2: Image Preprocessing (`scripts/preprocess.py`)

**Files:**
- Create: `scripts/preprocess.py`
- Create: `tests/test_preprocess.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_preprocess.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_preprocess.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement 01_preprocess.py**

Create `scripts/preprocess.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_preprocess.py -v`
Expected: PASS

- [ ] **Step 5: Run the script standalone and visually inspect**

Run: `cd /Users/i022021/dev/fontMikdash && python scripts/01_preprocess.py`
Expected: prints image dimensions, creates `glyphs/preprocessed.png`. Open the file and verify text is cleanly separated from background.

- [ ] **Step 6: Commit**

```bash
git add scripts/preprocess.py tests/test_preprocess.py
git commit -m "feat: add image preprocessing script"
```

---

### Task 3: Glyph Segmentation (`scripts/segment.py`)

**Files:**
- Create: `scripts/segment.py`
- Create: `tests/test_segment.py`

This is the most complex step. The image has 15 lines of Hebrew text. We need to:
1. Detect text lines using horizontal projection
2. Within each line, detect individual characters using contour detection
3. Map detected characters to Hebrew letter names
4. Save the best sample of each unique letter

Since the image is a scholarly transcription, not all 27 Hebrew letters may appear. We need to identify which ones are present and flag missing ones.

- [ ] **Step 1: Write the failing test**

Create `tests/test_segment.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_segment.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement 02_segment.py**

Create `scripts/segment.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_segment.py -v`
Expected: PASS (requires preprocessed.png from Task 2)

- [ ] **Step 5: Run standalone and inspect results**

Run: `cd /Users/i022021/dev/fontMikdash && python scripts/02_segment.py`
Expected: prints line count and character count. Inspect `glyphs/bitmaps/` — each file should contain a cleanly isolated Hebrew character.

- [ ] **Step 6: Manual glyph identification**

This is a manual step. Open `glyphs/bitmaps/` and:
1. Review each extracted character bitmap
2. Identify which Hebrew letter it is
3. Rename files to their letter names: `alef.png`, `bet.png`, etc.
4. For multiple samples of same letter, keep the clearest one
5. Note any missing letters from the 27 required

The segmentation parameters (min_area, x_overlap_threshold, padding) may need tuning based on the actual extraction results. Adjust and re-run as needed.

- [ ] **Step 7: Commit**

```bash
git add scripts/segment.py tests/test_segment.py
git commit -m "feat: add glyph segmentation script"
```

---

### Task 4: Vectorization (`scripts/vectorize.py`)

**Files:**
- Create: `scripts/vectorize.py`
- Create: `tests/test_vectorize.py`

Converts the manually-identified glyph bitmaps into SVG vector paths using potrace.

- [ ] **Step 1: Write the failing test**

Create `tests/test_vectorize.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_vectorize.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement 03_vectorize.py**

Create `scripts/vectorize.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_vectorize.py -v`
Expected: PASS (requires potrace installed and bitmap files from Task 3)

- [ ] **Step 5: Run standalone and inspect SVGs**

Run: `cd /Users/i022021/dev/fontMikdash && python scripts/03_vectorize.py`
Expected: SVGs in `glyphs/svg/`. Open them in a browser or Inkscape to verify glyph outlines look correct. This is the key quality checkpoint — look for:
- Clean, smooth curves
- No stray artifacts
- Faithful reproduction of the original character shapes

- [ ] **Step 6: Commit**

```bash
git add scripts/vectorize.py tests/test_vectorize.py
git commit -m "feat: add glyph vectorization script using potrace"
```

---

### Task 5: SVG Parsing Utility

**Files:**
- Add to: `scripts/helpers.py`
- Create: `tests/test_svg_parser.py`

Before we can assemble the font, we need to parse SVG path data into fontTools-compatible glyph contours.

- [ ] **Step 1: Write the failing test**

Create `tests/test_svg_parser.py`:

```python
import pytest


def test_parse_svg_path_moveto_lineto():
    """Should parse simple M/L path commands into points."""
    from scripts.helpers import parse_svg_to_contours

    # Simple square: M 0,0 L 100,0 L 100,100 L 0,100 Z
    svg_content = '''<svg><path d="M 0,0 L 100,0 L 100,100 L 0,100 Z"/></svg>'''
    contours = parse_svg_to_contours(svg_content)
    assert len(contours) == 1
    assert len(contours[0]) >= 4  # at least 4 points for a square


def test_parse_svg_path_curves():
    """Should parse cubic Bezier (C) commands."""
    from scripts.helpers import parse_svg_to_contours

    svg_content = '''<svg><path d="M 0,0 C 10,20 30,40 50,50 Z"/></svg>'''
    contours = parse_svg_to_contours(svg_content)
    assert len(contours) == 1
    assert len(contours[0]) > 0


def test_parse_svg_multiple_contours():
    """SVG with multiple subpaths should produce multiple contours."""
    from scripts.helpers import parse_svg_to_contours

    svg_content = '''<svg>
        <path d="M 0,0 L 10,0 L 10,10 Z M 20,20 L 30,20 L 30,30 Z"/>
    </svg>'''
    contours = parse_svg_to_contours(svg_content)
    assert len(contours) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_svg_parser.py -v`
Expected: FAIL — function not found

- [ ] **Step 3: Add SVG parsing to helpers.py**

Append to `scripts/helpers.py`:

```python
import re
import xml.etree.ElementTree as ET


def parse_svg_to_contours(svg_content: str) -> list[list[tuple]]:
    """Parse SVG path data into contours suitable for fontTools.

    Each contour is a list of (x, y, on_curve) tuples where on_curve is True
    for on-curve points and False for off-curve (control) points.

    Handles M (moveto), L (lineto), C (cubic bezier), Q (quadratic bezier), Z (close).
    Potrace outputs only M, C, L, and Z commands.

    Returns list of contours. Coordinates are in SVG space (y-down).
    """
    root = ET.fromstring(svg_content)
    # Handle SVG namespace
    ns = {"svg": "http://www.w3.org/2000/svg"}
    paths = root.findall(".//svg:path", ns)
    if not paths:
        paths = root.findall(".//{http://www.w3.org/2000/svg}path")
    if not paths:
        paths = root.findall(".//path")

    all_contours = []
    for path_elem in paths:
        d = path_elem.get("d", "")
        contours = _parse_path_d(d)
        all_contours.extend(contours)

    return all_contours


def _parse_path_d(d: str) -> list[list[tuple]]:
    """Parse an SVG path 'd' attribute into contours.

    Returns list of contours, each a list of (x, y, on_curve) tuples.
    """
    # Tokenize: split into commands and numbers
    tokens = re.findall(r"[MmLlCcQqZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)

    contours = []
    current_contour = []
    cx, cy = 0.0, 0.0  # current position
    i = 0

    while i < len(tokens):
        cmd = tokens[i]
        i += 1

        if cmd in ("M", "m"):
            if current_contour:
                contours.append(current_contour)
                current_contour = []
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "m":
                x, y = cx + x, cy + y
            cx, cy = x, y
            current_contour.append((x, y, True))

            # Implicit lineto after moveto
            while i < len(tokens) and tokens[i] not in "MmLlCcQqZz":
                x, y = float(tokens[i]), float(tokens[i + 1])
                i += 2
                if cmd == "m":
                    x, y = cx + x, cy + y
                cx, cy = x, y
                current_contour.append((x, y, True))

        elif cmd in ("L", "l"):
            while i < len(tokens) and tokens[i] not in "MmLlCcQqZz":
                x, y = float(tokens[i]), float(tokens[i + 1])
                i += 2
                if cmd == "l":
                    x, y = cx + x, cy + y
                cx, cy = x, y
                current_contour.append((x, y, True))

        elif cmd in ("C", "c"):
            while i < len(tokens) and tokens[i] not in "MmLlCcQqZz":
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
                x, y = float(tokens[i + 4]), float(tokens[i + 5])
                i += 6
                if cmd == "c":
                    x1, y1 = cx + x1, cy + y1
                    x2, y2 = cx + x2, cy + y2
                    x, y = cx + x, cy + y
                # Cubic bezier: two off-curve control points + endpoint
                current_contour.append((x1, y1, False))
                current_contour.append((x2, y2, False))
                current_contour.append((x, y, True))
                cx, cy = x, y

        elif cmd in ("Q", "q"):
            while i < len(tokens) and tokens[i] not in "MmLlCcQqZz":
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x, y = float(tokens[i + 2]), float(tokens[i + 3])
                i += 4
                if cmd == "q":
                    x1, y1 = cx + x1, cy + y1
                    x, y = cx + x, cy + y
                current_contour.append((x1, y1, False))
                current_contour.append((x, y, True))
                cx, cy = x, y

        elif cmd in ("Z", "z"):
            if current_contour:
                contours.append(current_contour)
                current_contour = []

    if current_contour:
        contours.append(current_contour)

    return contours


def normalize_contours(
    contours: list[list[tuple]], target_height: int = 800, units_per_em: int = 1000
) -> list[list[tuple]]:
    """Normalize contours to fit within font em-square.

    - Scales to target_height (ascender height)
    - Flips Y axis (SVG is y-down, font is y-up)
    - Centers horizontally

    Returns normalized contours and the glyph advance width.
    """
    if not contours:
        return [], 0

    # Find bounding box across all contours
    all_points = [p for contour in contours for p in contour]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    svg_width = max_x - min_x
    svg_height = max_y - min_y

    if svg_height == 0 or svg_width == 0:
        return contours, 0

    # Scale to fit target height
    scale = target_height / svg_height

    normalized = []
    for contour in contours:
        new_contour = []
        for x, y, on_curve in contour:
            # Translate to origin, scale, flip Y
            nx = (x - min_x) * scale
            ny = target_height - (y - min_y) * scale  # flip Y
            new_contour.append((round(nx), round(ny), on_curve))
        normalized.append(new_contour)

    advance_width = round(svg_width * scale)
    return normalized, advance_width
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_svg_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/helpers.py tests/test_svg_parser.py
git commit -m "feat: add SVG path parser and contour normalizer"
```

---

### Task 6: Font Assembly — Bold Weight (`scripts/assemble.py`)

**Files:**
- Create: `scripts/assemble.py`
- Create: `tests/test_assemble.py`

Build the Bold (filled) font first since it's simpler — contours go directly into the font.

- [ ] **Step 1: Write the failing test**

Create `tests/test_assemble.py`:

```python
import os
import pytest


def test_create_bold_font(tmp_path):
    """Should create a valid TTF file for Bold weight."""
    from scripts.assemble import create_bold_font

    output_path = str(tmp_path / "Mikdash-Bold.ttf")
    create_bold_font("glyphs/svg", output_path)
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 100  # not an empty file

    # Verify it's a valid font
    from fontTools.ttLib import TTFont
    font = TTFont(output_path)
    assert "cmap" in font
    assert "glyf" in font
    cmap = font.getBestCmap()
    # Should have at least some Hebrew codepoints mapped
    hebrew_mapped = [cp for cp in cmap if 0x05D0 <= cp <= 0x05EA]
    assert len(hebrew_mapped) > 0, "No Hebrew characters mapped"
    font.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py::test_create_bold_font -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement create_bold_font in 04_assemble.py**

Create `scripts/assemble.py`:

```python
"""Step 4: Assemble SVG glyphs into TTF font files.

Creates two weights:
- Mikdash-Bold.ttf  — filled glyphs (direct from SVG contours)
- Mikdash-Regular.ttf — hollow glyphs (stroke outlines via pyclipper)
"""

import glob
import os

from fontTools import ttLib
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.t2Pen import T2Pen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.ttLib import TTFont

from scripts.helpers import (
    ASCENDER,
    COMBINING_CIRCLE,
    COMBINING_DIAMOND,
    DESCENDER,
    FONT_FAMILY,
    HEBREW_LETTERS,
    LINE_GAP,
    STANDALONE_CIRCLE,
    UNITS_PER_EM,
    normalize_contours,
    parse_svg_to_contours,
)


def load_svg_glyphs(svg_dir: str) -> dict[str, list[list[tuple]]]:
    """Load all SVG files and parse into contours.

    Returns dict mapping glyph name -> normalized contours.
    File names should match keys in HEBREW_LETTERS (e.g., "alef.svg").
    """
    glyphs = {}
    for svg_path in sorted(glob.glob(os.path.join(svg_dir, "*.svg"))):
        name = os.path.splitext(os.path.basename(svg_path))[0]
        with open(svg_path) as f:
            svg_content = f.read()
        contours = parse_svg_to_contours(svg_content)
        if contours:
            glyphs[name] = contours
    return glyphs


def build_font(
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
    family_name: str,
    style_name: str,
    output_path: str,
) -> None:
    """Build a TTF font from normalized glyph contours.

    glyph_contours: dict mapping glyph_name -> (contours, advance_width)
    """
    # Map glyph names to Unicode codepoints
    name_to_unicode = {}
    for letter_name, codepoint in HEBREW_LETTERS.items():
        name_to_unicode[letter_name] = codepoint

    # Special marks
    name_to_unicode["diamond_above"] = COMBINING_DIAMOND
    name_to_unicode["circle_above"] = COMBINING_CIRCLE
    name_to_unicode["circle_standalone"] = STANDALONE_CIRCLE

    # Build glyph order and cmap
    glyph_names = [".notdef", "space"]
    cmap_entries = {0x0020: "space"}  # space
    metrics = {".notdef": (500, 0), "space": (250, 0)}
    glyph_data = {}

    for glyph_name, (contours, advance_width) in glyph_contours.items():
        if glyph_name in name_to_unicode:
            unicode_val = name_to_unicode[glyph_name]
            cmap_entries[unicode_val] = glyph_name
        glyph_names.append(glyph_name)
        metrics[glyph_name] = (advance_width, 0)
        glyph_data[glyph_name] = contours

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)
    fb.setupGlyphOrder(glyph_names)
    fb.setupCharacterMap(cmap_entries)

    # Draw glyphs
    fb.setupGlyf(
        _build_glyf_dict(glyph_names, glyph_data, fb)
    )

    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)

    fb.setupNameTable({
        "familyName": family_name,
        "styleName": style_name,
    })

    fb.setupOs2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        sTypoLineGap=LINE_GAP,
        usWeightClass=700 if style_name == "Bold" else 400,
    )
    fb.setupPost()
    fb.setupHead(unitsPerEm=UNITS_PER_EM)

    fb.font.save(output_path)
    print(f"Saved {output_path}")


def _build_glyf_dict(
    glyph_names: list[str],
    glyph_data: dict[str, list[list[tuple]]],
    fb: FontBuilder,
) -> dict:
    """Build the glyf table dict for FontBuilder.setupGlyf().

    Returns dict mapping glyph_name -> {"numberOfContours": N, "coordinates": [...], ...}
    or a pen-drawing function.
    """
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    glyf_dict = {}
    for name in glyph_names:
        pen = TTGlyphPen(None)
        if name in glyph_data:
            contours = glyph_data[name]
            for contour in contours:
                if not contour:
                    continue
                started = False
                for x, y, on_curve in contour:
                    if not started:
                        pen.moveTo((x, y))
                        started = True
                    elif on_curve:
                        pen.lineTo((x, y))
                    else:
                        # Collect off-curve points for qcurve
                        pass
                pen.closePath()
            glyf_dict[name] = pen.glyph()
        else:
            # Empty glyph (.notdef, space)
            pen.moveTo((0, 0))
            pen.lineTo((500, 0))
            pen.lineTo((500, 700))
            pen.lineTo((0, 700))
            pen.closePath()
            if name == "space":
                glyf_dict[name] = pen.glyph()  # will be overridden to empty
            else:
                glyf_dict[name] = pen.glyph()

    return glyf_dict


def create_bold_font(svg_dir: str, output_path: str) -> None:
    """Create the Bold (filled) weight of Mikdash font."""
    raw_glyphs = load_svg_glyphs(svg_dir)

    # Normalize all glyphs
    glyph_contours = {}
    for name, contours in raw_glyphs.items():
        normalized, advance_width = normalize_contours(contours)
        if normalized:
            # Add some side bearing
            bearing = max(20, advance_width // 10)
            shifted = []
            for contour in normalized:
                shifted.append([(x + bearing, y, on) for x, y, on in contour])
            glyph_contours[name] = (shifted, advance_width + bearing * 2)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    build_font(glyph_contours, FONT_FAMILY, "Bold", output_path)


if __name__ == "__main__":
    create_bold_font("glyphs/svg", "output/Mikdash-Bold.ttf")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py::test_create_bold_font -v`
Expected: PASS (requires SVG files from Task 4)

- [ ] **Step 5: Commit**

```bash
git add scripts/assemble.py tests/test_assemble.py
git commit -m "feat: add font assembly for Bold weight"
```

---

### Task 7: Hollow Glyph Generation and Regular Weight

**Files:**
- Modify: `scripts/assemble.py`
- Modify: `tests/test_assemble.py`

Add the Regular (hollow) weight by offsetting filled contours inward with pyclipper.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assemble.py`:

```python
def test_create_hollow_contours():
    """Hollow contours should have more contours than filled (inner + outer)."""
    from scripts.assemble import make_hollow_contours

    # Simple square contour
    filled = [[(0, 0, True), (100, 0, True), (100, 100, True), (0, 100, True)]]
    hollow = make_hollow_contours(filled, stroke_width=10)
    # Should have 2 contours: outer and inner
    assert len(hollow) == 2


def test_create_regular_font(tmp_path):
    """Should create a valid TTF for Regular (hollow) weight."""
    from scripts.assemble import create_regular_font

    output_path = str(tmp_path / "Mikdash-Regular.ttf")
    create_regular_font("glyphs/svg", output_path)
    assert os.path.exists(output_path)

    from fontTools.ttLib import TTFont
    font = TTFont(output_path)
    assert "cmap" in font
    hebrew_mapped = [cp for cp in font.getBestCmap() if 0x05D0 <= cp <= 0x05EA]
    assert len(hebrew_mapped) > 0
    font.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py::test_create_hollow_contours -v`
Expected: FAIL — function not found

- [ ] **Step 3: Add hollow generation to 04_assemble.py**

Add to `scripts/assemble.py`:

```python
import pyclipper


def make_hollow_contours(
    contours: list[list[tuple]], stroke_width: int = 60
) -> list[list[tuple]]:
    """Convert filled contours to hollow (outline) contours using polygon offsetting.

    Takes the outer contour and creates an inward offset to produce the inner wall.
    Returns combined contours: outer (clockwise) + inner (counter-clockwise).
    """
    # Convert to pyclipper format: list of (x, y) tuples, no on_curve flag
    clipper_paths = []
    for contour in contours:
        path = [(int(x), int(y)) for x, y, _ in contour]
        if len(path) >= 3:
            clipper_paths.append(path)

    if not clipper_paths:
        return contours

    # Create inward offset
    pco = pyclipper.PyclipperOffset()
    for path in clipper_paths:
        pco.AddPath(path, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

    inner_paths = pco.Execute(-stroke_width)

    if not inner_paths:
        # Offset too large — glyph is thinner than stroke width, return original
        return contours

    # Combine: original outer contours + reversed inner contours
    result = []
    for contour in contours:
        result.append(contour)  # outer, keep original on_curve flags

    for path in inner_paths:
        # Inner contour: reverse winding, all points on-curve (polygon approximation)
        inner_contour = [(x, y, True) for x, y in reversed(path)]
        result.append(inner_contour)

    return result


def create_regular_font(svg_dir: str, output_path: str) -> None:
    """Create the Regular (hollow) weight of Mikdash font."""
    from scripts.helpers import HOLLOW_STROKE_RATIO

    raw_glyphs = load_svg_glyphs(svg_dir)
    stroke_width = int(UNITS_PER_EM * HOLLOW_STROKE_RATIO)

    glyph_contours = {}
    for name, contours in raw_glyphs.items():
        normalized, advance_width = normalize_contours(contours)
        if normalized:
            hollow = make_hollow_contours(normalized, stroke_width=stroke_width)
            bearing = max(20, advance_width // 10)
            shifted = []
            for contour in hollow:
                shifted.append([(x + bearing, y, on) for x, y, on in contour])
            glyph_contours[name] = (shifted, advance_width + bearing * 2)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    build_font(glyph_contours, FONT_FAMILY, "Regular", output_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/assemble.py tests/test_assemble.py
git commit -m "feat: add hollow glyph generation and Regular weight"
```

---

### Task 8: Combining Marks (Diamond and Circle) with GPOS

**Files:**
- Modify: `scripts/assemble.py`
- Modify: `tests/test_assemble.py`

Add the diamond (filled) and circle (hollow) as combining marks with mark-to-base positioning, plus the standalone circle glyph.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assemble.py`:

```python
def test_font_has_combining_marks(tmp_path):
    """Font should have combining diamond and circle marks mapped."""
    from scripts.assemble import create_bold_font
    from scripts.helpers import COMBINING_CIRCLE, COMBINING_DIAMOND, STANDALONE_CIRCLE

    output_path = str(tmp_path / "Mikdash-Bold.ttf")
    create_bold_font("glyphs/svg", output_path)

    from fontTools.ttLib import TTFont
    font = TTFont(output_path)
    cmap = font.getBestCmap()

    assert COMBINING_DIAMOND in cmap, "Missing combining diamond mark"
    assert COMBINING_CIRCLE in cmap, "Missing combining circle mark"
    assert STANDALONE_CIRCLE in cmap, "Missing standalone circle"
    font.close()


def test_font_has_gpos_mark_positioning(tmp_path):
    """Font should have GPOS table with mark-to-base positioning."""
    from scripts.assemble import create_bold_font

    output_path = str(tmp_path / "Mikdash-Bold.ttf")
    create_bold_font("glyphs/svg", output_path)

    from fontTools.ttLib import TTFont
    font = TTFont(output_path)
    assert "GPOS" in font, "Missing GPOS table"
    font.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py::test_font_has_combining_marks -v`
Expected: FAIL — marks not in cmap

- [ ] **Step 3: Add mark glyphs and GPOS to 04_assemble.py**

Add to `scripts/assemble.py`:

```python
def create_diamond_contours(size: int = 80) -> list[list[tuple]]:
    """Create a filled diamond shape as contours.

    Diamond is centered at origin, caller positions it.
    """
    half = size // 2
    contour = [
        (0, half, True),     # top
        (half, 0, True),     # right
        (0, -half, True),    # bottom
        (-half, 0, True),    # left
    ]
    return [contour]


def create_circle_contours(radius: int = 40, hollow: bool = True, segments: int = 24) -> list[list[tuple]]:
    """Create a circle as contours.

    If hollow, creates outer + inner ring. If filled, just outer.
    """
    import math

    def make_circle(r, reverse=False):
        points = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            if reverse:
                angle = 2 * math.pi * (segments - i) / segments
            x = round(r * math.cos(angle))
            y = round(r * math.sin(angle))
            points.append((x, y, True))
        return points

    contours = [make_circle(radius)]
    if hollow:
        inner_radius = max(radius - 12, radius // 2)
        contours.append(make_circle(inner_radius, reverse=True))
    return contours


def add_mark_glyphs(
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
) -> None:
    """Add diamond and circle mark glyphs to the glyph dict."""
    # Diamond combining mark — zero advance width (combining)
    diamond = create_diamond_contours(size=80)
    # Position above baseline at ascender area
    positioned = []
    for contour in diamond:
        positioned.append([(x + 250, y + 900, on) for x, y, on in contour])
    glyph_contours["diamond_above"] = (positioned, 0)

    # Circle combining mark — zero advance width (combining)
    circle = create_circle_contours(radius=40, hollow=True)
    positioned = []
    for contour in circle:
        positioned.append([(x + 250, y + 900, on) for x, y, on in contour])
    glyph_contours["circle_above"] = (positioned, 0)

    # Circle standalone — has advance width
    circle_standalone = create_circle_contours(radius=50, hollow=True)
    positioned = []
    for contour in circle_standalone:
        positioned.append([(x + 60, y + 400, on) for x, y, on in contour])
    glyph_contours["circle_standalone"] = (positioned, 120)


def build_gpos_mark_to_base(font: TTFont, glyph_contours: dict) -> None:
    """Add GPOS mark-to-base positioning for combining marks.

    Each Hebrew base glyph gets an anchor above center.
    Diamond and circle marks get a corresponding anchor.
    """
    from fontTools.otTables import (
        GPOS,
        Anchor,
        BaseArray,
        BaseRecord,
        MarkArray,
        MarkBasePos,
        MarkRecord,
    )
    from fontTools.ttLib.tables import otTables

    mark_names = []
    if "diamond_above" in glyph_contours:
        mark_names.append("diamond_above")
    if "circle_above" in glyph_contours:
        mark_names.append("circle_above")

    if not mark_names:
        return

    # Base glyphs: all Hebrew letters
    base_names = [name for name in glyph_contours if name in HEBREW_LETTERS]

    # Build feature file string for simplicity
    fea_lines = []
    fea_lines.append("feature mark {")

    for base_name in base_names:
        contours, adv_w = glyph_contours[base_name]
        # Anchor above center of glyph
        anchor_x = adv_w // 2
        anchor_y = ASCENDER + 50

        for mark_name in mark_names:
            fea_lines.append(
                f"  pos base {base_name} <anchor {anchor_x} {anchor_y}> mark @mark_above;"
            )
            break  # one anchor per base is enough

    fea_lines.append("} mark;")

    # For now, use a simpler approach: write GPOS directly via fontTools
    # We'll use feaLib in the actual implementation
    _build_gpos_directly(font, base_names, mark_names, glyph_contours)


def _build_gpos_directly(
    font: TTFont,
    base_names: list[str],
    mark_names: list[str],
    glyph_contours: dict,
) -> None:
    """Build GPOS mark-to-base lookup directly using fontTools otTables."""
    from fontTools.otTables import (
        Anchor,
        BaseArray,
        BaseRecord,
        MarkArray,
        MarkBasePos,
        MarkRecord,
    )

    # Create mark-to-base lookup
    lookup = MarkBasePos()
    lookup.Format = 1

    # Mark class: all marks are class 0 (positioned above)
    mark_array = MarkArray()
    mark_array.MarkCount = len(mark_names)
    mark_array.MarkRecord = []

    for mark_name in mark_names:
        record = MarkRecord()
        record.Class = 0
        anchor = Anchor()
        anchor.Format = 1
        anchor.XCoordinate = 0
        anchor.YCoordinate = 0
        record.MarkAnchor = anchor
        mark_array.MarkRecord.append(record)

    lookup.MarkArray = mark_array
    lookup.MarkCoverage = _make_coverage(mark_names)
    lookup.ClassCount = 1

    # Base array
    base_array = BaseArray()
    base_array.BaseCount = len(base_names)
    base_array.BaseRecord = []

    for base_name in base_names:
        record = BaseRecord()
        contours, adv_w = glyph_contours[base_name]
        anchor = Anchor()
        anchor.Format = 1
        anchor.XCoordinate = adv_w // 2
        anchor.YCoordinate = ASCENDER + 50
        record.BaseAnchor = [anchor]
        base_array.BaseRecord.append(record)

    lookup.BaseArray = base_array
    lookup.BaseCoverage = _make_coverage(base_names)

    # Wrap in GPOS table
    from fontTools.otTables import GPOS as GPOSTable
    from fontTools.otTables import FeatureList, FeatureRecord, Feature
    from fontTools.otTables import LookupList, Lookup
    from fontTools.otTables import ScriptList, ScriptRecord, Script
    from fontTools.otTables import LangSysRecord, LangSys, DefaultLangSys

    gpos_lookup = Lookup()
    gpos_lookup.LookupType = 4  # MarkBasePos
    gpos_lookup.LookupFlag = 0
    gpos_lookup.SubTableCount = 1
    gpos_lookup.SubTable = [lookup]

    lookup_list = LookupList()
    lookup_list.LookupCount = 1
    lookup_list.Lookup = [gpos_lookup]

    # Feature
    feature = Feature()
    feature.FeatureParams = None
    feature.LookupCount = 1
    feature.LookupListIndex = [0]

    feat_record = FeatureRecord()
    feat_record.FeatureTag = "mark"
    feat_record.Feature = feature

    feature_list = FeatureList()
    feature_list.FeatureCount = 1
    feature_list.FeatureRecord = [feat_record]

    # Script
    default_lang = DefaultLangSys()
    default_lang.ReqFeatureIndex = 0xFFFF
    default_lang.FeatureCount = 1
    default_lang.FeatureIndex = [0]

    script = Script()
    script.DefaultLangSys = default_lang
    script.LangSysCount = 0
    script.LangSysRecord = []

    script_record = ScriptRecord()
    script_record.ScriptTag = "hebr"
    script_record.Script = script

    # Also add DFLT script
    dflt_script = Script()
    dflt_script.DefaultLangSys = default_lang
    dflt_script.LangSysCount = 0
    dflt_script.LangSysRecord = []

    dflt_record = ScriptRecord()
    dflt_record.ScriptTag = "DFLT"
    dflt_record.Script = dflt_script

    script_list = ScriptList()
    script_list.ScriptCount = 2
    script_list.ScriptRecord = [dflt_record, script_record]

    gpos_table = GPOSTable()
    gpos_table.Version = 0x00010000
    gpos_table.ScriptList = script_list
    gpos_table.FeatureList = feature_list
    gpos_table.LookupList = lookup_list

    font["GPOS"] = ttLib.newTable("GPOS")
    font["GPOS"].table = gpos_table


def _make_coverage(glyph_names: list[str]):
    """Create a Coverage table for the given glyph names."""
    from fontTools.otTables import Coverage

    coverage = Coverage()
    coverage.glyphs = glyph_names
    return coverage
```

Then update `create_bold_font` and `create_regular_font` to call `add_mark_glyphs` before building and `build_gpos_mark_to_base` after building:

```python
# In create_bold_font, before build_font call:
add_mark_glyphs(glyph_contours)

# After build_font, reopen and add GPOS:
font = TTFont(output_path)
build_gpos_mark_to_base(font, glyph_contours)
font.save(output_path)
```

Apply the same pattern to `create_regular_font`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/assemble.py tests/test_assemble.py
git commit -m "feat: add combining marks and GPOS mark-to-base positioning"
```

---

### Task 9: Merge EB Garamond Latin/Numbers

**Files:**
- Modify: `scripts/assemble.py`
- Modify: `tests/test_assemble.py`

Borrow Latin characters, numbers, and punctuation from EB Garamond.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assemble.py`:

```python
def test_font_has_latin_and_numbers(tmp_path):
    """Font should include Latin letters and numbers from EB Garamond."""
    from scripts.assemble import create_bold_font

    output_path = str(tmp_path / "Mikdash-Bold.ttf")
    create_bold_font("glyphs/svg", output_path, donor_font="donor/EBGaramond-Regular.ttf")

    from fontTools.ttLib import TTFont
    font = TTFont(output_path)
    cmap = font.getBestCmap()

    # Check for basic Latin
    assert ord("A") in cmap, "Missing Latin A"
    assert ord("a") in cmap, "Missing Latin a"
    assert ord("0") in cmap, "Missing digit 0"
    assert ord(".") in cmap, "Missing period"
    font.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py::test_font_has_latin_and_numbers -v`
Expected: FAIL

- [ ] **Step 3: Add donor font merging to 04_assemble.py**

Add to `scripts/assemble.py`:

```python
def merge_donor_glyphs(target_path: str, donor_path: str) -> None:
    """Merge Latin, numbers, and punctuation from donor font into target.

    Copies glyphs and their cmap entries without overwriting existing Hebrew glyphs.
    """
    donor = TTFont(donor_path)
    target = TTFont(target_path)

    donor_cmap = donor.getBestCmap()
    target_cmap_table = target["cmap"]

    # Codepoint ranges to borrow
    borrow_ranges = [
        (0x0020, 0x007E),   # Basic Latin (space through tilde)
        (0x00A0, 0x00FF),   # Latin-1 Supplement
        (0x2000, 0x206F),   # General Punctuation
        (0x2013, 0x2014),   # En-dash, em-dash
        (0x2018, 0x201D),   # Smart quotes
    ]

    # Get glyphs to copy
    glyphs_to_copy = set()
    new_cmap_entries = {}
    existing_cmap = target.getBestCmap()

    for start, end in borrow_ranges:
        for cp in range(start, end + 1):
            if cp in existing_cmap:
                continue  # don't overwrite our glyphs
            if cp in donor_cmap:
                glyph_name = donor_cmap[cp]
                glyphs_to_copy.add(glyph_name)
                new_cmap_entries[cp] = glyph_name

    # Copy glyph data
    donor_glyf = donor["glyf"]
    target_glyf = target["glyf"]
    donor_hmtx = donor["hmtx"]
    target_hmtx = target["hmtx"]

    # Scale factor if UPMs differ
    donor_upm = donor["head"].unitsPerEm
    target_upm = target["head"].unitsPerEm
    scale = target_upm / donor_upm if donor_upm != target_upm else 1.0

    glyph_order = list(target.getGlyphOrder())

    for glyph_name in glyphs_to_copy:
        if glyph_name in target_glyf:
            continue  # already exists

        if glyph_name not in donor_glyf:
            continue

        # Copy glyph
        glyph = donor_glyf[glyph_name]
        if scale != 1.0 and hasattr(glyph, "coordinates") and glyph.coordinates:
            # Scale coordinates
            from fontTools.misc.arrayTools import Vector
            coords = []
            for x, y in glyph.coordinates:
                coords.append((round(x * scale), round(y * scale)))
            glyph.coordinates = coords

        target_glyf[glyph_name] = glyph
        glyph_order.append(glyph_name)

        # Copy metrics
        if glyph_name in donor_hmtx.metrics:
            width, lsb = donor_hmtx.metrics[glyph_name]
            target_hmtx.metrics[glyph_name] = (round(width * scale), round(lsb * scale))

    target.setGlyphOrder(glyph_order)

    # Update cmap
    for subtable in target_cmap_table.tables:
        if hasattr(subtable, "cmap"):
            subtable.cmap.update(new_cmap_entries)

    # Update maxp
    target["maxp"].numGlyphs = len(glyph_order)

    target.save(target_path)
    donor.close()
    target.close()
    print(f"Merged {len(glyphs_to_copy)} glyphs from {donor_path}")
```

Update `create_bold_font` and `create_regular_font` signatures to accept an optional `donor_font` parameter and call `merge_donor_glyphs` at the end:

```python
def create_bold_font(svg_dir: str, output_path: str, donor_font: str = None) -> None:
    # ... existing code ...
    build_font(glyph_contours, FONT_FAMILY, "Bold", output_path)
    # ... GPOS code ...
    if donor_font and os.path.exists(donor_font):
        merge_donor_glyphs(output_path, donor_font)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_assemble.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/assemble.py tests/test_assemble.py
git commit -m "feat: merge Latin/numbers from EB Garamond donor font"
```

---

### Task 10: End-to-End Pipeline and Final Output

**Files:**
- Create: `scripts/build.py` (orchestrator)
- Create: `tests/test_e2e.py`

A single script that runs the full pipeline from `font.jpg` to TTF output.

- [ ] **Step 1: Write the failing test**

Create `tests/test_e2e.py`:

```python
import os
import pytest


def test_full_pipeline_produces_fonts(tmp_path):
    """Full pipeline should produce both Regular and Bold TTF files."""
    from scripts.build import build_all

    build_all(
        source_image="font.jpg",
        output_dir=str(tmp_path),
        donor_font="donor/EBGaramond-Regular.ttf",
    )

    regular = tmp_path / "Mikdash-Regular.ttf"
    bold = tmp_path / "Mikdash-Bold.ttf"
    assert regular.exists(), "Missing Regular weight"
    assert bold.exists(), "Missing Bold weight"

    from fontTools.ttLib import TTFont

    for path in [regular, bold]:
        font = TTFont(str(path))
        cmap = font.getBestCmap()
        hebrew = [cp for cp in cmap if 0x05D0 <= cp <= 0x05EA]
        assert len(hebrew) > 0, f"No Hebrew in {path.name}"
        font.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_e2e.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement build.py**

Create `scripts/build.py`:

```python
"""Mikdash Font — Full build pipeline.

Usage: python scripts/build.py [--source font.jpg] [--output output/] [--donor donor/EBGaramond-Regular.ttf]
"""

import argparse
import os
import sys

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.preprocess import preprocess
from scripts.segment import segment
from scripts.vectorize import vectorize_all
from scripts.assemble import create_bold_font, create_regular_font


def build_all(
    source_image: str = "font.jpg",
    output_dir: str = "output",
    donor_font: str = None,
) -> None:
    """Run the full pipeline: preprocess → segment → vectorize → assemble."""
    print("=" * 60)
    print("Mikdash Font Build Pipeline")
    print("=" * 60)

    # Step 1: Preprocess
    print("\n[1/4] Preprocessing image...")
    preprocess(source_image)

    # Step 2: Segment
    print("\n[2/4] Segmenting glyphs...")
    segment("glyphs/preprocessed.png")
    print(
        "\n*** MANUAL STEP REQUIRED ***"
        "\nReview glyphs/bitmaps/ and rename files to Hebrew letter names."
        "\nE.g.: char_01_003.png → alef.png, char_02_005.png → bet.png"
        "\nThen re-run this script to continue from vectorization."
        "\n"
    )

    # Check if bitmaps have been renamed
    import glob
    from scripts.helpers import HEBREW_LETTERS

    named_bitmaps = [
        f
        for f in glob.glob("glyphs/bitmaps/*.png")
        if os.path.splitext(os.path.basename(f))[0] in HEBREW_LETTERS
    ]

    if not named_bitmaps:
        print("No named glyph bitmaps found. Please rename and re-run.")
        return

    print(f"Found {len(named_bitmaps)} named glyph bitmaps.")

    # Step 3: Vectorize
    print("\n[3/4] Vectorizing glyphs...")
    vectorize_all("glyphs/bitmaps", "glyphs/svg")

    # Step 4: Assemble
    print("\n[4/4] Assembling fonts...")
    os.makedirs(output_dir, exist_ok=True)

    bold_path = os.path.join(output_dir, "Mikdash-Bold.ttf")
    regular_path = os.path.join(output_dir, "Mikdash-Regular.ttf")

    create_bold_font("glyphs/svg", bold_path, donor_font=donor_font)
    create_regular_font("glyphs/svg", regular_path, donor_font=donor_font)

    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print(f"  Bold:    {bold_path}")
    print(f"  Regular: {regular_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Mikdash font")
    parser.add_argument("--source", default="font.jpg", help="Source image path")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--donor", default="donor/EBGaramond-Regular.ttf", help="Donor font path")
    args = parser.parse_args()

    build_all(source_image=args.source, output_dir=args.output, donor_font=args.donor)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/test_e2e.py -v`
Expected: PASS (requires all previous pipeline outputs)

- [ ] **Step 5: Commit**

```bash
git add scripts/build.py tests/test_e2e.py
git commit -m "feat: add end-to-end build pipeline orchestrator"
```

---

### Task 11: Final Verification and Cleanup

- [ ] **Step 1: Run the full test suite**

Run: `cd /Users/i022021/dev/fontMikdash && python -m pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 2: Build the fonts from scratch**

Run:
```bash
cd /Users/i022021/dev/fontMikdash
python scripts/build.py
```

- [ ] **Step 3: Validate the output fonts**

Run:
```bash
cd /Users/i022021/dev/fontMikdash
python -c "
from fontTools.ttLib import TTFont

for name in ['output/Mikdash-Bold.ttf', 'output/Mikdash-Regular.ttf']:
    font = TTFont(name)
    cmap = font.getBestCmap()
    hebrew = {hex(cp): cmap[cp] for cp in cmap if 0x05D0 <= cp <= 0x05EA}
    latin = {chr(cp): cmap[cp] for cp in cmap if 0x0041 <= cp <= 0x005A}
    print(f'{name}:')
    print(f'  Hebrew glyphs: {len(hebrew)}')
    print(f'  Latin glyphs: {len(latin)}')
    print(f'  Total glyphs: {len(cmap)}')
    print(f'  Has GPOS: {\"GPOS\" in font}')
    font.close()
"
```
Expected: both fonts have Hebrew glyphs, Latin glyphs, and GPOS table.

- [ ] **Step 4: Install and test visually**

Open `output/Mikdash-Bold.ttf` and `output/Mikdash-Regular.ttf` in Font Book (macOS) or a text editor that supports custom fonts. Type Hebrew text and verify:
- Characters render correctly
- Bold is filled, Regular is hollow
- Combining marks (diamond, circle) position above letters
- Standalone circle renders as its own character
- Latin and numbers render from EB Garamond

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete Mikdash font pipeline - Bold and Regular weights"
```
