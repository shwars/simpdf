from pathlib import Path

from simpdf import FontFace, MarkdownPdfRenderer


ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
OUTPUT = ROOT / "examples" / "basic_render.pdf"

markdown_text = """
# Basic Example

Привет, мир.

- Первый пункт
- Второй пункт
"""

renderer = MarkdownPdfRenderer(
    font_directory=FONTS_DIR,
    font_face=FontFace.dejavu_sans(),
)

renderer.render_to_file(markdown_text, OUTPUT)
print(f"Wrote {OUTPUT}")
