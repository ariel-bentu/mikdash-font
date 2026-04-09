import os
import pytest


def test_full_assembly_pipeline(tmp_path):
    """Assembly pipeline should produce both Regular and Bold TTF files from existing SVGs."""
    from scripts.assemble import create_bold_font, create_regular_font

    bold_path = str(tmp_path / "NewMikdash-Bold.ttf")
    regular_path = str(tmp_path / "NewMikdash-Regular.ttf")

    create_bold_font("glyphs/svg", bold_path, donor_font="donor/EBGaramond-Bold.ttf")
    create_regular_font("glyphs/svg", regular_path, donor_font="donor/EBGaramond-Bold.ttf")

    assert os.path.exists(bold_path)
    assert os.path.exists(regular_path)

    from fontTools.ttLib import TTFont

    for path in [bold_path, regular_path]:
        font = TTFont(path)
        cmap = font.getBestCmap()
        # Should have Latin from donor
        assert ord("A") in cmap, f"No Latin A in {os.path.basename(path)}"
        # Should have GPOS
        assert "GPOS" in font, f"No GPOS in {os.path.basename(path)}"
        font.close()
