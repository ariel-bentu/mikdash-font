"""Font assembly — build TrueType fonts from SVG glyph contours.

This module provides the Bold (filled) weight assembly. Contours parsed from
SVGs are normalized, converted from cubic to quadratic beziers, and packed
into a .ttf via fontTools' FontBuilder.
"""

import os
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

from scripts.helpers import (
    ASCENDER,
    DESCENDER,
    FONT_FAMILY,
    HEBREW_LETTERS,
    LINE_GAP,
    UNITS_PER_EM,
    normalize_contours,
    parse_svg_to_contours,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_svg_glyphs(svg_dir: str) -> dict[str, list[list[tuple]]]:
    """Load all SVG files from *svg_dir* and parse each into contours.

    Returns a dict mapping the file stem (e.g. ``"alef"`` or
    ``"char_00_001"``) to a list of contours, where each contour is a list
    of ``(x, y, on_curve)`` tuples.
    """
    svg_path = Path(svg_dir)
    glyphs: dict[str, list[list[tuple]]] = {}

    for svg_file in sorted(svg_path.glob("*.svg")):
        svg_content = svg_file.read_text(encoding="utf-8")
        contours = parse_svg_to_contours(svg_content)
        if contours:
            glyphs[svg_file.stem] = contours

    return glyphs


def build_font(
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
    family_name: str,
    style_name: str,
    output_path: str,
) -> None:
    """Build a TrueType font from normalised contour data.

    Parameters
    ----------
    glyph_contours : dict
        Maps glyph name -> (contours, advance_width).  Contours are lists
        of ``(x, y, on_curve)`` tuples. advance_width is an integer in
        font units.
    family_name : str
        The font family name (e.g. ``"Mikdash"``).
    style_name : str
        The style/weight name (e.g. ``"Bold"``).
    output_path : str
        File path for the generated ``.ttf``.
    """
    glyph_names = [".notdef"] + sorted(glyph_contours.keys())

    # Build cmap: only map glyphs whose names appear in HEBREW_LETTERS
    cmap = {}
    for name in glyph_names:
        if name in HEBREW_LETTERS:
            cmap[HEBREW_LETTERS[name]] = name

    # Prepare advance widths — .notdef gets a default width
    default_width = UNITS_PER_EM // 2
    metrics = {".notdef": (default_width, 0)}
    for name, (contours, adv_w) in glyph_contours.items():
        metrics[name] = (max(adv_w, 1), 0)  # (advance width, LSB placeholder)

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)
    fb.setupGlyphOrder(glyph_names)
    fb.setupCharacterMap(cmap)

    # --- build glyf table ------------------------------------------------
    glyph_table = _build_glyf_dict(glyph_names, glyph_contours, fb)
    fb.setupGlyf(glyph_table)

    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)

    fb.setupNameTable({
        "familyName": family_name,
        "styleName": style_name,
    })

    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        sTypoLineGap=LINE_GAP,
    )
    fb.setupPost()
    fb.setupHead(unitsPerEm=UNITS_PER_EM)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fb.font.save(output_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_glyf_dict(
    glyph_names: list[str],
    glyph_data: dict[str, tuple[list[list[tuple]], int]],
    fb: FontBuilder,
) -> dict:
    """Draw contours into TrueType glyphs, converting cubics to quadratics.

    Returns a dict suitable for ``FontBuilder.setupGlyf()``.
    """
    glyph_table: dict = {}

    for name in glyph_names:
        if name == ".notdef":
            # Empty glyph for .notdef
            pen = TTGlyphPen(None)
            pen.moveTo((0, 0))
            pen.lineTo((0, ASCENDER))
            pen.lineTo((UNITS_PER_EM // 2, ASCENDER))
            pen.lineTo((UNITS_PER_EM // 2, 0))
            pen.closePath()
            glyph_table[name] = pen.glyph()
            continue

        contours, _adv_w = glyph_data[name]
        glyph_table[name] = _draw_contours_to_glyph(contours)

    return glyph_table


def _draw_contours_to_glyph(contours: list[list[tuple]]):
    """Draw contours (with cubic beziers) into a TrueType glyph.

    Uses ``Cu2QuPen`` to automatically convert cubic curves to quadratic.
    """
    tt_pen = TTGlyphPen(None)
    cu2qu_pen = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=False)

    for contour in contours:
        if not contour:
            continue

        segments = _contour_to_segments(contour)
        if not segments:
            continue

        # First segment is the moveTo (single point)
        cu2qu_pen.moveTo(segments[0][0])

        for seg in segments[1:]:
            if len(seg) == 1:
                cu2qu_pen.lineTo(seg[0])
            elif len(seg) == 3:
                # cubic: two control points + on-curve endpoint
                cu2qu_pen.curveTo(*seg)
            elif len(seg) == 2:
                # quadratic: one control point + on-curve endpoint
                cu2qu_pen.qCurveTo(*seg)

        cu2qu_pen.closePath()

    return tt_pen.glyph()


def _contour_to_segments(
    contour: list[tuple],
) -> list[list[tuple[float, float]]]:
    """Convert ``(x, y, on_curve)`` point list to drawable segments.

    Returns a list of segments where each segment is a list of ``(x, y)``
    tuples:

    * ``[(x, y)]``                       — moveTo / lineTo
    * ``[(cx1, cy1), (cx2, cy2), (x, y)]`` — cubic curveTo
    * ``[(cx, cy), (x, y)]``             — quadratic qCurveTo
    """
    segments: list[list[tuple[float, float]]] = []
    current_segment: list[tuple[float, float]] = []

    for i, (x, y, on_curve) in enumerate(contour):
        if i == 0:
            # moveTo point
            segments.append([(x, y)])
            continue

        if on_curve:
            current_segment.append((x, y))
            segments.append(current_segment)
            current_segment = []
        else:
            current_segment.append((x, y))

    # If there are trailing off-curve points (shouldn't normally happen),
    # discard them to avoid malformed segments.
    return segments


def create_bold_font(svg_dir: str, output_path: str) -> None:
    """Orchestrator: load SVGs, normalise, and build a Bold TTF.

    Parameters
    ----------
    svg_dir : str
        Directory containing SVG glyph files.
    output_path : str
        Where to write the resulting ``.ttf``.
    """
    raw_glyphs = load_svg_glyphs(svg_dir)

    # Normalise contours and compute advance widths
    glyph_contours: dict[str, tuple[list[list[tuple]], int]] = {}
    for name, contours in raw_glyphs.items():
        normalised, adv_w = normalize_contours(contours)
        if normalised:
            # Add side bearings (about 5 % of advance width on each side)
            bearing = max(int(adv_w * 0.05), 10)
            shifted = []
            for contour in normalised:
                shifted.append(
                    [(x + bearing, y, on) for x, y, on in contour]
                )
            total_width = adv_w + 2 * bearing
            glyph_contours[name] = (shifted, total_width)

    build_font(glyph_contours, FONT_FAMILY, "Bold", output_path)
