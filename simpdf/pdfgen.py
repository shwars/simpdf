import re
from pathlib import Path

from fpdf import FPDF

_FONT_FILES = None


def set_font_files(fonts_dir):
    base = Path(fonts_dir)
    files = {
        "regular": base / "DejaVuSans.ttf",
        "bold": base / "DejaVuSans-Bold.ttf",
        "italic": base / "DejaVuSans-Oblique.ttf",
        "bold_italic": base / "DejaVuSans-BoldOblique.ttf",
        "cond_regular": base / "DejaVuSansCondensed.ttf",
        "cond_bold": base / "DejaVuSansCondensed-Bold.ttf",
        "cond_italic": base / "DejaVuSansCondensed-Oblique.ttf",
        "cond_bold_italic": base / "DejaVuSansCondensed-BoldOblique.ttf",
    }
    missing = [str(path) for path in files.values() if not path.exists()]
    if missing:
        raise RuntimeError("Missing required fonts: " + ", ".join(missing))

    global _FONT_FILES
    _FONT_FILES = {name: str(path) for name, path in files.items()}


def get_font_config():
    if _FONT_FILES is None:
        return {}
    return dict(_FONT_FILES)


def _configure_pdf_fonts(pdf):
    if _FONT_FILES is None:
        raise RuntimeError("Fonts are not configured. Call set_font_files(...) first.")

    family = "DejaVuSans"
    condensed_family = "DejaVuSansCondensed"
    pdf.add_font(family, style="", fname=_FONT_FILES["regular"])
    pdf.add_font(family, style="B", fname=_FONT_FILES["bold"])
    pdf.add_font(family, style="I", fname=_FONT_FILES["italic"])
    pdf.add_font(family, style="BI", fname=_FONT_FILES["bold_italic"])

    pdf.add_font(condensed_family, style="", fname=_FONT_FILES["cond_regular"])
    pdf.add_font(condensed_family, style="B", fname=_FONT_FILES["cond_bold"])
    pdf.add_font(condensed_family, style="I", fname=_FONT_FILES["cond_italic"])
    pdf.add_font(condensed_family, style="BI", fname=_FONT_FILES["cond_bold_italic"])
    return family


def strip_markdown_inline(value):
    text = value
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    return text


def _normalize_for_pdf(text):
    if text is None:
        return ""
    return (
        text.replace("\u00A0", " ")
        .replace("\u202F", " ")
        .replace("\u2011", "-")
        .replace("\u00AD", "")
    )


def _break_long_tokens(text, chunk=32):
    parts = re.split(r"(\s+)", text)
    out = []
    for part in parts:
        if not part or part.isspace() or len(part) <= chunk:
            out.append(part)
            continue
        wrapped = [part[i : i + chunk] for i in range(0, len(part), chunk)]
        out.append(" ".join(wrapped))
    return "".join(out)


def _pdf_multicell_markdown(pdf, h, txt):
    pdf.set_x(pdf.l_margin)
    txt = _normalize_for_pdf(txt)
    try:
        pdf.multi_cell(0, h, txt, markdown=True)
        return
    except Exception:
        pass

    plain = strip_markdown_inline(txt)
    try:
        pdf.multi_cell(0, h, plain)
    except Exception:
        pdf.multi_cell(0, h, _break_long_tokens(plain))


def _parse_markdown_row(line):
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _is_table_separator_row(cells):
    if not cells:
        return False
    for cell in cells:
        sample = cell.replace(":", "").replace("-", "").replace(" ", "")
        if sample:
            return False
        if "-" not in cell:
            return False
    return True


def _wrap_cell_text(pdf, text, max_width):
    text = _normalize_for_pdf(strip_markdown_inline(text or ""))
    if not text:
        return [""]

    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue

        words = paragraph.split()
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if pdf.get_string_width(trial) <= max_width:
                current = trial
                continue

            if current:
                lines.append(current)
                current = ""

            if pdf.get_string_width(word) <= max_width:
                current = word
                continue

            chunk = ""
            for ch in word:
                trial_chunk = chunk + ch
                if pdf.get_string_width(trial_chunk) <= max_width:
                    chunk = trial_chunk
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            current = chunk

        if current:
            lines.append(current)

    return lines or [""]


def _column_score(pdf, rows, col_idx):
    max_cell_width = 0.0
    max_token_width = 0.0
    for row in rows:
        value = _normalize_for_pdf(strip_markdown_inline(row[col_idx] if col_idx < len(row) else ""))
        if not value:
            continue
        max_cell_width = max(max_cell_width, pdf.get_string_width(value))
        for token in value.split():
            max_token_width = max(max_token_width, pdf.get_string_width(token))
    # Blend full-cell and longest-token pressure to improve readability.
    return max(1.0, max_cell_width * 0.25 + max_token_width * 0.75)


def _compute_table_col_widths(pdf, rows, usable_width):
    col_count = max((len(r) for r in rows), default=1)
    min_col_width = 24.0
    weights = [_column_score(pdf, rows, idx) for idx in range(col_count)]
    total_weight = sum(weights) or 1.0

    widths = [(w / total_weight) * usable_width for w in weights]

    # Clamp to minimums first.
    widths = [max(min_col_width, w) for w in widths]
    width_sum = sum(widths)

    # If clamping overflowed available width, shrink proportionally above min widths.
    if width_sum > usable_width:
        overflow = width_sum - usable_width
        shrinkable = [max(0.0, w - min_col_width) for w in widths]
        shrink_total = sum(shrinkable)
        if shrink_total > 0:
            for i in range(col_count):
                widths[i] -= overflow * (shrinkable[i] / shrink_total)

    # Normalize final tiny drift.
    final_sum = sum(widths)
    if final_sum != 0:
        scale = usable_width / final_sum
        widths = [w * scale for w in widths]

    return widths


def _draw_table_row(pdf, row_cells, widths, line_height, cell_padding):
    x0 = pdf.l_margin
    y0 = pdf.get_y()

    wrapped_per_cell = []
    max_lines = 1
    for idx, width in enumerate(widths):
        text = row_cells[idx] if idx < len(row_cells) else ""
        inner_width = max(1.0, width - 2 * cell_padding)
        wrapped = _wrap_cell_text(pdf, text, inner_width)
        wrapped_per_cell.append(wrapped)
        max_lines = max(max_lines, len(wrapped))

    row_height = max_lines * line_height + 2 * cell_padding

    # Caller handles page breaks. Draw borders and write wrapped lines.
    x = x0
    for col_idx, width in enumerate(widths):
        pdf.rect(x, y0, width, row_height)
        lines = wrapped_per_cell[col_idx]
        for line_idx, line in enumerate(lines):
            pdf.set_xy(x + cell_padding, y0 + cell_padding + line_idx * line_height)
            pdf.cell(max(1.0, width - 2 * cell_padding), line_height, line)
        x += width

    pdf.set_xy(x0, y0 + row_height)
    return row_height


def _render_table(pdf, font_family, table_lines):
    rows = [_parse_markdown_row(line) for line in table_lines if "|" in line]
    if not rows:
        return

    if len(rows) >= 2 and _is_table_separator_row(rows[1]):
        header = rows[0]
        body = rows[2:]
    else:
        header = rows[0]
        body = rows[1:]

    col_count = max([len(header)] + [len(r) for r in body] + [1])
    header += [""] * (col_count - len(header))
    norm_body = [r + [""] * (col_count - len(r)) for r in body]

    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font(font_family, "", 11)
    widths = _compute_table_col_widths(pdf, [header] + norm_body, usable_width)
    line_height = 6.0
    cell_padding = 1.3
    page_bottom = pdf.h - pdf.b_margin

    header_max_lines = 1
    for idx, width in enumerate(widths):
        inner_width = max(1.0, width - 2 * cell_padding)
        lines = _wrap_cell_text(pdf, header[idx], inner_width)
        header_max_lines = max(header_max_lines, len(lines))
    header_height = header_max_lines * line_height + 2 * cell_padding
    if pdf.get_y() + header_height > page_bottom:
        pdf.add_page()

    pdf.set_font(font_family, "B", 12)
    _draw_table_row(pdf, header, widths, line_height=line_height, cell_padding=cell_padding)

    pdf.set_font(font_family, "", 11)
    for row in norm_body:
        # Estimate row height for page-break decision.
        wrapped = []
        max_lines = 1
        for idx, width in enumerate(widths):
            inner_width = max(1.0, width - 2 * cell_padding)
            lines = _wrap_cell_text(pdf, row[idx], inner_width)
            wrapped.append(lines)
            max_lines = max(max_lines, len(lines))
        expected_height = max_lines * line_height + 2 * cell_padding
        if pdf.get_y() + expected_height > page_bottom:
            pdf.add_page()
            pdf.set_font(font_family, "B", 12)
            _draw_table_row(pdf, header, widths, line_height=line_height, cell_padding=cell_padding)
            pdf.set_font(font_family, "", 11)
        _draw_table_row(pdf, row, widths, line_height=line_height, cell_padding=cell_padding)
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)


def _render_markdown_to_pdf(pdf, text, font_family):
    lines = (text or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            pdf.ln(4)
            i += 1
            continue

        if "|" in stripped:
            table_block = [line]
            j = i + 1
            while j < len(lines) and "|" in lines[j].strip():
                table_block.append(lines[j])
                j += 1
            if len(table_block) >= 2:
                _render_table(pdf, font_family, table_block)
                i = j
                continue

        header_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if header_match:
            level = len(header_match.group(1))
            header_text = header_match.group(2).strip()
            header_size = max(12, 22 - (level - 1) * 2)
            pdf.set_font(font_family, "B", header_size)
            _pdf_multicell_markdown(pdf, 8, header_text)
            pdf.ln(1)
            i += 1
            continue

        pdf.set_font(font_family, "", 12)
        _pdf_multicell_markdown(pdf, 7, stripped)
        i += 1


def render_text_to_pdf_bytes(text):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    font_family = _configure_pdf_fonts(pdf)
    _render_markdown_to_pdf(pdf, text, font_family)
    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1")
    if isinstance(output, bytearray):
        return bytes(output)
    return output
