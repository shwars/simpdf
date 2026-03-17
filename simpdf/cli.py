from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fonts import FontFace, download_dejavu_fonts
from .renderer import MarkdownPdfRenderer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simpdf", description="Render Markdown into PDF with configurable TTF fonts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="Render a Markdown file into PDF.")
    render_parser.add_argument("input_markdown", type=Path)
    render_parser.add_argument("output_pdf", type=Path)
    render_parser.add_argument("--fonts-dir", type=Path, required=True)
    render_parser.add_argument("--family-name", default="DejaVuSans")
    render_parser.add_argument("--font-regular", required=True)
    render_parser.add_argument("--font-bold")
    render_parser.add_argument("--font-italic")
    render_parser.add_argument("--font-bold-italic")
    render_parser.add_argument("--options-file", type=Path, help="Path to a JSON file with formatting options.")

    download_parser = subparsers.add_parser("download-dejavu", help="Download the DejaVu Sans font files.")
    download_parser.add_argument("target_dir", type=Path)
    download_parser.add_argument("--overwrite", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "download-dejavu":
        download_dejavu_fonts(args.target_dir, overwrite=args.overwrite)
        return 0

    options = {}
    if args.options_file:
        options = json.loads(args.options_file.read_text(encoding="utf-8"))

    renderer = MarkdownPdfRenderer(
        font_directory=args.fonts_dir,
        font_face=FontFace(
            family=args.family_name,
            regular=args.font_regular,
            bold=args.font_bold,
            italic=args.font_italic,
            bold_italic=args.font_bold_italic,
        ),
        formatting_options=options,
    )
    markdown_text = args.input_markdown.read_text(encoding="utf-8")
    renderer.render_to_file(markdown_text, args.output_pdf)
    return 0
