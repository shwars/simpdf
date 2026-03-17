import base64
from pathlib import Path

from simpdf import FontFace, MarkdownPdfRenderer


ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / "examples"
FONTS_DIR = ROOT / "fonts"
OUTPUT = EXAMPLES_DIR / "images_from_filesystem.pdf"
IMAGE_PATH = EXAMPLES_DIR / "filesystem_badge.png"

PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAHgAAAA8CAIAAAAiz+n/AAABBUlEQVR4nO3cwQnCQBBA0Y2kFmFbsY1crcGDNXi1DVtZsAhPAa+5"
    "ihJQSL6T4b+bXgKfYcIuYvccH0Xr2wHPkKE5hoYYGmJoSP/5VR0u1NMza9fj60cnGmLo/62OueHXN+YWrxMNMTTE0BBDB3gZvrmf"
    "DyWM/elWNsWJhhg63uqIr7KXBz+dM5xoiKEhqVZHC3xn4ERDDA0xNMTQEENDDA0xNMTQkFQHlupdhwwNSbU6mncdMjTE0BBDQwwN"
    "MTTE0BBDQ1IdWOo6dx2LnIOcaIihIalWR/OuQ4aOtzo299vvUJxoiKEhhoYYOsDL0L85WJATDTE0pPPv2BhONMTQEENDDF0YEyGx"
    "IFn1M8VAAAAAAElFTkSuQmCC"
)

IMAGE_PATH.write_bytes(base64.b64decode(PNG_BASE64))

markdown_text = """
# Filesystem Images

Below is an image resolved from the filesystem:

![Filesystem badge](filesystem_badge.png)

| Preview | Note |
| --- | --- |
| ![Cell image](filesystem_badge.png) | Image-only cell |
| Text ![ignored](filesystem_badge.png) | Mixed content falls back to text |
"""

renderer = MarkdownPdfRenderer(
    font_directory=FONTS_DIR,
    font_face=FontFace.dejavu_sans(),
    image_base_dir=EXAMPLES_DIR,
)

renderer.render_to_file(markdown_text, OUTPUT)
print(f"Wrote {OUTPUT}")
