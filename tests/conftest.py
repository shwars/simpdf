from __future__ import annotations

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
