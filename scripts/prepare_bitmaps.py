"""Rename Hebrew-named bitmaps to HEBREW_LETTERS keys and prepare for vectorization."""

import os
import shutil
import glob

# Mapping: Hebrew character filename stem -> HEBREW_LETTERS key
RENAME_MAP = {
    "א": "alef",
    "ב": "bet",
    "ג": "gimel",
    "ד": "dalet",
    "ה": "he",
    "ו": "vav",
    "ז": "zayin",
    "ח": "chet",
    "ט": "tet",
    "י": "yod",
    "כ": "kaf",
    "ך": "final_kaf",
    "ל": "lamed",
    "מ": "mem",
    "ם": "final_mem",
    "נ": "nun",
    "ן": "final_nun",
    "ס": "samekh",
    "ע": "ayin",
    "פ": "pe",
    "ף": "final_pe",
    "צ": "tsade",
    "ץ": "final_tsade",
    "ק": "qof",
    "ר": "resh",
    "ש": "shin",
    "ת": "tav",
}


def prepare_bitmaps():
    src_dir = "glyphs/bitmaps"
    dst_dir = "glyphs/named-bitmaps"
    os.makedirs(dst_dir, exist_ok=True)

    # Clean destination
    for f in glob.glob(os.path.join(dst_dir, "*.png")):
        os.remove(f)

    copied = []
    for hebrew_char, english_key in RENAME_MAP.items():
        src = os.path.join(src_dir, f"{hebrew_char}.png")
        if os.path.exists(src):
            dst = os.path.join(dst_dir, f"{english_key}.png")
            shutil.copy2(src, dst)
            copied.append(english_key)
            print(f"  {hebrew_char}.png -> {english_key}.png")

    # Also copy vav.png if the Hebrew ו wasn't already mapped
    if "vav" not in copied:
        src = os.path.join(src_dir, "vav.png")
        if os.path.exists(src):
            dst = os.path.join(dst_dir, "vav.png")
            shutil.copy2(src, dst)
            copied.append("vav")
            print(f"  vav.png -> vav.png")

    print(f"\nPrepared {len(copied)} glyph bitmaps in {dst_dir}/")

    # Report missing
    all_keys = set(RENAME_MAP.values())
    missing = all_keys - set(copied)
    if missing:
        print(f"Missing: {', '.join(sorted(missing))}")

    return dst_dir


if __name__ == "__main__":
    prepare_bitmaps()
