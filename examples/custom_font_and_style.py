from pathlib import Path

from simpdf import FontFace, MarkdownPdfRenderer


ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
OUTPUT = ROOT / "examples" / "custom_font_and_style.pdf"

markdown_text = """
# Styled Output

This paragraph is in English, but the next one contains Cyrillic.

Пример текста с настраиваемыми размерами заголовков и таблиц.

| Column | Value |
| --- | --- |
| A | 10 |
| B | 20 |
"""

renderer = MarkdownPdfRenderer(
    font_directory=FONTS_DIR,
    font_face=FontFace.dejavu_sans(),
    formatting_options={
        "text": {"font_size": 11},
        "headings": {"sizes": {1: 28, 2: 20, 3: 16}},
        "table": {"heading_font_size": 13, "font_size": 10},
    },
)

renderer.render_to_file(markdown_text, OUTPUT)
print(f"Wrote {OUTPUT}")
