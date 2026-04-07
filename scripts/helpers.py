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
