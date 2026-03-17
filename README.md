# simpdf

`simpdf` is a small Python library for rendering Markdown into PDF with `fpdf2`, while keeping font handling explicit so Cyrillic and other non-Latin text work reliably with external TTF fonts.

The library is centered on a `MarkdownPdfRenderer` class. You give it a directory with TTF files, describe the font face to register, and then render Markdown into PDF bytes or directly into a file.

## Features

- Uses `fpdf2` as the PDF backend
- Supports external TTF fonts and Cyrillic-friendly fonts such as DejaVu Sans
- Provides a helper to download DejaVu Sans fonts into a target directory
- Supports markdown images from filesystem paths, `data:` URLs, remote URLs, and custom callbacks
- Class-first API with optional convenience helpers
- Minimal CLI for rendering Markdown and downloading DejaVu fonts
- Supports these Markdown elements in v1:
  - headings
  - paragraphs
  - bold and italic text
  - inline code
  - ordered and unordered lists
  - tables
  - blockquotes
  - fenced code blocks
  - thematic breaks
  - clickable links
  - block images

## Installation

```bash
pip install simpdf
```

For development and tests:

```bash
pip install -e .[dev]
```

## Quick Start

```python
from simpdf import FontFace, MarkdownPdfRenderer

renderer = MarkdownPdfRenderer(
    font_directory="fonts",
    font_face=FontFace.dejavu_sans(),
)

markdown_text = """
# Example

Привет, мир.

- one
- two
"""

pdf_bytes = renderer.render_to_bytes(markdown_text)

with open("output.pdf", "wb") as handle:
    handle.write(pdf_bytes)
```

## Downloading DejaVu Fonts

The library does not bundle fonts inside the wheel. Use the download helper to populate your own font directory.

```python
from simpdf import download_dejavu_fonts

downloaded = download_dejavu_fonts("fonts")
print([path.name for path in downloaded])
```

The helper downloads the DejaVu font files from public GitHub repository.

## Using Custom Fonts

You can use any TTF family as long as you provide at least a regular face. Bold, italic, and bold-italic are optional; if omitted, the regular face is reused.

```python
from simpdf import FontFace, MarkdownPdfRenderer

renderer = MarkdownPdfRenderer(
    font_directory="my-fonts",
    font_face=FontFace(
        family="NotoSansCustom",
        regular="NotoSans-Regular.ttf",
        bold="NotoSans-Bold.ttf",
        italic="NotoSans-Italic.ttf",
        bold_italic="NotoSans-BoldItalic.ttf",
    ),
)
```

Font file values may be file names relative to `font_directory` or absolute paths.

## Formatting Options

Formatting is configured with a plain nested dictionary. Any omitted value falls back to the library defaults.

Example:

```python
from simpdf import FontFace, MarkdownPdfRenderer

renderer = MarkdownPdfRenderer(
    font_directory="fonts",
    font_face=FontFace.dejavu_sans(),
    formatting_options={
        "text": {"font_size": 11},
        "headings": {
            "sizes": {1: 26, 2: 20, 3: 16},
        },
        "lists": {"indent": 9},
        "table": {"heading_font_size": 13},
    },
)
```

Supported option groups:

- `page`: page size, orientation, and margins
- `text`: base font size, line height multiplier, text color
- `headings`: per-level sizes and spacing
- `paragraph`: paragraph spacing
- `lists`: indent, bullet symbol, list spacing
- `blockquote`: indent, bar styling, text color
- `table`: font sizes, padding, minimum column width, spacing
- `code_block`: font size, padding, colors, spacing
- `inline_code`: inline code text color
- `images`: block image sizing, spacing, alignment, table-cell best-effort height
- `links`: link color and underline toggle
- `thematic_break`: rule color, width, spacing

## Image Support

Markdown images use the normal syntax:

```markdown
![alt text](path-or-url)
```

Supported image sources in `0.1.1`:

- custom callback
- filesystem paths
- `data:` URLs with embedded image data
- remote `http/https` URLs

### Filesystem Images

If you do nothing, filesystem images are resolved relative to the current working directory. If you want a different base directory, pass `image_base_dir`.

```python
from simpdf import FontFace, MarkdownPdfRenderer

renderer = MarkdownPdfRenderer(
    font_directory="fonts",
    font_face=FontFace.dejavu_sans(),
    image_base_dir="docs-assets",
)

markdown_text = "![Logo](logo.png)"
pdf_bytes = renderer.render_to_bytes(markdown_text)
```

### Custom Callback

The callback receives `(alt_text, source)` and may return raw bytes, a binary stream, or a `PIL.Image.Image` when Pillow is installed. Returning `None` falls through to the built-in resolvers.

```python
from io import BytesIO
from simpdf import FontFace, MarkdownPdfRenderer

def image_callback(alt_text: str, source: str):
    if source == "custom://badge":
        return BytesIO(open("badge.png", "rb").read())
    return None

renderer = MarkdownPdfRenderer(
    font_directory="fonts",
    font_face=FontFace.dejavu_sans(),
    image_resolver=image_callback,
)
```

### Layout Behavior

- Images render as standalone block elements.
- If a paragraph mixes text and images, the renderer outputs the text and image blocks in order.
- Images inside table cells are best-effort in `0.1.1`.
  - image-only cells are rendered as images
  - mixed text+image cells fall back to text rendering using the image alt text

## Convenience Helpers

If you prefer a functional call site, `simpdf` also exports:

- `render_markdown_to_pdf_bytes(...)`
- `render_markdown_to_pdf_file(...)`

These helpers internally construct `MarkdownPdfRenderer`.

## CLI Usage

Render Markdown into PDF:

```bash
simpdf render input.md output.pdf \
  --fonts-dir ./fonts \
  --family-name DejaVuSans \
  --font-regular DejaVuSans.ttf \
  --font-bold DejaVuSans-Bold.ttf \
  --font-italic DejaVuSans-Oblique.ttf \
  --font-bold-italic DejaVuSans-BoldOblique.ttf \
  --image-base-dir ./images
```

Download DejaVu fonts:

```bash
simpdf download-dejavu ./fonts
```

If you want custom formatting from the CLI, pass a JSON file with `--options-file`.

## Examples

See [`examples/basic_render.py`](/D:/GIT/simpdf/examples/basic_render.py), [`examples/custom_font_and_style.py`](/D:/GIT/simpdf/examples/custom_font_and_style.py), [`examples/rich_markdown.py`](/D:/GIT/simpdf/examples/rich_markdown.py), [`examples/images_from_filesystem.py`](/D:/GIT/simpdf/examples/images_from_filesystem.py), and [`examples/images_custom_callback.py`](/D:/GIT/simpdf/examples/images_custom_callback.py).

## Tests

The repo now contains a pytest suite that covers:

- font config validation
- DejaVu download helper behavior
- markdown token flattening and table extraction
- image resolvers and image rendering
- PDF rendering with Cyrillic content
- formatting overrides
- CLI render and download flows

Run tests with:

```bash
pytest
```

## Compatibility Note

For older code that imported `simpdf.pdfgen`, a small compatibility wrapper is still present. The recommended API is the class-based renderer from `simpdf`.
