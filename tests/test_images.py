from __future__ import annotations

from io import BytesIO
from pathlib import Path

import importlib.util
import pytest

from simpdf import FontFace, MarkdownPdfRenderer
from simpdf.images import DataUrlImageResolver, FileImageResolver, HttpImageResolver, ImageDecodingError, resolve_markdown_image


def test_file_image_resolver_reads_from_base_dir(sample_png_path: Path):
    resolver = FileImageResolver(base_dir=sample_png_path.parent)
    assert resolver("alt", sample_png_path.name) == sample_png_path.read_bytes()


def test_data_url_image_resolver_decodes(sample_png_data_url: str, sample_png_bytes: bytes):
    resolver = DataUrlImageResolver()
    assert resolver("alt", sample_png_data_url) == sample_png_bytes


def test_http_image_resolver_fetches(monkeypatch, sample_png_bytes: bytes):
    class DummyResponse:
        def read(self):
            return sample_png_bytes

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("simpdf.images.urlopen", lambda url, timeout=10.0: DummyResponse())
    resolver = HttpImageResolver(timeout=3.0)
    assert resolver("alt", "https://example.com/image.png") == sample_png_bytes


def test_resolve_markdown_image_accepts_bytes(sample_png_bytes: bytes):
    image = resolve_markdown_image(lambda alt, src: sample_png_bytes, alt_text="alt", source="custom://image")
    assert image.width_px == 1
    assert image.height_px == 1


def test_resolve_markdown_image_accepts_stream(sample_png_bytes: bytes):
    image = resolve_markdown_image(lambda alt, src: BytesIO(sample_png_bytes), alt_text="alt", source="custom://image")
    assert image.data == sample_png_bytes


@pytest.mark.skipif(not importlib.util.find_spec("PIL"), reason="Pillow not installed")
def test_resolve_markdown_image_accepts_pil_image():
    from PIL import Image

    pil_image = Image.new("RGB", (2, 2), color=(255, 0, 0))
    image = resolve_markdown_image(lambda alt, src: pil_image, alt_text="alt", source="custom://image")
    assert image.width_px == 2
    assert image.height_px == 2


def test_resolve_markdown_image_rejects_bad_type():
    with pytest.raises(ImageDecodingError):
        resolve_markdown_image(lambda alt, src: object(), alt_text="alt", source="custom://image")


def test_renderer_renders_filesystem_image(fonts_dir: Path, sample_png_path: Path):
    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
        image_base_dir=sample_png_path.parent,
    )
    data = renderer.render_to_bytes("![sample](sample.png)")
    assert data[:4] == b"%PDF"


def test_renderer_renders_data_url_image(fonts_dir: Path, sample_png_data_url: str):
    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
    )
    data = renderer.render_to_bytes(f"![sample]({sample_png_data_url})")
    assert data[:4] == b"%PDF"


def test_renderer_renders_custom_callback_image(fonts_dir: Path, sample_png_bytes: bytes):
    def callback(alt_text: str, source: str):
        if source == "custom://logo":
            return sample_png_bytes
        return None

    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
        image_resolver=callback,
    )
    data = renderer.render_to_bytes("![sample](custom://logo)")
    assert data[:4] == b"%PDF"


def test_renderer_best_effort_image_only_table_cell(fonts_dir: Path, sample_png_path: Path):
    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
        image_base_dir=sample_png_path.parent,
    )
    markdown_text = "| Preview | Value |\n| --- | --- |\n| ![sample](sample.png) | 1 |"
    data = renderer.render_to_bytes(markdown_text)
    assert data[:4] == b"%PDF"


def test_renderer_falls_back_for_mixed_table_cell(fonts_dir: Path, sample_png_path: Path):
    renderer = MarkdownPdfRenderer(
        font_directory=fonts_dir,
        font_face=FontFace.dejavu_sans(),
        image_base_dir=sample_png_path.parent,
    )
    markdown_text = "| Preview | Value |\n| --- | --- |\n| Text ![sample](sample.png) | 1 |"
    data = renderer.render_to_bytes(markdown_text)
    assert data[:4] == b"%PDF"
