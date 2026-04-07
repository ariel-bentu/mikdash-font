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

# Special marks — PUA codepoints
COMBINING_DIAMOND = 0xE001  # standalone diamond mark
COMBINING_CIRCLE = 0xE002   # standalone circle mark
STANDALONE_CIRCLE = 0x25CB  # WHITE CIRCLE — standalone glyph

# Pre-composed letter+mark PUA codepoints
# Each Hebrew letter + diamond/circle gets its own codepoint so the browser
# renders a single glyph with the mark perfectly centered — no GSUB needed.
_LETTER_ORDER = [
    "alef", "bet", "gimel", "dalet", "he", "vav", "zayin", "chet", "tet",
    "yod", "kaf", "final_kaf", "lamed", "mem", "final_mem", "nun",
    "final_nun", "samekh", "ayin", "pe", "final_pe", "tsade", "final_tsade",
    "qof", "resh", "shin", "tav",
]

COMPOSED_DIAMOND = {}  # letter_name -> PUA codepoint
COMPOSED_CIRCLE = {}   # letter_name -> PUA codepoint
for i, name in enumerate(_LETTER_ORDER):
    COMPOSED_DIAMOND[name] = 0xE100 + i        # U+E100..E11A
    COMPOSED_CIRCLE[name] = 0xE100 + 27 + i    # U+E11B..E135

# Font metrics (will be calibrated from image measurements)
UNITS_PER_EM = 1000
ASCENDER = 800
DESCENDER = -200
LINE_GAP = 0

# Stroke width for hollow (Regular) glyphs, as fraction of UPM
HOLLOW_STROKE_RATIO = 0.035  # 3.5% of em — calibrated from image

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

    Potrace wraps paths in a ``<g transform="translate(tx,ty) scale(sx,sy)">``.
    We apply that transform so returned coordinates are in SVG visual space
    (y-down), which ``normalize_contours`` expects.

    Returns list of contours. Coordinates are in SVG space (y-down).
    """
    root = ET.fromstring(svg_content)
    # Handle SVG namespace
    ns = {"svg": "http://www.w3.org/2000/svg"}

    # Look for potrace's <g transform="..."> wrapper
    tx, ty, sx, sy = 0.0, 0.0, 1.0, 1.0
    groups = root.findall(".//svg:g", ns)
    if not groups:
        groups = root.findall(".//{http://www.w3.org/2000/svg}g")
    if not groups:
        groups = root.findall(".//g")
    for g in groups:
        transform = g.get("transform", "")
        # Parse translate(tx,ty) scale(sx,sy)
        t_match = re.search(r"translate\(\s*([-\d.]+)\s*[,\s]\s*([-\d.]+)\s*\)", transform)
        s_match = re.search(r"scale\(\s*([-\d.]+)\s*[,\s]\s*([-\d.]+)\s*\)", transform)
        if t_match:
            tx, ty = float(t_match.group(1)), float(t_match.group(2))
        if s_match:
            sx, sy = float(s_match.group(1)), float(s_match.group(2))

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

    # Apply potrace transform: point = (x * sx + tx, y * sy + ty)
    if sx != 1.0 or sy != 1.0 or tx != 0.0 or ty != 0.0:
        transformed = []
        for contour in all_contours:
            new_contour = []
            for x, y, on_curve in contour:
                new_contour.append((x * sx + tx, y * sy + ty, on_curve))
            transformed.append(new_contour)
        all_contours = transformed

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
    contours: list[list[tuple]],
    target_height: int = 800,
    units_per_em: int = 1000,
    global_scale: float = None,
    global_top: float = None,
    baseline_y: float = None,
) -> tuple[list[list[tuple]], int]:
    """Normalize contours to fit within font em-square.

    When *global_scale*, *global_top*, and *baseline_y* are provided, all
    glyphs are scaled uniformly and aligned to a common top-line / baseline.
    This preserves the relative sizes of letters (e.g. yod stays small).

    Without those parameters, each glyph is scaled independently to fill
    *target_height* (legacy behaviour).

    Returns (normalized_contours, advance_width).
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

    if global_scale is not None and global_top is not None and baseline_y is not None:
        scale = global_scale
        # In SVG y-down space:
        #   global_top = top of tallest normal letters
        #   baseline_y = bottom of normal letters (the baseline)
        # In font space (y-up):
        #   baseline = 0, ascender = target_height
        # A point at SVG y maps to font y:
        #   font_y = target_height - (y - global_top) * scale
        # This puts global_top -> target_height (ascender) and
        # baseline_y -> target_height - (baseline_y - global_top)*scale = 0
        ref_top = global_top
    else:
        scale = target_height / svg_height
        ref_top = min_y

    normalized = []
    for contour in contours:
        new_contour = []
        for x, y, on_curve in contour:
            nx = (x - min_x) * scale
            ny = target_height - (y - ref_top) * scale  # flip Y, align to top
            new_contour.append((round(nx), round(ny), on_curve))
        normalized.append(new_contour)

    advance_width = round(svg_width * scale)
    return normalized, advance_width


def compute_global_scale(
    all_glyphs: dict[str, list[list[tuple]]],
    target_height: int = 800,
) -> tuple[float, float, float]:
    """Compute a uniform scale factor from all glyph contours.

    Uses only "normal" height glyphs (not ascenders/descenders) to derive
    the scale, so that letters like lamed naturally extend above the
    ascender line and qof/final forms extend below the baseline.

    Returns (scale, global_top, baseline_y).
    """
    glyph_info = {}
    for name, contours in all_glyphs.items():
        all_points = [p for c in contours for p in c]
        if not all_points:
            continue
        ys = [p[1] for p in all_points]
        glyph_info[name] = (min(ys), max(ys), max(ys) - min(ys))

    if not glyph_info:
        return 1.0, 0.0, 0.0

    # Find median height to identify "normal" glyphs
    all_heights = sorted(info[2] for info in glyph_info.values())
    median_h = all_heights[len(all_heights) // 2]

    # "Normal" glyphs: height within 20% of median (excludes ascenders,
    # descenders, and tiny glyphs like yod)
    normal_glyphs = {
        name: info for name, info in glyph_info.items()
        if abs(info[2] - median_h) / median_h < 0.20
    }

    if not normal_glyphs:
        normal_glyphs = glyph_info  # fallback

    # Body top and bottom from normal glyphs only
    normal_tops = [info[0] for info in normal_glyphs.values()]
    normal_bots = [info[1] for info in normal_glyphs.values()]

    sorted_tops = sorted(normal_tops)
    sorted_bots = sorted(normal_bots)
    global_top = sorted_tops[len(sorted_tops) // 2]
    global_bot = sorted_bots[len(sorted_bots) // 2]

    body_height = global_bot - global_top
    if body_height <= 0:
        body_height = median_h

    scale = target_height / body_height
    baseline_y = global_bot

    return scale, global_top, baseline_y
