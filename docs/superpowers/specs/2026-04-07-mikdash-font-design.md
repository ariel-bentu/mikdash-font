# NewMikdash Font — Design Spec

## Overview

Reverse-engineer the Hebrew typeface from `font.jpg` (a scholarly Dead Sea Scrolls transcription, Column VII) into a TTF font family called **NewMikdash** with two weights:

- **NewMikdash-Regular** — hollow (outline-only) glyphs
- **NewMikdash-Bold** — filled (solid) glyphs

## Source Material

`font.jpg` — a scanned page of a Qumran/Temple Scroll scholarly transcription. The Hebrew text uses a distinctive serif square-script typeface. The image includes diacritical marks (diamonds and circles above letters) and footnotes in English.

## Glyph Inventory

### Hebrew Letters (27 glyphs)

22 standard consonants + 5 final (sofit) forms:

| Letter | Unicode | Letter | Unicode |
|--------|---------|--------|---------|
| Alef א | U+05D0 | Lamed ל | U+05DC |
| Bet ב | U+05D1 | Mem מ | U+05DE |
| Gimel ג | U+05D2 | Final Mem ם | U+05DD |
| Dalet ד | U+05D3 | Nun נ | U+05E0 |
| He ה | U+05D4 | Final Nun ן | U+05DF |
| Vav ו | U+05D5 | Samekh ס | U+05E1 |
| Zayin ז | U+05D6 | Ayin ע | U+05E2 |
| Chet ח | U+05D7 | Pe פ | U+05E4 |
| Tet ט | U+05D8 | Final Pe ף | U+05E3 |
| Yod י | U+05D9 | Tsade צ | U+05E6 |
| Kaf כ | U+05DB | Final Tsade ץ | U+05E5 |
| Final Kaf ך | U+05DA | Qof ק | U+05E7 |
| | | Resh ר | U+05E8 |
| | | Shin ש | U+05E9 |
| | | Tav ת | U+05EA |

Each letter exists in both Regular (hollow) and Bold (filled) variants.

### Special Marks

#### Diamond (◆) — Combining Mark Only
- Always solid filled in both Regular and Bold weights
- Combining diacritical mark positioned above base Hebrew letters
- No standalone glyph
- Unicode: Private Use Area (e.g., U+E001) with OpenType `mark` feature

#### Circle (○) — Two Forms
- Always hollow (outline) in both Regular and Bold weights
- **Combining mark:** positioned above base Hebrew letters (same mechanism as diamond)
- **Standalone glyph:** occupies its own horizontal space, centered vertically
- Combining: PUA (e.g., U+E002) with OpenType `mark` feature
- Standalone: U+25CB (WHITE CIRCLE) or U+05C0 range

### Borrowed Glyphs (from EB Garamond, OFL licensed)
- Latin alphabet (A-Z, a-z)
- Numerals (0-9)
- Basic punctuation (. , ; : ! ? - — ' " ( ) [ ])
- Subset only what is needed

## Font Metrics

Derived from image measurements:
- **Units per em:** 1000 (standard)
- **Ascender / Descender / Line gap:** measured from image character proportions
- **Advance widths:** per-glyph, measured from image spacing
- **Right-to-left:** Hebrew glyphs flagged RTL in OpenType tables

## Hollow vs Filled Generation

1. Start with high-fidelity filled (Bold) contours for each glyph
2. **Bold:** use the filled contours directly
3. **Regular:** generate inward offset contours to create outline/stroke effect
   - Stroke width: ~8-10% of em square (exact value calibrated from image)
   - Result: outer contour + inner contour forming a hollow ring shape
   - Consistent stroke width across all letters

## OpenType Tables

### Required Tables
- `cmap` — Unicode character mappings (Hebrew block, PUA for marks, Latin)
- `GPOS` — Glyph positioning:
  - Mark-to-base anchors: each Hebrew base glyph has an anchor above center
  - Diamond and circle combining marks have corresponding anchors
  - Allows any Hebrew letter to combine with either mark
- `name` — Font family: "NewMikdash", subfamilies: "Regular", "Bold"
- `OS/2` — Weight class, Unicode ranges, script coverage
- `head`, `hhea`, `hmtx`, `maxp`, `post` — standard required tables

### Script/Language Support
- Hebrew script (`hebr`)
- Latin script (`latn`) via borrowed glyphs

## Pipeline

### Step 1: Preprocessing (`scripts/preprocess.py`)
- Load `font.jpg`
- Convert to grayscale
- Apply adaptive thresholding for clean binary image
- Deskew if needed
- Enhance contrast
- Output: clean binary image

### Step 2: Glyph Segmentation (`scripts/segment.py`)
- Define crop regions for each unique Hebrew character in the image
- Semi-automatic: use contour detection to find character bounding boxes, with manual region specification as fallback
- Extract each character as an isolated bitmap
- Multiple samples of same letter averaged/best-picked for quality
- Output: individual glyph bitmaps in `glyphs/bitmaps/`

### Step 3: Vectorization (`scripts/vectorize.py`)
- For each glyph bitmap, run potrace (or Python binding) to convert to SVG outlines
- Clean up: simplify paths, remove noise, smooth curves
- Normalize to consistent em-square sizing
- Output: SVG files in `glyphs/svg/`

### Step 4: Font Assembly (`scripts/assemble.py`)
- Load SVG glyphs into fontTools TTFont
- Generate Bold weight from filled contours
- Generate Regular weight by creating inward offset (hollow) contours
- Import EB Garamond Latin/number subset
- Build `cmap`, `GPOS`, `name`, and other OpenType tables
- Set font metrics (ascender, descender, advance widths)
- Add combining mark anchors for diamond and circle
- Add standalone circle glyph
- Output: `output/NewMikdash-Regular.ttf` and `output/NewMikdash-Bold.ttf`

## File Structure

```
fontNewMikdash/
├── font.jpg                          # Source image
├── scripts/
│   ├── preprocess.py              # Image cleanup
│   ├── segment.py                 # Glyph extraction
│   ├── vectorize.py               # Bitmap -> SVG
│   └── assemble.py                # SVG -> TTF
├── glyphs/
│   ├── bitmaps/                      # Cropped glyph images
│   └── svg/                          # Vectorized glyphs (review these)
├── donor/                            # EB Garamond subset files
├── docs/superpowers/specs/
│   └── 2026-04-07-mikdash-font-design.md
└── output/
    ├── NewMikdash-Regular.ttf
    └── NewMikdash-Bold.ttf
```

## Dependencies

- Python 3.10+
- Pillow — image processing
- OpenCV (cv2) — contour detection, segmentation
- potrace / pypotrace or Pillow+skimage — bitmap to vector conversion
- fontTools — TTF assembly and OpenType table construction
- shapely or clipper — contour offsetting for hollow glyphs
- EB Garamond font files (OFL license) — Latin/number donor

## Quality Checkpoints

1. After Step 2: review `glyphs/bitmaps/` — all 27 letters cleanly isolated?
2. After Step 3: review `glyphs/svg/` — contours smooth, no artifacts, faithful to source?
3. After Step 4: install TTF, type sample Hebrew text — correct rendering, proper RTL, marks position correctly?

## Risks and Mitigations

- **Low image resolution:** some fine details may be lost in vectorization. Mitigation: manual SVG cleanup at Step 3, pick best glyph samples.
- **Hollow generation artifacts:** inward offset can create self-intersecting paths on complex glyphs. Mitigation: use Clipper library for robust offsetting, validate each glyph.
- **Mark positioning:** combining marks may need per-letter anchor tuning. Mitigation: start with centered-above default, refine per glyph as needed.
- **Not all 27 letters may be clearly visible** in the single image. Mitigation: identify which letters are present, flag missing ones for manual creation or sourcing from similar scholarly texts.
