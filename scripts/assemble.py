"""Font assembly — build TrueType fonts from SVG glyph contours.

This module provides the Bold (filled) weight assembly. Contours parsed from
SVGs are normalized, converted from cubic to quadratic beziers, and packed
into a .ttf via fontTools' FontBuilder.
"""

import os
from pathlib import Path

import pyclipper
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

from scripts.helpers import (
    ASCENDER,
    COMBINING_CIRCLE,
    COMBINING_DIAMOND,
    DESCENDER,
    FONT_FAMILY,
    HEBREW_LETTERS,
    HOLLOW_STROKE_RATIO,
    LINE_GAP,
    STANDALONE_CIRCLE,
    UNITS_PER_EM,
    normalize_contours,
    parse_svg_to_contours,
)


# ---------------------------------------------------------------------------
# Mark codepoint mapping
# ---------------------------------------------------------------------------

MARK_CODEPOINTS = {
    "diamond_above": COMBINING_DIAMOND,
    "circle_above": COMBINING_CIRCLE,
    "circle_standalone": STANDALONE_CIRCLE,
}


# ---------------------------------------------------------------------------
# Programmatic mark glyph creation
# ---------------------------------------------------------------------------


def create_diamond_contours(size: int = 80) -> list[list[tuple]]:
    """Create a filled diamond shape as contours (4 points: top, right, bottom, left).

    The diamond is centered at the origin; callers shift it to desired position.
    """
    half = size // 2
    contour = [
        (0, half, True),       # top
        (half, 0, True),       # right
        (0, -half, True),      # bottom
        (-half, 0, True),      # left
    ]
    return [contour]


def create_circle_contours(
    radius: int = 40, hollow: bool = True, segments: int = 24,
) -> list[list[tuple]]:
    """Create a circle as a polygon approximation.

    If *hollow* is True (default for the circle mark), an inner ring with
    reversed winding is added to punch a hole.
    """
    import math

    outer = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = round(radius * math.cos(angle))
        y = round(radius * math.sin(angle))
        outer.append((x, y, True))

    contours = [outer]

    if hollow:
        inner_radius = max(radius - 12, radius * 2 // 3)
        inner = []
        for i in range(segments):
            # Reversed winding (clockwise) to create a hole
            angle = 2 * math.pi * (segments - 1 - i) / segments
            x = round(inner_radius * math.cos(angle))
            y = round(inner_radius * math.sin(angle))
            inner.append((x, y, True))
        contours.append(inner)

    return contours


def add_mark_glyphs(
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
) -> None:
    """Add diamond_above, circle_above, and circle_standalone to *glyph_contours*.

    Combining marks have advance_width=0 (zero-width) and are positioned
    above the baseline. circle_standalone has a non-zero advance width.
    Mutates *glyph_contours* in place.
    """
    center_x = 250
    mark_y = ASCENDER + 100  # above ascender line

    # --- diamond_above (combining, zero-width) ---
    diamond = create_diamond_contours(size=80)
    diamond_shifted = []
    for contour in diamond:
        diamond_shifted.append(
            [(x + center_x, y + mark_y, on) for x, y, on in contour]
        )
    glyph_contours["diamond_above"] = (diamond_shifted, 0)

    # --- circle_above (combining, zero-width) ---
    circle = create_circle_contours(radius=40, hollow=True, segments=24)
    circle_shifted = []
    for contour in circle:
        circle_shifted.append(
            [(x + center_x, y + mark_y, on) for x, y, on in contour]
        )
    glyph_contours["circle_above"] = (circle_shifted, 0)

    # --- circle_standalone (visible glyph, non-zero width) ---
    standalone = create_circle_contours(radius=40, hollow=True, segments=24)
    standalone_y = 400  # centered vertically around midline
    standalone_x = 60   # centered in a ~120-wide advance
    standalone_shifted = []
    for contour in standalone:
        standalone_shifted.append(
            [(x + standalone_x, y + standalone_y, on) for x, y, on in contour]
        )
    glyph_contours["circle_standalone"] = (standalone_shifted, 120)


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

    # Build cmap: map Hebrew letters and mark glyphs
    cmap = {}
    for name in glyph_names:
        if name in HEBREW_LETTERS:
            cmap[HEBREW_LETTERS[name]] = name
        elif name in MARK_CODEPOINTS:
            cmap[MARK_CODEPOINTS[name]] = name

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

    full_name = f"{family_name} {style_name}"
    ps_name = f"{family_name}-{style_name}"
    fb.setupNameTable({
        "copyright": "Copyright 2026, Mikdash Font Project",
        "familyName": family_name,
        "styleName": style_name,
        "uniqueFontIdentifier": f"1.000;NONE;{ps_name}",
        "fullName": full_name,
        "version": "Version 1.000",
        "psName": ps_name,
    })

    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        sTypoLineGap=LINE_GAP,
    )
    fb.setupPost()
    import calendar, time
    now = calendar.timegm(time.gmtime())
    fb.setupHead(unitsPerEm=UNITS_PER_EM, created=now, modified=now)

    # gasp table — needed for Font Book validation
    from fontTools.ttLib import newTable
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000A}  # symmetric smoothing + gridfit at all sizes
    fb.font["gasp"] = gasp

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


def add_gpos_marks(
    font_path: str,
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
) -> None:
    """Add GPOS mark-to-base positioning to an existing font.

    Builds an OpenType feature definition string and compiles it into the
    font using ``fontTools.feaLib``.
    """
    mark_names = [
        name for name in ("diamond_above", "circle_above")
        if name in glyph_contours
    ]
    if not mark_names:
        return

    base_names = sorted(
        name for name in glyph_contours
        if name not in ("diamond_above", "circle_above", "circle_standalone")
    )
    if not base_names:
        return

    font = TTFont(font_path)

    # Anchor positions
    # Base anchor: above the centre of each base glyph
    # Mark anchor: at the "attachment" point of each mark
    base_anchor_y = ASCENDER + 100
    mark_anchor_y = ASCENDER + 100

    # Build OpenType feature code
    lines = []

    # Define @bases glyph class
    lines.append("@bases = [%s];" % " ".join(base_names))

    # Define mark classes — each mark gets its own class for the "top" anchor
    for mark_name in mark_names:
        # The mark anchor is where the mark's own reference point is:
        # We place it at the same (center_x, mark_y) used when drawing the glyph
        lines.append(
            "markClass %s <anchor 250 %d> @mark_top_%s;"
            % (mark_name, mark_anchor_y, mark_name)
        )

    # Build the mark-to-base feature
    lines.append("feature mark {")
    for mark_name in mark_names:
        lines.append("  lookup mark2base_%s {" % mark_name)
        for base_name in base_names:
            # Compute base anchor X as half the advance width
            _contours, adv_w = glyph_contours[base_name]
            anchor_x = adv_w // 2
            lines.append(
                "    pos base %s <anchor %d %d> mark @mark_top_%s;"
                % (base_name, anchor_x, base_anchor_y, mark_name)
            )
        lines.append("  } mark2base_%s;" % mark_name)
    lines.append("} mark;")

    fea_code = "\n".join(lines)

    addOpenTypeFeaturesFromString(font, fea_code)
    font.save(font_path)
    font.close()


def merge_donor_glyphs(target_path: str, donor_path: str) -> None:
    """Merge Latin, numbers, and punctuation from donor font into target."""
    donor = TTFont(donor_path)
    target = TTFont(target_path)

    donor_cmap = donor.getBestCmap()

    # Codepoint ranges to borrow
    borrow_ranges = [
        (0x0020, 0x007E),   # Basic Latin (space through tilde)
        (0x00A0, 0x00FF),   # Latin-1 Supplement
    ]

    existing_cmap = target.getBestCmap()
    glyphs_to_copy = set()
    new_cmap_entries = {}

    for start, end in borrow_ranges:
        for cp in range(start, end + 1):
            if cp in existing_cmap:
                continue
            if cp in donor_cmap:
                glyph_name = donor_cmap[cp]
                glyphs_to_copy.add(glyph_name)
                new_cmap_entries[cp] = glyph_name

    # Also collect component dependencies (composite glyphs)
    donor_glyf = donor["glyf"]
    all_to_copy = set(glyphs_to_copy)
    for glyph_name in glyphs_to_copy:
        if glyph_name in donor_glyf:
            glyph = donor_glyf[glyph_name]
            if glyph.isComposite():
                for component in glyph.components:
                    all_to_copy.add(component.glyphName)

    target_glyf = target["glyf"]
    target_hmtx = target["hmtx"]
    donor_hmtx = donor["hmtx"]
    glyph_order = list(target.getGlyphOrder())

    for glyph_name in sorted(all_to_copy):
        if glyph_name in target_glyf:
            continue
        if glyph_name not in donor_glyf:
            continue

        target_glyf[glyph_name] = donor_glyf[glyph_name]
        glyph_order.append(glyph_name)

        if glyph_name in donor_hmtx.metrics:
            target_hmtx.metrics[glyph_name] = donor_hmtx.metrics[glyph_name]

    target.setGlyphOrder(glyph_order)

    # Update cmap
    for subtable in target["cmap"].tables:
        if hasattr(subtable, "cmap"):
            subtable.cmap.update(new_cmap_entries)

    target["maxp"].numGlyphs = len(glyph_order)

    target.save(target_path)
    donor.close()
    target.close()


def create_bold_font(svg_dir: str, output_path: str, donor_font: str = None) -> None:
    """Orchestrator: load SVGs, normalise, and build a Bold TTF.

    Parameters
    ----------
    svg_dir : str
        Directory containing SVG glyph files.
    output_path : str
        Where to write the resulting ``.ttf``.
    donor_font : str, optional
        Path to a donor TrueType font from which Latin glyphs are merged.
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

    # Add programmatic mark glyphs (diamond, circle)
    add_mark_glyphs(glyph_contours)

    build_font(glyph_contours, FONT_FAMILY, "Bold", output_path)

    # Add GPOS mark-to-base positioning
    add_gpos_marks(output_path, glyph_contours)

    # Merge Latin/numbers from donor font
    if donor_font and os.path.exists(donor_font):
        merge_donor_glyphs(output_path, donor_font)


def make_hollow_contours(
    contours: list[list[tuple]], stroke_width: int = 60
) -> list[list[tuple]]:
    """Convert filled contours to hollow (outline) contours using polygon offsetting.

    Takes the original (outer) contours, offsets them inward by *stroke_width*
    to produce inner contours, and returns the combined set. The inner contours
    are reversed so that their winding order creates a "hole" when rendered.
    """
    clipper_paths = []
    for contour in contours:
        path = [(int(x), int(y)) for x, y, _ in contour]
        if len(path) >= 3:
            clipper_paths.append(path)

    if not clipper_paths:
        return contours

    pco = pyclipper.PyclipperOffset()
    for path in clipper_paths:
        pco.AddPath(path, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

    inner_paths = pco.Execute(-stroke_width)

    if not inner_paths:
        return contours

    result = []
    for contour in contours:
        result.append(contour)

    for path in inner_paths:
        inner_contour = [(x, y, True) for x, y in reversed(path)]
        result.append(inner_contour)

    return result


def create_regular_font(svg_dir: str, output_path: str, donor_font: str = None) -> None:
    """Create the Regular (hollow) weight of Mikdash font.

    Works like :func:`create_bold_font` but applies :func:`make_hollow_contours`
    to each glyph after normalisation so the glyphs appear as outlines rather
    than filled shapes.

    Parameters
    ----------
    svg_dir : str
        Directory containing SVG glyph files.
    output_path : str
        Where to write the resulting ``.ttf``.
    donor_font : str, optional
        Path to a donor TrueType font from which Latin glyphs are merged.
    """
    raw_glyphs = load_svg_glyphs(svg_dir)
    stroke_width = int(UNITS_PER_EM * HOLLOW_STROKE_RATIO)

    glyph_contours: dict[str, tuple[list[list[tuple]], int]] = {}
    for name, contours in raw_glyphs.items():
        normalized, advance_width = normalize_contours(contours)
        if normalized:
            hollow = make_hollow_contours(normalized, stroke_width=stroke_width)
            bearing = max(int(advance_width * 0.05), 10)
            shifted = []
            for contour in hollow:
                shifted.append([(x + bearing, y, on) for x, y, on in contour])
            glyph_contours[name] = (shifted, advance_width + bearing * 2)

    # Add programmatic mark glyphs (diamond, circle)
    add_mark_glyphs(glyph_contours)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    build_font(glyph_contours, FONT_FAMILY, "Regular", output_path)

    # Add GPOS mark-to-base positioning
    add_gpos_marks(output_path, glyph_contours)

    # Merge Latin/numbers from donor font
    if donor_font and os.path.exists(donor_font):
        merge_donor_glyphs(output_path, donor_font)
