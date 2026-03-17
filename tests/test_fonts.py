from __future__ import annotations

from pathlib import Path

import pytest

from simpdf import DEJAVU_FONT_FILES, FontFace
from simpdf.fonts import coerce_font_face, download_dejavu_fonts, resolve_font_paths


def test_resolve_font_paths_accepts_dataclass(fonts_dir: Path):
    resolved = resolve_font_paths(fonts_dir, FontFace.dejavu_sans())
    assert resolved["regular"].name == "DejaVuSans.ttf"
    assert resolved["bold"].name == "DejaVuSans-Bold.ttf"


def test_resolve_font_paths_accepts_mapping(fonts_dir: Path):
    resolved = resolve_font_paths(
        fonts_dir,
        {
            "family": "CustomFace",
            "regular": "DejaVuSans.ttf",
            "bold": "DejaVuSans-Bold.ttf",
        },
    )
    assert resolved["regular"].exists()
    assert resolved["italic"] == resolved["regular"]


def test_resolve_font_paths_requires_regular_font(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        resolve_font_paths(
            tmp_path,
            {
                "family": "Missing",
                "regular": "Missing.ttf",
            },
        )


def test_coerce_font_face_requires_required_fields():
    with pytest.raises(ValueError):
        coerce_font_face({"family": "Broken"})


def test_download_dejavu_fonts_uses_expected_urls(monkeypatch, tmp_path: Path):
    requested_urls = []

    class DummyResponse:
        def __init__(self, payload: bytes):
            self.payload = payload

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(url, timeout=30):
        requested_urls.append(url)
        return DummyResponse(b"font-data")

    monkeypatch.setattr("simpdf.fonts.urlopen", fake_urlopen)

    downloaded = download_dejavu_fonts(tmp_path)
    assert [path.name for path in downloaded] == list(DEJAVU_FONT_FILES)
    assert requested_urls[0].endswith("/DejaVuSans.ttf")
    assert all(path.read_bytes() == b"font-data" for path in downloaded)


def test_download_dejavu_fonts_skips_existing_without_overwrite(monkeypatch, tmp_path: Path):
    existing = tmp_path / DEJAVU_FONT_FILES[0]
    existing.write_bytes(b"existing")
    requested_urls = []

    def fake_urlopen(url, timeout=30):
        requested_urls.append(url)

        class DummyResponse:
            def read(self):
                return b"downloaded"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return DummyResponse()

    monkeypatch.setattr("simpdf.fonts.urlopen", fake_urlopen)
    result = download_dejavu_fonts(tmp_path, overwrite=False)
    assert result[0].read_bytes() == b"existing"
    assert not any(url.endswith(f"/{DEJAVU_FONT_FILES[0]}") for url in requested_urls)
