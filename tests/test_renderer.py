from __future__ import annotations

from pathlib import Path

from simpdf import FontFace, MarkdownPdfRenderer, render_markdown_to_pdf_bytes, render_markdown_to_pdf_file


def assert_pdf_bytes(data: bytes):
    assert isinstance(data, (bytes, bytearray))
    assert data[:4] == b"%PDF"
    assert len(data) > 800


def test_renderer_outputs_pdf_bytes(renderer: MarkdownPdfRenderer):
    data = renderer.render_to_bytes("# Header\n\nПривет, мир.")
    assert_pdf_bytes(data)


def test_renderer_supports_richer_markdown(renderer: MarkdownPdfRenderer):
    markdown_text = """# Заголовок

Параграф с [ссылкой](https://example.com), **жирным**, *курсивом* и `кодом`.

> Цитата на русском.

1. Первый пункт
2. Второй пункт

| Колонка | Значение |
| --- | --- |
| Один | 1 |
| Два | 2 |

---

```python
print("hello")
```
"""
    data = renderer.render_to_bytes(markdown_text)
    assert_pdf_bytes(data)


def test_renderer_allows_heading_size_overrides(fonts_dir: Path):
    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
        formatting_options={"headings": {"sizes": {1: 28}}},
    )
    data = renderer.render_to_bytes("# Big heading")
    assert_pdf_bytes(data)


def test_renderer_supports_regular_only_font_config(fonts_dir: Path):
    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace(
            family="SingleStyleFace",
            regular="DejaVuSans.ttf",
        ),
    )
    data = renderer.render_to_bytes("Простой текст без дополнительных начертаний.")
    assert_pdf_bytes(data)


def test_renderer_normalizes_problematic_unicode_spaces(renderer: MarkdownPdfRenderer):
    data = renderer.render_to_bytes("Привет\u00A0мир\u202Fс\u2011переносом\u00AD.")
    assert_pdf_bytes(data)


def test_convenience_render_helpers(fonts_dir: Path, tmp_path: Path):
    pdf_bytes = render_markdown_to_pdf_bytes(
        "Hello from helper",
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
    )
    assert_pdf_bytes(pdf_bytes)

    output_path = tmp_path / "helper.pdf"
    render_markdown_to_pdf_file(
        "Hello file helper",
        output_path,
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
    )
    assert output_path.exists()
    assert output_path.read_bytes()[:4] == b"%PDF"
