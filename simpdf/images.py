from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO, IOBase
from pathlib import Path
from typing import Callable
from urllib.parse import unquote_to_bytes, urlparse
from urllib.request import urlopen

from fpdf.image_parsing import get_img_info

try:
    from PIL import Image as PILImageModule
except ImportError:  # pragma: no cover - optional dependency
    PILImageModule = None


class ImageResolutionError(RuntimeError):
    pass


class ImageDecodingError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedImage:
    alt_text: str
    source: str
    data: bytes
    width_px: int
    height_px: int
    link: str | None = None


class FileImageResolver:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else None

    def __call__(self, alt_text: str, source: str):
        if source.startswith(("data:", "http://", "https://")):
            return None
        path = Path(source)
        if not path.is_absolute():
            path = (self.base_dir or Path.cwd()) / path
        if not path.exists():
            return None
        return path.read_bytes()


class DataUrlImageResolver:
    def __call__(self, alt_text: str, source: str):
        if not source.startswith("data:"):
            return None

        header, _, payload = source.partition(",")
        if not payload:
            raise ImageDecodingError("Malformed data URL for markdown image")
        if not header.startswith("data:image/"):
            raise ImageDecodingError("Only image data URLs are supported")

        if ";base64" in header:
            return base64.b64decode(payload)
        return unquote_to_bytes(payload)


class HttpImageResolver:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def __call__(self, alt_text: str, source: str):
        parsed = urlparse(source)
        if parsed.scheme not in {"http", "https"}:
            return None
        with urlopen(source, timeout=self.timeout) as response:
            return response.read()


class ChainImageResolver:
    def __init__(self, resolvers: list[Callable[[str, str], object | None]]) -> None:
        self.resolvers = resolvers

    def __call__(self, alt_text: str, source: str):
        for resolver in self.resolvers:
            result = resolver(alt_text, source)
            if result is not None:
                return result
        return None


def build_default_image_resolver(
    *,
    user_resolver: Callable[[str, str], object | None] | None = None,
    base_dir: str | Path | None = None,
) -> ChainImageResolver:
    resolvers: list[Callable[[str, str], object | None]] = []
    if user_resolver is not None:
        resolvers.append(user_resolver)
    resolvers.extend(
        [
            DataUrlImageResolver(),
            FileImageResolver(base_dir=base_dir),
            HttpImageResolver(),
        ]
    )
    return ChainImageResolver(resolvers)


def resolve_markdown_image(
    resolver: Callable[[str, str], object | None],
    *,
    alt_text: str,
    source: str,
) -> ResolvedImage:
    result = resolver(alt_text, source)
    if result is None:
        raise ImageResolutionError(f"Unable to resolve markdown image source: {source}")
    image_bytes = _coerce_image_bytes(result)
    try:
        info = get_img_info(BytesIO(image_bytes))
    except Exception as exc:  # pragma: no cover - exercised by tests via public API
        raise ImageDecodingError(f"Unable to decode markdown image source: {source}") from exc
    link = source if source.startswith(("http://", "https://")) else None
    return ResolvedImage(
        alt_text=alt_text,
        source=source,
        data=image_bytes,
        width_px=info["w"],
        height_px=info["h"],
        link=link,
    )


def _coerce_image_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, BytesIO):
        return value.getvalue()
    if isinstance(value, IOBase):
        position = value.tell() if value.seekable() else None
        data = value.read()
        if position is not None:
            value.seek(position)
        if not isinstance(data, (bytes, bytearray)):
            raise ImageDecodingError("Image streams must produce bytes")
        return bytes(data)
    if PILImageModule is not None and isinstance(value, PILImageModule.Image):
        buffer = BytesIO()
        value.save(buffer, format="PNG")
        return buffer.getvalue()
    raise ImageDecodingError(
        "Unsupported image callback return type. Expected bytes, a binary stream, or PIL.Image.Image."
    )
