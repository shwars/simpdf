from __future__ import annotations

import json
from pathlib import Path

from simpdf.cli import main


def test_cli_render_command(fonts_dir: Path, tmp_path: Path):
    input_markdown = tmp_path / "input.md"
    output_pdf = tmp_path / "output.pdf"
    options_file = tmp_path / "options.json"

    input_markdown.write_text("# CLI\n\nПривет from CLI.", encoding="utf-8")
    options_file.write_text(json.dumps({"headings": {"sizes": {"1": 24}}}), encoding="utf-8")

    exit_code = main(
        [
            "render",
            str(input_markdown),
            str(output_pdf),
            "--fonts-dir",
            str(fonts_dir),
            "--family-name",
            "DejaVuSans",
            "--font-regular",
            "DejaVuSans.ttf",
            "--font-bold",
            "DejaVuSans-Bold.ttf",
            "--font-italic",
            "DejaVuSans-Oblique.ttf",
            "--font-bold-italic",
            "DejaVuSans-BoldOblique.ttf",
            "--options-file",
            str(options_file),
        ]
    )

    assert exit_code == 0
    assert output_pdf.exists()
    assert output_pdf.read_bytes()[:4] == b"%PDF"


def test_cli_download_command(monkeypatch, tmp_path: Path):
    called = {}

    def fake_download(target_dir, overwrite=False, timeout=30):
        called["target_dir"] = Path(target_dir)
        called["overwrite"] = overwrite
        return []

    monkeypatch.setattr("simpdf.cli.download_dejavu_fonts", fake_download)
    exit_code = main(["download-dejavu", str(tmp_path), "--overwrite"])

    assert exit_code == 0
    assert called["target_dir"] == tmp_path
    assert called["overwrite"] is True
