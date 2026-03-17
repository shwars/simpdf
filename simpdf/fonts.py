from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.request import urlopen


DEJAVU_BASE_URL = "https://github.com/shwars/simpdf/raw/refs/heads/main/fonts"
DEJAVU_FONT_FILES = (
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSans-Oblique.ttf",
    "DejaVuSans-BoldOblique.ttf",
    "DejaVuSansCondensed.ttf",
    "DejaVuSansCondensed-Bold.ttf",
    "DejaVuSansCondensed-Oblique.ttf",
    "DejaVuSansCondensed-BoldOblique.ttf",
)


@dataclass(frozen=True)
class FontFace:
    family: str
    regular: str
    bold: str | None = None
    italic: str | None = None
    bold_italic: str | None = None

    @classmethod
    def dejavu_sans(cls) -> "FontFace":
        return cls(
            family="DejaVuSans",
            regular="DejaVuSans.ttf",
            bold="DejaVuSans-Bold.ttf",
            italic="DejaVuSans-Oblique.ttf",
            bold_italic="DejaVuSans-BoldOblique.ttf",
        )


def coerce_font_face(font_face: FontFace | Mapping[str, str]) -> FontFace:
    if isinstance(font_face, FontFace):
        return font_face

    try:
        family = font_face["family"]
        regular = font_face["regular"]
    except KeyError as exc:
        raise ValueError(f"Missing required font face field: {exc.args[0]}") from exc

    return FontFace(
        family=family,
        regular=regular,
        bold=font_face.get("bold"),
        italic=font_face.get("italic"),
        bold_italic=font_face.get("bold_italic"),
    )


def resolve_font_paths(font_directory: str | Path, font_face: FontFace | Mapping[str, str]) -> dict[str, Path]:
    directory = Path(font_directory)
    face = coerce_font_face(font_face)
    if not directory.exists():
        raise FileNotFoundError(f"Font directory does not exist: {directory}")

    regular = _resolve_path(directory, face.regular)
    bold = _resolve_path(directory, face.bold) if face.bold else regular
    italic = _resolve_path(directory, face.italic) if face.italic else regular
    bold_italic = _resolve_path(directory, face.bold_italic) if face.bold_italic else bold

    missing = [path for path in (regular, bold, italic, bold_italic) if not path.exists()]
    if missing:
        message = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing required font files: {message}")

    return {
        "regular": regular,
        "bold": bold,
        "italic": italic,
        "bold_italic": bold_italic,
    }


def register_font_family(pdf, font_directory: str | Path, font_face: FontFace | Mapping[str, str]) -> str:
    face = coerce_font_face(font_face)
    resolved = resolve_font_paths(font_directory, face)
    pdf.add_font(face.family, style="", fname=str(resolved["regular"]))
    pdf.add_font(face.family, style="B", fname=str(resolved["bold"]))
    pdf.add_font(face.family, style="I", fname=str(resolved["italic"]))
    pdf.add_font(face.family, style="BI", fname=str(resolved["bold_italic"]))
    return face.family


def download_dejavu_fonts(
    target_dir: str | Path,
    *,
    overwrite: bool = False,
    timeout: int = 30,
) -> list[Path]:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for filename in DEJAVU_FONT_FILES:
        destination = target / filename
        if destination.exists() and not overwrite:
            downloaded.append(destination)
            continue

        url = f"{DEJAVU_BASE_URL}/{filename}"
        with urlopen(url, timeout=timeout) as response:
            destination.write_bytes(response.read())
        downloaded.append(destination)

    return downloaded


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path
