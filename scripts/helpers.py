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

# ---------------------------------------------------------------------------
# SVG path parsing utilities
# ---------------------------------------------------------------------------

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
