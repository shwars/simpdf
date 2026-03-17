import base64
from io import BytesIO
from pathlib import Path

from simpdf import FontFace, MarkdownPdfRenderer


ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
OUTPUT = ROOT / "examples" / "images_custom_callback.pdf"

PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAHgAAAA8CAIAAAAiz+n/AAABBUlEQVR4nO3cwQnCQBBA0Y2kFmFbsY1crcGDNXi1DVtZsAhPAa+5"
    "ihJQSL6T4b+bXgKfYcIuYvccH0Xr2wHPkKE5hoYYGmJoSP/5VR0u1NMza9fj60cnGmLo/62OueHXN+YWrxMNMTTE0BBDB3gZvrmf"
    "DyWM/elWNsWJhhg63uqIr7KXBz+dM5xoiKEhqVZHC3xn4ERDDA0xNMTQEENDDA0xNMTQkFQHlupdhwwNSbU6mncdMjTE0BBDQwwN"
    "MTTE0BBDQ1IdWOo6dx2LnIOcaIihIalWR/OuQ4aOtzo299vvUJxoiKEhhoYYOsDL0L85WJATDTE0pPPv2BhONMTQEENDDF0YEyGx"
    "IFn1M8VAAAAAAElFTkSuQmCC"
)


def image_callback(alt_text: str, source: str):
    if source == "custom://badge":
        return BytesIO(base64.b64decode(PNG_BASE64))
    return None


markdown_text = """
# Custom Callback Images

![Callback badge](custom://badge)
"""

renderer = MarkdownPdfRenderer(
    font_directory=FONTS_DIR,
    font_face=FontFace.dejavu_sans(),
    image_resolver=image_callback,
)

renderer.render_to_file(markdown_text, OUTPUT)
print(f"Wrote {OUTPUT}")
