"""Mikdash Font — Full build pipeline.

Usage: python scripts/build.py [--source font.jpg] [--output output/] [--donor donor/EBGaramond-Bold.ttf]
"""

import argparse
import glob
import os
import sys

from scripts.preprocess import preprocess
from scripts.segment import segment
from scripts.vectorize import vectorize_all
from scripts.assemble import create_bold_font, create_regular_font
from scripts.helpers import HEBREW_LETTERS


def build_all(
    source_image: str = "font.jpg",
    output_dir: str = "output",
    donor_font: str = None,
) -> None:
    """Run the full pipeline: preprocess -> segment -> vectorize -> assemble."""
    print("=" * 60)
    print("Mikdash Font Build Pipeline")
    print("=" * 60)

    # Step 1: Preprocess
    print("\n[1/4] Preprocessing image...")
    preprocess(source_image)

    # Step 2: Segment
    print("\n[2/4] Segmenting glyphs...")
    segment("glyphs/preprocessed.png")

    # Check if bitmaps have been renamed to Hebrew letter names
    named_bitmaps = [
        f
        for f in glob.glob("glyphs/bitmaps/*.png")
        if os.path.splitext(os.path.basename(f))[0] in HEBREW_LETTERS
    ]

    if not named_bitmaps:
        print(
            "\n*** MANUAL STEP REQUIRED ***"
            "\nReview glyphs/bitmaps/ and rename files to Hebrew letter names."
            "\nE.g.: char_01_003.png -> alef.png, char_02_005.png -> bet.png"
            "\nThen re-run this script to continue from vectorization."
            "\nNo named glyph bitmaps found. Please rename and re-run."
        )
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
    parser.add_argument("--donor", default="donor/EBGaramond-Bold.ttf", help="Donor font path")
    args = parser.parse_args()

    build_all(source_image=args.source, output_dir=args.output, donor_font=args.donor)
