"""Build NewMikdash fonts from an existing Hebrew OTF/TTF source.

Takes a source font with Hebrew glyphs, adds diamond/circle marks,
GPOS positioning, Latin donor glyphs, and produces:
  - NewMikdash-Bold.ttf (filled, from source)
  - NewMikdash-Regular.ttf (hollow/outline version)
"""

import os
import math
import calendar
import time

from fontTools.ttLib import TTFont, newTable
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

import pyclipper

from scripts.helpers import (
    ASCENDER,
    COMBINING_CIRCLE,
    COMBINING_DIAMOND,
    COMPOSED_CIRCLE,
    COMPOSED_DIAMOND,
    DESCENDER,
    FONT_FAMILY,
    HEBREW_COMBINING_CIRCLE,
    HEBREW_COMBINING_DIAMOND,
    HEBREW_LETTERS,
    HOLLOW_STROKE_RATIO,
    LINE_GAP,
    STANDALONE_CIRCLE,
    UNITS_PER_EM,
)


# ---------------------------------------------------------------------------
# Extract contours from source font
# ---------------------------------------------------------------------------

def extract_glyph_contours(source_font_path: str) -> dict[str, tuple[list[list[tuple]], int]]:
    """Extract Hebrew glyph contours from a CFF or TrueType font.

    Returns dict mapping our glyph names -> (contours, advance_width).
    Contours are lists of (x, y, on_curve) tuples, scaled to UPM=1000.
    """
    font = TTFont(source_font_path)
    source_upm = font["head"].unitsPerEm
    scale = UNITS_PER_EM / source_upm

    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()

    result = {}

    # Map our names to codepoints from HEBREW_LETTERS
    for our_name, codepoint in HEBREW_LETTERS.items():
        if codepoint not in cmap:
            print(f"  WARNING: U+{codepoint:04X} ({our_name}) not in source font")
            continue

        source_glyph_name = cmap[codepoint]
        adv_width = font["hmtx"].metrics[source_glyph_name][0]
        adv_width_scaled = round(adv_width * scale)

        # Draw glyph to extract contours
        contours = _glyph_to_contours(glyph_set, source_glyph_name, scale)
        if contours:
            result[our_name] = (contours, adv_width_scaled)

    font.close()
    return result


def _glyph_to_contours(
    glyph_set, glyph_name: str, scale: float
) -> list[list[tuple]]:
    """Convert a glyph from a GlyphSet to contour lists of (x, y, on_curve)."""
    from fontTools.pens.recordingPen import RecordingPen

    rec_pen = RecordingPen()
    glyph_set[glyph_name].draw(rec_pen)

    contours = []
    current = []

    for op, args in rec_pen.value:
        if op == "moveTo":
            if current:
                contours.append(current)
                current = []
            x, y = args[0]
            current.append((round(x * scale), round(y * scale), True))

        elif op == "lineTo":
            x, y = args[0]
            current.append((round(x * scale), round(y * scale), True))

        elif op == "curveTo":
            # Cubic bezier: (cp1, cp2, endpoint)
            for i, (x, y) in enumerate(args):
                on_curve = (i == len(args) - 1)
                current.append((round(x * scale), round(y * scale), on_curve))

        elif op == "qCurveTo":
            for i, (x, y) in enumerate(args):
                on_curve = (i == len(args) - 1)
                current.append((round(x * scale), round(y * scale), on_curve))

        elif op == "closePath" or op == "endPath":
            if current:
                contours.append(current)
                current = []

    if current:
        contours.append(current)

    return contours


# ---------------------------------------------------------------------------
# Side-bearing normalisation
# ---------------------------------------------------------------------------

# Fraction of ink width used as side bearing on each side.
_BEARING_RATIO = 0.06  # 6% of ink width per side


def normalize_side_bearings(
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
    bearing_ratio: float = _BEARING_RATIO,
) -> dict[str, tuple[list[list[tuple]], int]]:
    """Recalculate advance widths with consistent proportional side bearings.

    The source font's side bearings are inconsistent (e.g. vav has LSB=41
    while bet has LSB=27). This strips the original bearings by shifting
    contours to x=0, then adds ``bearing_ratio * ink_width`` on each side.
    The result is optically even spacing across narrow and wide letters.
    """
    result = {}
    for name, (contours, _old_adv_w) in glyph_contours.items():
        all_x = [x for c in contours for x, y, _ in c]
        if not all_x:
            result[name] = (contours, _old_adv_w)
            continue

        x_min = min(all_x)
        x_max = max(all_x)
        ink_w = x_max - x_min

        bearing = max(round(ink_w * bearing_ratio), 8)

        # Shift contours so ink starts at x=bearing
        shift = bearing - x_min
        new_contours = [
            [(x + shift, y, on) for x, y, on in c]
            for c in contours
        ]
        new_adv_w = ink_w + 2 * bearing
        result[name] = (new_contours, new_adv_w)

    return result


# ---------------------------------------------------------------------------
# Mark glyphs (same as assemble.py)
# ---------------------------------------------------------------------------

MARK_CODEPOINTS = {
    "diamond_above": COMBINING_DIAMOND,
    "circle_above": COMBINING_CIRCLE,
    "circle_standalone": STANDALONE_CIRCLE,
    "hebrew_diamond": HEBREW_COMBINING_DIAMOND,
    "hebrew_circle": HEBREW_COMBINING_CIRCLE,
}


def create_diamond_contours(size: int = 180) -> list[list[tuple]]:
    half_w = size // 3       # narrower horizontally
    half_h = size // 2       # taller vertically
    return [[(0, half_h, True), (half_w, 0, True), (0, -half_h, True), (-half_w, 0, True)]]


def create_circle_contours(radius: int = 100, hollow: bool = True, segments: int = 32):
    outer = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        outer.append((round(radius * math.cos(angle)),
                       round(radius * math.sin(angle)), True))
    contours = [outer]
    if hollow:
        inner_r = max(radius - 20, radius * 2 // 3)
        inner = []
        for i in range(segments):
            angle = 2 * math.pi * (segments - 1 - i) / segments
            inner.append((round(inner_r * math.cos(angle)),
                          round(inner_r * math.sin(angle)), True))
        contours.append(inner)
    return contours


def _mark_anchor_x(base_name, base_contours, base_adv_w, mark_type="diamond"):
    """Compute the x position for the mark anchor above a base glyph.

    Most letters use the centre of the advance width.  Lamed's ascender
    rises from the left half of the glyph, so the circle mark is shifted
    slightly to the right to avoid collision.  Diamond is fine centred.
    """
    if base_name == "lamed" and mark_type == "circle":
        return round(base_adv_w * 0.60)
    return base_adv_w // 2


def add_mark_glyphs(glyph_contours):
    """Add standalone marks and pre-composed letter+mark glyphs.

    Each letter+mark combination gets its own PUA codepoint (mapped in
    COMPOSED_DIAMOND / COMPOSED_CIRCLE). No GSUB or GPOS needed — the
    user types a single codepoint and gets a glyph with the mark baked
    in at the correct position.
    """
    # Find the typical top of base glyphs (75th percentile)
    glyph_tops = []
    for name, (contours, adv_w) in glyph_contours.items():
        top = 0
        for c in contours:
            for x, y, _ in c:
                if y > top:
                    top = y
        glyph_tops.append(top)
    glyph_tops.sort()
    typical_top = glyph_tops[len(glyph_tops) * 3 // 4]

    mark_y = typical_top + 150

    # Mark contour templates (centered at x=0)
    diamond_template = create_diamond_contours(size=160)
    circle_template = create_circle_contours(radius=80, hollow=True, segments=32)

    # --- Standalone mark glyphs ---
    glyph_contours["diamond_above"] = (
        [[(x, y + mark_y, on) for x, y, on in c] for c in diamond_template], 0
    )
    glyph_contours["circle_above"] = (
        [[(x, y + mark_y, on) for x, y, on in c] for c in circle_template], 0
    )

    # --- Standalone circle (same size as combining circle mark) ---
    standalone = create_circle_contours(radius=80, hollow=True, segments=32)
    standalone_x = 100
    standalone_y = typical_top // 2
    glyph_contours["circle_standalone"] = (
        [[(x + standalone_x, y + standalone_y, on) for x, y, on in c] for c in standalone], 200
    )

    # --- Hebrew combining marks (zero-width, positioned by GPOS) ---
    # These use real Hebrew codepoints so they stay in the same shaping run.
    # Contours centered at x=0; GPOS mark-to-base anchors handle positioning.
    glyph_contours["hebrew_diamond"] = (
        [[(x, y + mark_y, on) for x, y, on in c] for c in diamond_template], 0
    )
    glyph_contours["hebrew_circle"] = (
        [[(x, y + mark_y, on) for x, y, on in c] for c in circle_template], 0
    )

    # --- Pre-composed letter+mark glyphs (one PUA codepoint each) ---
    for base_name in list(glyph_contours.keys()):
        if base_name in ("diamond_above", "circle_above", "circle_standalone"):
            continue
        if base_name not in COMPOSED_DIAMOND:
            continue

        base_contours, base_adv_w = glyph_contours[base_name]

        # letter + diamond
        diamond_x = _mark_anchor_x(base_name, base_contours, base_adv_w, "diamond")
        diamond_contours = [
            [(x + diamond_x, y + mark_y, on) for x, y, on in c]
            for c in diamond_template
        ]
        glyph_contours[f"{base_name}_diamond"] = (
            list(base_contours) + diamond_contours, base_adv_w
        )

        # letter + circle
        circle_x = _mark_anchor_x(base_name, base_contours, base_adv_w, "circle")
        circle_contours_mark = [
            [(x + circle_x, y + mark_y, on) for x, y, on in c]
            for c in circle_template
        ]
        glyph_contours[f"{base_name}_circle"] = (
            list(base_contours) + circle_contours_mark, base_adv_w
        )

    return mark_y


def add_gpos_marks(font_path, glyph_contours, mark_y):
    """Add GPOS mark-to-base positioning for Hebrew combining marks.

    Uses separate lookups for diamond and circle so that per-letter
    anchor offsets (e.g. lamed circle shifted right) work correctly.
    """
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

    has_diamond = "hebrew_diamond" in glyph_contours
    has_circle = "hebrew_circle" in glyph_contours
    if not has_diamond and not has_circle:
        return

    base_names = sorted(
        name for name in glyph_contours
        if name in HEBREW_LETTERS
    )
    if not base_names:
        return

    font = TTFont(font_path)

    lines = []

    # Separate mark class + lookup for each mark type
    if has_diamond:
        lines.append(
            "markClass hebrew_diamond <anchor 0 %d> @mark_diamond;" % mark_y
        )
    if has_circle:
        lines.append(
            "markClass hebrew_circle <anchor 0 %d> @mark_circle;" % mark_y
        )

    lines.append("feature mark {")

    if has_diamond:
        lines.append("  lookup mark2base_diamond {")
        for base_name in base_names:
            base_contours, adv_w = glyph_contours[base_name]
            anchor_x = _mark_anchor_x(base_name, base_contours, adv_w, "diamond")
            lines.append(
                "    pos base %s <anchor %d %d> mark @mark_diamond;"
                % (base_name, anchor_x, mark_y)
            )
        lines.append("  } mark2base_diamond;")

    if has_circle:
        lines.append("  lookup mark2base_circle {")
        for base_name in base_names:
            base_contours, adv_w = glyph_contours[base_name]
            anchor_x = _mark_anchor_x(base_name, base_contours, adv_w, "circle")
            lines.append(
                "    pos base %s <anchor %d %d> mark @mark_circle;"
                % (base_name, anchor_x, mark_y)
            )
        lines.append("  } mark2base_circle;")

    lines.append("} mark;")

    fea_code = "\n".join(lines)
    addOpenTypeFeaturesFromString(font, fea_code)
    font.save(font_path)
    font.close()


# ---------------------------------------------------------------------------
# Hollow contour generation
# ---------------------------------------------------------------------------

def make_hollow_contours(contours, stroke_width=35):
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

    result = list(contours)
    for path in inner_paths:
        result.append([(x, y, True) for x, y in reversed(path)])
    return result


# ---------------------------------------------------------------------------
# Font building
# ---------------------------------------------------------------------------

def _draw_contours_to_glyph(contours):
    tt_pen = TTGlyphPen(None)
    cu2qu_pen = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=False)

    for contour in contours:
        if not contour:
            continue
        segments = _contour_to_segments(contour)
        if not segments:
            continue

        cu2qu_pen.moveTo(segments[0][0])
        for seg in segments[1:]:
            if len(seg) == 1:
                cu2qu_pen.lineTo(seg[0])
            elif len(seg) == 3:
                cu2qu_pen.curveTo(*seg)
            elif len(seg) == 2:
                cu2qu_pen.qCurveTo(*seg)
        cu2qu_pen.closePath()

    return tt_pen.glyph()


def _contour_to_segments(contour):
    segments = []
    current_segment = []
    for i, (x, y, on_curve) in enumerate(contour):
        if i == 0:
            segments.append([(x, y)])
            continue
        if on_curve:
            current_segment.append((x, y))
            segments.append(current_segment)
            current_segment = []
        else:
            current_segment.append((x, y))
    return segments


def build_font_from_contours(
    glyph_contours: dict[str, tuple[list[list[tuple]], int]],
    family_name: str,
    style_name: str,
    output_path: str,
    is_italic: bool = False,
) -> None:
    glyph_names = [".notdef"] + sorted(glyph_contours.keys())

    cmap = {}
    for name in glyph_names:
        if name in HEBREW_LETTERS:
            cmap[HEBREW_LETTERS[name]] = name
        elif name in MARK_CODEPOINTS:
            cmap[MARK_CODEPOINTS[name]] = name
        elif name.endswith("_diamond"):
            base = name[:-len("_diamond")]
            if base in COMPOSED_DIAMOND:
                cmap[COMPOSED_DIAMOND[base]] = name
        elif name.endswith("_circle"):
            base = name[:-len("_circle")]
            if base in COMPOSED_CIRCLE:
                cmap[COMPOSED_CIRCLE[base]] = name

    metrics = {".notdef": (UNITS_PER_EM // 2, 0)}
    for name, (_, adv_w) in glyph_contours.items():
        metrics[name] = (max(adv_w, 1), 0)

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)
    fb.setupGlyphOrder(glyph_names)
    fb.setupCharacterMap(cmap)

    # Build glyf
    glyph_table = {}
    for name in glyph_names:
        if name == ".notdef":
            pen = TTGlyphPen(None)
            pen.moveTo((0, 0))
            pen.lineTo((0, ASCENDER))
            pen.lineTo((UNITS_PER_EM // 2, ASCENDER))
            pen.lineTo((UNITS_PER_EM // 2, 0))
            pen.closePath()
            glyph_table[name] = pen.glyph()
        else:
            contours, _ = glyph_contours[name]
            glyph_table[name] = _draw_contours_to_glyph(contours)

    fb.setupGlyf(glyph_table)

    # Set LSB = xMin for each glyph so the renderer respects contour positions
    for name in glyph_names:
        g = glyph_table[name]
        if hasattr(g, 'xMin'):
            metrics[name] = (metrics[name][0], g.xMin)

    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)

    full_name = f"{family_name} {style_name}"
    ps_name = f"{family_name}-{style_name}"
    fb.setupNameTable({
        "copyright": "Copyright 2026, NewMikdash Font Project",
        "familyName": family_name,
        "styleName": style_name,
        "uniqueFontIdentifier": f"1.000;NONE;{ps_name}",
        "fullName": full_name,
        "version": "Version 1.000",
        "psName": ps_name,
    })

    fs_selection = 0
    if is_italic:
        fs_selection |= 0x0001  # ITALIC
    else:
        fs_selection |= 0x0040  # REGULAR

    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        sTypoLineGap=LINE_GAP,
        fsSelection=fs_selection,
    )
    fb.setupPost(isFixedPitch=0, italicAngle=-12 if is_italic else 0)

    now = calendar.timegm(time.gmtime())
    mac_style = 0x0002 if is_italic else 0x0000  # bit 1 = italic
    fb.setupHead(unitsPerEm=UNITS_PER_EM, created=now, modified=now,
                 macStyle=mac_style)

    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000A}
    fb.font["gasp"] = gasp

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fb.font.save(output_path)


def merge_donor_glyphs(target_path, donor_path):
    """Merge Latin glyphs from donor font."""
    from scripts.assemble import merge_donor_glyphs as _merge
    _merge(target_path, donor_path)


# ---------------------------------------------------------------------------
# Main build functions
# ---------------------------------------------------------------------------

def build_from_source(
    source_font: str,
    output_dir: str = "output",
    donor_font: str = None,
):
    """Build NewMikdash Regular (filled) + Italic (hollow) from an existing Hebrew font."""
    print(f"Extracting Hebrew glyphs from {source_font}...")
    glyph_contours = extract_glyph_contours(source_font)
    print(f"  Extracted {len(glyph_contours)} glyphs")

    # Normalise side bearings for consistent inter-letter spacing
    glyph_contours = normalize_side_bearings(glyph_contours)

    # Add marks and pre-composed letter+mark glyphs
    mark_y = add_mark_glyphs(glyph_contours)

    # --- Regular (filled) ---
    regular_path = os.path.join(output_dir, "NewMikdash-Regular.ttf")
    print(f"Building Regular (filled) -> {regular_path}")
    build_font_from_contours(glyph_contours, FONT_FAMILY, "Regular", regular_path,
                             is_italic=False)
    add_gpos_marks(regular_path, glyph_contours, mark_y)
    if donor_font and os.path.exists(donor_font):
        merge_donor_glyphs(regular_path, donor_font)

    # --- Italic (hollow) ---
    stroke_width = int(UNITS_PER_EM * 0.03)
    hollow_contours = {}
    skip_hollow = {"diamond_above", "circle_above", "circle_standalone",
                   "hebrew_diamond", "hebrew_circle"}
    for name, (contours, adv_w) in glyph_contours.items():
        if name in skip_hollow:
            hollow_contours[name] = (contours, adv_w)
        elif "_diamond" in name or "_circle" in name:
            # Composed glyph: hollow only the base part, keep mark as-is
            base_name = name.rsplit("_", 1)[0]
            if base_name in glyph_contours:
                n_base = len(glyph_contours[base_name][0])
                base_part = contours[:n_base]
                mark_part = contours[n_base:]
                hollow_base = make_hollow_contours(base_part, stroke_width=stroke_width)
                hollow_contours[name] = (hollow_base + mark_part, adv_w)
            else:
                hollow_contours[name] = (contours, adv_w)
        else:
            hollow = make_hollow_contours(contours, stroke_width=stroke_width)
            hollow_contours[name] = (hollow, adv_w)

    italic_path = os.path.join(output_dir, "NewMikdash-Italic.ttf")
    print(f"Building Italic (hollow) -> {italic_path}")
    build_font_from_contours(hollow_contours, FONT_FAMILY, "Italic", italic_path,
                             is_italic=True)
    add_gpos_marks(italic_path, glyph_contours, mark_y)
    if donor_font and os.path.exists(donor_font):
        merge_donor_glyphs(italic_path, donor_font)

    print("Done!")


if __name__ == "__main__":
    build_from_source(
        "FrankRuehlCLM-Medium.otf",
        "output",
        donor_font="donor/EBGaramond-Bold.ttf",
    )
