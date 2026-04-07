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
    # Note: cmap may not have Hebrew mappings yet since SVGs aren't renamed
    # But the font should be valid
    font.close()


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
    assert "glyf" in font
    font.close()


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


def test_font_has_latin_and_numbers(tmp_path):
    """Font should include Latin letters and numbers from EB Garamond."""
    from scripts.assemble import create_bold_font

    output_path = str(tmp_path / "Mikdash-Bold.ttf")
    create_bold_font("glyphs/svg", output_path, donor_font="donor/EBGaramond-Bold.ttf")

    from fontTools.ttLib import TTFont
    font = TTFont(output_path)
    cmap = font.getBestCmap()

    assert ord("A") in cmap, "Missing Latin A"
    assert ord("a") in cmap, "Missing Latin a"
    assert ord("0") in cmap, "Missing digit 0"
    assert ord(".") in cmap, "Missing period"
    font.close()
