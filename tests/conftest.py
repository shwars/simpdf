from __future__ import annotations

import base64
from pathlib import Path

import pytest

from simpdf import FontFace, MarkdownPdfRenderer


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def fonts_dir(repo_root: Path) -> Path:
    return repo_root / "fonts"


@pytest.fixture
def dejavu_face() -> FontFace:
    return FontFace.dejavu_sans()


@pytest.fixture
def renderer(fonts_dir: Path, dejavu_face: FontFace) -> MarkdownPdfRenderer:
    return MarkdownPdfRenderer(font_directory=fonts_dir, font_face=dejavu_face)


@pytest.fixture
def sample_png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W4mQAAAAASUVORK5CYII="
    )


@pytest.fixture
def sample_png_path(tmp_path: Path, sample_png_bytes: bytes) -> Path:
    path = tmp_path / "sample.png"
    path.write_bytes(sample_png_bytes)
    return path


@pytest.fixture
def sample_png_data_url(sample_png_bytes: bytes) -> str:
    encoded = base64.b64encode(sample_png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"
