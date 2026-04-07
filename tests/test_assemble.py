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
