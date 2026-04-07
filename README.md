# Mikdash Font

A Hebrew font family designed for scholarly transcription of Dead Sea Scrolls and similar ancient texts. Features custom diacritical marks (diamond and circle above letters) used in academic publications.

**Two weights:**

- **Mikdash-Bold** — filled (solid) glyphs
- **Mikdash-Regular** — hollow (outline) glyphs

![Sample](https://raw.githubusercontent.com/ariel-bentu/mikdash-font/main/output/sample.png)

## Download

Pre-built font files are in the [`output/`](output/) directory:

- [`Mikdash-Bold.ttf`](output/Mikdash-Bold.ttf)
- [`Mikdash-Regular.ttf`](output/Mikdash-Regular.ttf)

Install by double-clicking the `.ttf` files (macOS/Windows) or copying them to your system font directory.

## Features

- All 27 Hebrew letters (22 consonants + 5 final forms)
- Diamond mark above any letter (used in scholarly transcriptions to indicate uncertain readings)
- Circle mark above any letter (used to mark scribal corrections or additions)
- Standalone circle glyph
- Latin alphabet, numbers, and punctuation (borrowed from EB Garamond)
- Both weights share identical metrics for easy switching

## Using the Special Marks

Each letter+mark combination is a single pre-composed glyph at a Private Use Area (PUA) Unicode codepoint. In HTML:

```html
<!-- Letter with diamond above -->
&#xE100;  <!-- alef + diamond -->
&#xE119;  <!-- shin + diamond -->

<!-- Letter with circle above -->
&#xE11B;  <!-- alef + circle -->
&#xE134;  <!-- shin + circle -->

<!-- Standalone circle -->
&#x25CB;
```

### Codepoint Reference

| Letter | + Diamond | + Circle | | Letter | + Diamond | + Circle |
|--------|-----------|----------|-|--------|-----------|----------|
| א Alef | U+E100 | U+E11B | | נ Nun | U+E10F | U+E12A |
| ב Bet | U+E101 | U+E11C | | ן Final Nun | U+E110 | U+E12B |
| ג Gimel | U+E102 | U+E11D | | ס Samekh | U+E111 | U+E12C |
| ד Dalet | U+E103 | U+E11E | | ע Ayin | U+E112 | U+E12D |
| ה He | U+E104 | U+E11F | | פ Pe | U+E113 | U+E12E |
| ו Vav | U+E105 | U+E120 | | ף Final Pe | U+E114 | U+E12F |
| ז Zayin | U+E106 | U+E121 | | צ Tsade | U+E115 | U+E130 |
| ח Chet | U+E107 | U+E122 | | ץ Final Tsade | U+E116 | U+E131 |
| ט Tet | U+E108 | U+E123 | | ק Qof | U+E117 | U+E132 |
| י Yod | U+E109 | U+E124 | | ר Resh | U+E118 | U+E133 |
| כ Kaf | U+E10A | U+E125 | | ש Shin | U+E119 | U+E134 |
| ך Final Kaf | U+E10B | U+E126 | | ת Tav | U+E11A | U+E135 |
| ל Lamed | U+E10C | U+E127 | | | | |
| מ Mem | U+E10D | U+E128 | | | | |
| ם Final Mem | U+E10E | U+E129 | | | | |

### Test Page

Open [`test.html`](test.html) in a browser for an interactive preview with all glyphs and a textarea where you can type with the special marks.

## Building from Source

### Prerequisites

- Python 3.10+
- potrace (`brew install potrace` on macOS)

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Build

The primary build extracts Hebrew glyphs from [FrankRuehlCLM](https://culmus.sourceforge.io/) and adds the custom marks and hollow weight:

```bash
python -m scripts.assemble_from_font
```

Output: `output/Mikdash-Bold.ttf` and `output/Mikdash-Regular.ttf`

There is also a full image-based pipeline that extracts glyphs from a scanned page (`font.jpg`):

```bash
python scripts/build.py
```

### Tests

```bash
python -m pytest tests/ -v
```

## How It Works

1. Hebrew glyph contours are extracted from `FrankRuehlCLM-Medium.otf`
2. Side bearings are normalized to 6% of ink width for consistent letter spacing
3. Pre-composed letter+mark glyphs are created — each letter+diamond and letter+circle combination is a single glyph with the mark baked in at the correct position (centered above the letter)
4. **Bold** uses the filled contours directly
5. **Regular** applies an inward polygon offset (via pyclipper) to create hollow outlines
6. Latin characters, numbers, and punctuation are merged from EB Garamond

### Why Pre-composed Glyphs?

Web browsers (Chrome, Safari, Firefox) do not apply OpenType GPOS or GSUB features across Hebrew letters and Private Use Area characters — the HarfBuzz text shaper splits them into separate shaping runs. Pre-composed single-codepoint glyphs bypass this limitation entirely.

## License

This project is licensed under the **GNU General Public License v2.0** — see the [LICENSE](LICENSE) file.

### Attribution

- **Hebrew glyphs:** Derived from [FrankRuehlCLM](https://culmus.sourceforge.io/) (Frank-Ruehl font family), copyright 2002-2011 Maxim Iorsh. Distributed under GPL v2.
- **Latin glyphs, digits, and punctuation in the base font:** Portions of Century Schoolbook L Roman ver. 1.06, copyright 1999 (URW)++ Design & Development. All rights reserved.
- **Latin glyphs, digits, and punctuation (donor):** [EB Garamond](https://github.com/georgd/EB-Garamond), distributed under the SIL Open Font License.

### Source Code Availability

As required by GPL v2, the complete source code for building this font is included in this repository. You can rebuild the font files from source using the instructions above.

### Redistribution

If you redistribute Mikdash (modified or unmodified), you must:

1. Include a copy of the GPL v2 license ([LICENSE](LICENSE))
2. Include the source code or a written offer to provide it
3. Preserve the copyright notices listed above
4. License your modifications under GPL v2
