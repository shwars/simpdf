from __future__ import annotations

from pathlib import Path

from .fonts import FontFace
from .renderer import MarkdownPdfRenderer

_legacy_font_directory: Path | None = None
_legacy_font_face = FontFace.dejavu_sans()


def set_font_files(fonts_dir):
    global _legacy_font_directory
    _legacy_font_directory = Path(fonts_dir)


def get_font_config():
    if _legacy_font_directory is None:
        return {}
    return {
        "font_directory": str(_legacy_font_directory),
        "family": _legacy_font_face.family,
        "regular": _legacy_font_face.regular,
        "bold": _legacy_font_face.bold,
        "italic": _legacy_font_face.italic,
        "bold_italic": _legacy_font_face.bold_italic,
    }


def render_text_to_pdf_bytes(text, formatting_options=None):
    if _legacy_font_directory is None:
        raise RuntimeError("Fonts are not configured. Call set_font_files(...) first.")

    renderer = MarkdownPdfRenderer(
        font_directory=_legacy_font_directory,
        font_face=_legacy_font_face,
        formatting_options=formatting_options,
    )
    return renderer.render_to_bytes(text)
