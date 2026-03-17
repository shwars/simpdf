from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
import re
from typing import Mapping

from fpdf import FPDF

from .fonts import FontFace, coerce_font_face, register_font_family
from .images import FileImageResolver, build_default_image_resolver, resolve_markdown_image
from .markdown import InlineFragment, TableCellContent, create_markdown_parser, inline_fragments_from_node, paragraph_elements_from_node, parse_markdown_tree, table_rows_from_node
from .options import merge_formatting_options


class MarkdownPdfRenderer:
    def __init__(
        self,
        font_directory: str | Path,
        font_face: FontFace | Mapping[str, str],
        formatting_options: dict | None = None,
        image_resolver=None,
        image_base_dir: str | Path | None = None,
    ) -> None:
        self.font_directory = Path(font_directory)
        self.font_face = coerce_font_face(font_face)
        self.options = merge_formatting_options(formatting_options)
        self.parser = create_markdown_parser()
        self.image_base_dir = Path(image_base_dir) if image_base_dir is not None else None
        self.file_image_resolver = FileImageResolver(base_dir=self.image_base_dir)
        self.image_resolver = build_default_image_resolver(
            user_resolver=image_resolver,
            base_dir=self.image_base_dir,
        )
        self._image_cache: dict[str, object] = {}

    def render_to_bytes(self, markdown_text: str) -> bytes:
        pdf = self._create_pdf()
        font_family = register_font_family(pdf, self.font_directory, self.font_face)
        self._render_tree(pdf, parse_markdown_tree(markdown_text, self.parser), font_family)
        output = pdf.output()
        if isinstance(output, str):
            return output.encode("latin-1")
        if isinstance(output, bytearray):
            return bytes(output)
        return output

    def render_to_file(self, markdown_text: str, output_path: str | Path) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.render_to_bytes(markdown_text))
        return destination

    def _create_pdf(self) -> FPDF:
        page_options = self.options["page"]
        margins = page_options["margins"]
        pdf = FPDF(
            orientation=page_options["orientation"],
            format=page_options["format"],
        )
        pdf.set_margins(margins["left"], margins["top"], margins["right"])
        pdf.set_auto_page_break(auto=True, margin=margins["bottom"])
        pdf.add_page()
        return pdf

    def _render_tree(self, pdf: FPDF, tree, font_family: str) -> None:
        for child in tree.children or []:
            self._render_block(pdf, child, font_family, list_depth=0)

    def _render_block(self, pdf: FPDF, node, font_family: str, *, list_depth: int) -> None:
        if node.type == "heading":
            self._render_heading(pdf, node, font_family)
            return
        if node.type == "paragraph":
            self._render_paragraph(pdf, node, font_family)
            return
        if node.type in {"bullet_list", "ordered_list"}:
            self._render_list(pdf, node, font_family, list_depth=list_depth)
            return
        if node.type == "blockquote":
            self._render_blockquote(pdf, node, font_family, list_depth=list_depth)
            return
        if node.type == "table":
            self._render_table(pdf, node, font_family)
            return
        if node.type == "fence":
            self._render_code_block(pdf, node, font_family)
            return
        if node.type == "hr":
            self._render_thematic_break(pdf)
            return
        for child in node.children or []:
            self._render_block(pdf, child, font_family, list_depth=list_depth)

    def _render_heading(self, pdf: FPDF, node, font_family: str) -> None:
        level = min(6, max(1, int(node.tag[1:])))
        heading_options = self.options["headings"]
        if pdf.get_y() > pdf.t_margin:
            pdf.ln(heading_options["spacing_before"].get(level, 1.5))
        self._write_fragments(
            pdf,
            self._inline_fragments_for_first_child(node),
            font_family=font_family,
            font_size=heading_options["sizes"].get(level, 12),
            line_height_multiplier=heading_options["line_height"],
            force_bold=True,
        )
        pdf.ln(heading_options["spacing_after"].get(level, 2.0))

    def _render_paragraph(self, pdf: FPDF, node, font_family: str) -> None:
        if not node.children:
            pdf.ln(self.options["paragraph"]["spacing_after"])
            return

        rendered_any = False
        elements = paragraph_elements_from_node(node.children[0])
        for element in elements:
            if element.is_image:
                self._render_block_image(pdf, element.image)
                rendered_any = True
                continue
            if element.fragments:
                self._write_fragments(
                    pdf,
                    list(element.fragments),
                    font_family=font_family,
                    font_size=self.options["text"]["font_size"],
                    line_height_multiplier=self.options["text"]["line_height"],
                )
                rendered_any = True
        if rendered_any and elements and not elements[-1].is_image:
            pdf.ln(self.options["paragraph"]["spacing_after"])

    def _render_list(self, pdf: FPDF, node, font_family: str, *, list_depth: int) -> None:
        list_options = self.options["lists"]
        start = int(node.attrs.get("start", 1))
        for index, item in enumerate(node.children or []):
            prefix = f"{list_options['bullet']} " if node.type == "bullet_list" else f"{start + index}. "
            self._render_list_item(pdf, item, font_family, prefix=prefix, list_depth=list_depth)
        if node.children:
            pdf.ln(list_options["block_spacing_after"])

    def _render_list_item(self, pdf: FPDF, node, font_family: str, *, prefix: str, list_depth: int) -> None:
        list_options = self.options["lists"]
        base_left = pdf.l_margin
        indent = list_options["indent"] * (list_depth + 1)
        prefix_width = pdf.get_string_width(prefix) + 1.0
        body_left = base_left + indent + prefix_width
        child_blocks = list(node.children or [])

        rendered_first = False
        first_block = child_blocks[0] if child_blocks else None
        if first_block and first_block.type == "paragraph":
            self._write_fragments(
                pdf,
                [InlineFragment(prefix)] + self._inline_fragments_for_first_child(first_block),
                font_family=font_family,
                font_size=self.options["text"]["font_size"],
                line_height_multiplier=self.options["text"]["line_height"],
                left_margin=base_left + indent,
                hanging_left=body_left,
            )
            pdf.ln(list_options["item_spacing_after"])
            rendered_first = True

        with self._temporary_margins(pdf, left=body_left, right=pdf.r_margin):
            for child in child_blocks[1 if rendered_first else 0 :]:
                if not rendered_first:
                    self._write_fragments(
                        pdf,
                        [InlineFragment(prefix)],
                        font_family=font_family,
                        font_size=self.options["text"]["font_size"],
                        line_height_multiplier=self.options["text"]["line_height"],
                        left_margin=base_left + indent,
                    )
                    rendered_first = True
                self._render_block(pdf, child, font_family, list_depth=list_depth + 1)

    def _render_blockquote(self, pdf: FPDF, node, font_family: str, *, list_depth: int) -> None:
        quote_options = self.options["blockquote"]
        start_page = pdf.page_no()
        start_y = pdf.get_y()
        bar_x = pdf.l_margin
        content_left = pdf.l_margin + quote_options["indent"]
        pdf.set_text_color(*quote_options["text_color"])
        with self._temporary_margins(pdf, left=content_left, right=pdf.r_margin):
            for child in node.children or []:
                self._render_block(pdf, child, font_family, list_depth=list_depth)
        pdf.set_text_color(*self.options["text"]["color"])
        end_y = pdf.get_y()
        if pdf.page_no() == start_page and end_y > start_y:
            pdf.set_draw_color(*quote_options["text_color"])
            pdf.set_line_width(quote_options["bar_width"])
            x = bar_x + (quote_options["bar_gap"] / 2.0)
            pdf.line(x, start_y, x, end_y)
            pdf.set_draw_color(0, 0, 0)
        pdf.ln(quote_options["spacing_after"])

    def _render_code_block(self, pdf: FPDF, node, font_family: str) -> None:
        code_options = self.options["code_block"]
        font_size = code_options["font_size"]
        line_height = code_options["line_height"]
        padding = code_options["padding"]
        text = self._normalize_for_pdf(node.content.rstrip("\n"))

        usable_width = pdf.w - pdf.l_margin - pdf.r_margin
        lines = text.splitlines() or [""]
        height = (len(lines) * line_height) + (2 * padding)
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()

        start_x = pdf.l_margin
        start_y = pdf.get_y()
        pdf.set_fill_color(*code_options["background_color"])
        pdf.rect(start_x, start_y, usable_width, height, style="F")
        pdf.set_xy(start_x + padding, start_y + padding)
        pdf.set_font(font_family, "", font_size)
        pdf.set_text_color(*code_options["text_color"])
        pdf.multi_cell(max(1.0, usable_width - (2 * padding)), line_height, text)
        pdf.set_text_color(*self.options["text"]["color"])
        pdf.set_x(pdf.l_margin)
        pdf.ln(code_options["spacing_after"])

    def _render_thematic_break(self, pdf: FPDF) -> None:
        rule_options = self.options["thematic_break"]
        pdf.ln(rule_options["spacing_before"])
        y = pdf.get_y()
        pdf.set_draw_color(*rule_options["color"])
        pdf.set_line_width(rule_options["width"])
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.set_draw_color(0, 0, 0)
        pdf.ln(rule_options["spacing_after"])

    def _render_table(self, pdf: FPDF, node, font_family: str) -> None:
        header, body = table_rows_from_node(node)
        if not header and not body:
            return

        table_options = self.options["table"]
        col_count = max([len(header)] + [len(row) for row in body] + [1])
        normalized_header = header + [self._empty_table_cell()] * (col_count - len(header))
        normalized_body = [row + [self._empty_table_cell()] * (col_count - len(row)) for row in body]
        usable_width = pdf.w - pdf.l_margin - pdf.r_margin

        pdf.set_font(font_family, "", table_options["font_size"])
        widths = self._compute_table_col_widths(pdf, [normalized_header] + normalized_body, usable_width, table_options["min_col_width"])
        self._draw_table_header(pdf, font_family, normalized_header, widths)
        pdf.set_font(font_family, "", table_options["font_size"])
        for row in normalized_body:
            expected_height = self._estimate_row_height(pdf, row, widths)
            if pdf.get_y() + expected_height > pdf.h - pdf.b_margin:
                pdf.add_page()
                self._draw_table_header(pdf, font_family, normalized_header, widths)
                pdf.set_font(font_family, "", table_options["font_size"])
            self._draw_table_row(pdf, row, widths)

        pdf.ln(table_options["spacing_after"])
        pdf.set_x(pdf.l_margin)

    def _draw_table_header(self, pdf: FPDF, font_family: str, header: list, widths: list[float]) -> None:
        table_options = self.options["table"]
        pdf.set_font(font_family, "B", table_options["heading_font_size"])
        expected_height = self._estimate_row_height(pdf, header, widths)
        if pdf.get_y() + expected_height > pdf.h - pdf.b_margin:
            pdf.add_page()
        self._draw_table_row(pdf, header, widths)

    def _draw_table_row(self, pdf: FPDF, row: list, widths: list[float]) -> float:
        table_options = self.options["table"]
        line_height = table_options["line_height"]
        cell_padding = table_options["cell_padding"]
        x0 = pdf.l_margin
        y0 = pdf.get_y()

        prepared_cells = []
        max_height = line_height + (2 * cell_padding)
        for index, width in enumerate(widths):
            cell = row[index] if index < len(row) else self._empty_table_cell()
            prepared = self._prepare_table_cell(pdf, cell, max(1.0, width - (2 * cell_padding)))
            prepared_cells.append(prepared)
            max_height = max(max_height, prepared["height"])

        row_height = max_height
        x = x0
        for index, width in enumerate(widths):
            pdf.rect(x, y0, width, row_height)
            prepared = prepared_cells[index]
            pdf.set_xy(x + cell_padding, y0 + cell_padding)
            if prepared["kind"] == "image":
                image_y = y0 + ((row_height - prepared["height"]) / 2.0) + cell_padding
                pdf.image(
                    prepared["stream"],
                    x=x + cell_padding,
                    y=image_y,
                    w=prepared["width"],
                    h=prepared["image_height"],
                    keep_aspect_ratio=True,
                    alt_text=prepared["image"].alt_text,
                    link=prepared["image"].link or "",
                )
            else:
                pdf.multi_cell(max(1.0, width - (2 * cell_padding)), line_height, "\n".join(prepared["lines"]))
            x += width
            pdf.set_xy(x, y0)

        pdf.set_xy(x0, y0 + row_height)
        return row_height

    def _estimate_row_height(self, pdf: FPDF, row: list, widths: list[float]) -> float:
        table_options = self.options["table"]
        cell_padding = table_options["cell_padding"]
        line_height = table_options["line_height"]
        max_height = line_height + (2 * cell_padding)
        for index, width in enumerate(widths):
            cell = row[index] if index < len(row) else self._empty_table_cell()
            prepared = self._prepare_table_cell(pdf, cell, max(1.0, width - (2 * cell_padding)))
            max_height = max(max_height, prepared["height"])
        return max_height

    def _compute_table_col_widths(self, pdf: FPDF, rows: list[list], usable_width: float, min_col_width: float) -> list[float]:
        col_count = max((len(row) for row in rows), default=1)
        weights = [self._column_score(pdf, rows, index) for index in range(col_count)]
        total_weight = sum(weights) or 1.0
        widths = [(weight / total_weight) * usable_width for weight in weights]
        widths = [max(min_col_width, width) for width in widths]
        width_sum = sum(widths)

        if width_sum > usable_width:
            overflow = width_sum - usable_width
            shrinkable = [max(0.0, width - min_col_width) for width in widths]
            shrink_total = sum(shrinkable)
            if shrink_total > 0:
                widths = [
                    width - overflow * (shrinkable[index] / shrink_total)
                    for index, width in enumerate(widths)
                ]

        final_sum = sum(widths)
        if final_sum:
            scale = usable_width / final_sum
            widths = [width * scale for width in widths]
        return widths

    def _column_score(self, pdf: FPDF, rows: list[list], col_index: int) -> float:
        max_cell_width = 0.0
        max_token_width = 0.0
        for row in rows:
            cell = row[col_index] if col_index < len(row) else self._empty_table_cell()
            value = self._normalize_for_pdf(cell.text)
            if not value and cell.image is None:
                continue
            max_cell_width = max(max_cell_width, pdf.get_string_width(value))
            for token in value.split():
                max_token_width = max(max_token_width, pdf.get_string_width(token))
            if cell.image is not None and not cell.has_mixed_content:
                resolved = self._resolve_image(cell.image)
                max_cell_width = max(max_cell_width, self._default_image_width_mm(resolved))
        return max(1.0, (max_cell_width * 0.25) + (max_token_width * 0.75))

    def _empty_table_cell(self) -> TableCellContent:
        return TableCellContent(text="")

    def _prepare_table_cell(self, pdf: FPDF, cell: TableCellContent, max_width: float) -> dict:
        table_options = self.options["table"]
        cell_padding = table_options["cell_padding"]
        if cell.image is not None and not cell.has_mixed_content:
            resolved = self._resolve_image(cell.image)
            image_width, image_height = self._fit_image(
                resolved,
                max_width=max_width,
                max_height=self.options["images"]["table_cell_max_height"],
            )
            return {
                "kind": "image",
                "image": resolved,
                "stream": self._image_stream(resolved),
                "width": image_width,
                "image_height": image_height,
                "height": image_height + (2 * cell_padding),
            }

        lines = self._wrap_cell_text(pdf, cell.text, max_width)
        return {
            "kind": "text",
            "lines": lines,
            "height": (len(lines) * table_options["line_height"]) + (2 * cell_padding),
        }

    def _render_block_image(self, pdf: FPDF, markdown_image) -> None:
        image_options = self.options["images"]
        resolved = self._resolve_image(markdown_image)
        width, height = self._fit_image(
            resolved,
            max_width=image_options["max_width"],
            max_height=image_options["max_height"],
        )
        total_height = height + image_options["spacing_before"] + image_options["spacing_after"]
        if pdf.get_y() + total_height > pdf.h - pdf.b_margin:
            pdf.add_page()

        pdf.ln(image_options["spacing_before"])
        x = pdf.l_margin
        if image_options["align"] == "center":
            x = pdf.l_margin + ((pdf.w - pdf.l_margin - pdf.r_margin - width) / 2.0)
        pdf.image(
            self._image_stream(resolved),
            x=x,
            y=pdf.get_y(),
            w=width,
            h=height,
            keep_aspect_ratio=True,
            alt_text=resolved.alt_text,
            link=resolved.link or "",
        )
        pdf.set_y(pdf.get_y() + height)
        pdf.ln(image_options["spacing_after"])

    def _resolve_image(self, markdown_image):
        cached = self._image_cache.get(markdown_image.source)
        if cached is not None:
            return cached.__class__(
                alt_text=markdown_image.alt_text,
                source=cached.source,
                data=cached.data,
                width_px=cached.width_px,
                height_px=cached.height_px,
                link=cached.link,
            )
        resolved = resolve_markdown_image(
            self.image_resolver,
            alt_text=markdown_image.alt_text,
            source=markdown_image.source,
        )
        self._image_cache[markdown_image.source] = resolved
        return resolved

    def _fit_image(self, resolved_image, *, max_width: float, max_height: float) -> tuple[float, float]:
        base_width = self._default_image_width_mm(resolved_image)
        base_height = self._default_image_height_mm(resolved_image)
        width_scale = max_width / base_width if base_width else 1.0
        height_scale = max_height / base_height if base_height else 1.0
        scale = min(1.0, width_scale, height_scale)
        return max(1.0, base_width * scale), max(1.0, base_height * scale)

    def _default_image_width_mm(self, resolved_image) -> float:
        return resolved_image.width_px * 25.4 / 72.0

    def _default_image_height_mm(self, resolved_image) -> float:
        return resolved_image.height_px * 25.4 / 72.0

    def _image_stream(self, resolved_image) -> BytesIO:
        return BytesIO(resolved_image.data)

    def _wrap_cell_text(self, pdf: FPDF, text: str, max_width: float) -> list[str]:
        value = self._normalize_for_pdf(text)
        if not value:
            return [""]

        lines: list[str] = []
        for paragraph in value.splitlines():
            if not paragraph.strip():
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
                for character in word:
                    trial_chunk = chunk + character
                    if pdf.get_string_width(trial_chunk) <= max_width:
                        chunk = trial_chunk
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = character
                current = chunk

            if current:
                lines.append(current)

        return lines or [""]

    def _write_fragments(
        self,
        pdf: FPDF,
        fragments: list[InlineFragment],
        *,
        font_family: str,
        font_size: float,
        line_height_multiplier: float,
        left_margin: float | None = None,
        hanging_left: float | None = None,
        force_bold: bool = False,
    ) -> None:
        line_height = round(font_size * line_height_multiplier / 2.5, 2)
        current_left = left_margin if left_margin is not None else pdf.l_margin
        current_hanging = hanging_left if hanging_left is not None else current_left
        lines = self._layout_fragments_to_lines(
            pdf,
            fragments,
            font_family=font_family,
            font_size=font_size,
            first_left=current_left,
            rest_left=current_hanging,
            force_bold=force_bold,
        )

        for index, line in enumerate(lines):
            line_left = current_left if index == 0 else current_hanging
            self._ensure_space_for_line(pdf, line_height)
            pdf.set_xy(line_left, pdf.get_y())
            current_x = line_left
            for fragment in line:
                text = fragment.text
                if not text:
                    continue
                style = self._fragment_style(fragment, force_bold=force_bold)
                text_color = self._fragment_text_color(fragment)
                pdf.set_font(font_family, style, font_size)
                pdf.set_text_color(*text_color)
                width = pdf.get_string_width(text)
                pdf.set_xy(current_x, pdf.get_y())
                pdf.cell(width, line_height, text, link=fragment.link or "")
                current_x += width
            pdf.set_xy(line_left, pdf.get_y() + line_height)
        pdf.set_text_color(*self.options["text"]["color"])

    def _layout_fragments_to_lines(
        self,
        pdf: FPDF,
        fragments: list[InlineFragment],
        *,
        font_family: str,
        font_size: float,
        first_left: float,
        rest_left: float,
        force_bold: bool,
    ) -> list[list[InlineFragment]]:
        lines: list[list[InlineFragment]] = []
        current_line: list[InlineFragment] = []
        current_width = 0.0
        line_index = 0

        def line_left() -> float:
            return first_left if line_index == 0 else rest_left

        def available_width() -> float:
            return max(1.0, pdf.w - pdf.r_margin - line_left())

        def flush_line() -> None:
            nonlocal current_line, current_width, line_index
            trimmed = self._trim_trailing_whitespace(current_line)
            lines.append(trimmed)
            current_line = []
            current_width = 0.0
            line_index += 1

        for fragment in fragments:
            normalized_text = self._normalize_for_pdf(fragment.text)
            if not normalized_text:
                continue

            pieces = normalized_text.split("\n")
            for piece_index, piece in enumerate(pieces):
                if piece:
                    for token in self._split_fragment_tokens(fragment, piece):
                        token = self._drop_leading_whitespace_if_needed(token, current_width)
                        if not token.text:
                            continue

                        token_width = self._fragment_width(pdf, token, font_family, font_size, force_bold=force_bold)
                        if current_width + token_width <= available_width():
                            current_line.append(token)
                            current_width += token_width
                            continue

                        if current_line:
                            flush_line()
                            token = self._drop_leading_whitespace_if_needed(token, current_width)
                            if not token.text:
                                continue
                            token_width = self._fragment_width(pdf, token, font_family, font_size, force_bold=force_bold)

                        if token_width <= available_width():
                            current_line.append(token)
                            current_width += token_width
                            continue

                        for chunk in self._split_fragment_to_fit(
                            pdf,
                            token,
                            font_family=font_family,
                            font_size=font_size,
                            max_width=available_width(),
                            force_bold=force_bold,
                        ):
                            chunk = self._drop_leading_whitespace_if_needed(chunk, current_width)
                            if not chunk.text:
                                continue
                            chunk_width = self._fragment_width(pdf, chunk, font_family, font_size, force_bold=force_bold)
                            if current_width and current_width + chunk_width > available_width():
                                flush_line()
                                chunk = self._drop_leading_whitespace_if_needed(chunk, current_width)
                                if not chunk.text:
                                    continue
                                chunk_width = self._fragment_width(pdf, chunk, font_family, font_size, force_bold=force_bold)
                            current_line.append(chunk)
                            current_width += chunk_width

                if piece_index < len(pieces) - 1:
                    flush_line()

        if current_line or not lines:
            lines.append(self._trim_trailing_whitespace(current_line))
        return lines

    def _split_fragment_tokens(self, fragment: InlineFragment, text: str) -> list[InlineFragment]:
        tokens = re.findall(r"\S+\s*|\s+", text)
        return [self._fragment_with_text(fragment, token) for token in tokens]

    def _split_fragment_to_fit(
        self,
        pdf: FPDF,
        fragment: InlineFragment,
        *,
        font_family: str,
        font_size: float,
        max_width: float,
        force_bold: bool,
    ) -> list[InlineFragment]:
        chunks: list[InlineFragment] = []
        current = ""
        for character in fragment.text:
            trial = current + character
            if current and self._fragment_width(
                pdf,
                self._fragment_with_text(fragment, trial),
                font_family,
                font_size,
                force_bold=force_bold,
            ) > max_width:
                chunks.append(self._fragment_with_text(fragment, current))
                current = character
            else:
                current = trial
        if current:
            chunks.append(self._fragment_with_text(fragment, current))
        return chunks or [fragment]

    def _fragment_width(
        self,
        pdf: FPDF,
        fragment: InlineFragment,
        font_family: str,
        font_size: float,
        *,
        force_bold: bool,
    ) -> float:
        pdf.set_font(font_family, self._fragment_style(fragment, force_bold=force_bold), font_size)
        return pdf.get_string_width(fragment.text)

    def _fragment_style(self, fragment: InlineFragment, *, force_bold: bool) -> str:
        style_parts = []
        if force_bold or fragment.bold:
            style_parts.append("B")
        if fragment.italic:
            style_parts.append("I")
        if fragment.link and self.options["links"]["underline"]:
            style_parts.append("U")
        return "".join(style_parts)

    def _fragment_text_color(self, fragment: InlineFragment) -> tuple[int, int, int]:
        if fragment.link:
            return self.options["links"]["color"]
        if fragment.code:
            return self.options["inline_code"]["text_color"]
        return self.options["text"]["color"]

    def _trim_trailing_whitespace(self, fragments: list[InlineFragment]) -> list[InlineFragment]:
        if not fragments:
            return []
        trimmed = list(fragments)
        while trimmed and not trimmed[-1].text.strip():
            trimmed.pop()
        if trimmed and trimmed[-1].text != trimmed[-1].text.rstrip():
            trimmed[-1] = self._fragment_with_text(trimmed[-1], trimmed[-1].text.rstrip())
        return trimmed

    def _drop_leading_whitespace_if_needed(self, fragment: InlineFragment, current_width: float) -> InlineFragment:
        if current_width > 0:
            return fragment
        stripped = fragment.text.lstrip()
        if stripped == fragment.text:
            return fragment
        return self._fragment_with_text(fragment, stripped)

    def _fragment_with_text(self, fragment: InlineFragment, text: str) -> InlineFragment:
        return InlineFragment(
            text=text,
            bold=fragment.bold,
            italic=fragment.italic,
            code=fragment.code,
            link=fragment.link,
        )

    def _ensure_space_for_line(self, pdf: FPDF, line_height: float) -> None:
        if pdf.get_y() + line_height <= pdf.h - pdf.b_margin:
            return
        pdf.add_page()

    def _inline_fragments_for_first_child(self, node) -> list[InlineFragment]:
        if not node.children:
            return []
        return inline_fragments_from_node(node.children[0])

    @contextmanager
    def _temporary_margins(self, pdf: FPDF, *, left: float, right: float):
        previous_left = pdf.l_margin
        previous_right = pdf.r_margin
        previous_x = pdf.get_x()
        pdf.set_left_margin(left)
        pdf.set_right_margin(right)
        if pdf.get_x() < left:
            pdf.set_x(left)
        try:
            yield
        finally:
            pdf.set_left_margin(previous_left)
            pdf.set_right_margin(previous_right)
            pdf.set_x(max(previous_left, previous_x))

    @staticmethod
    def _normalize_for_pdf(text: str | None) -> str:
        if text is None:
            return ""
        return (
            text.replace("\u00A0", " ")
            .replace("\u202F", " ")
            .replace("\u2011", "-")
            .replace("\u00AD", "")
        )


def render_markdown_to_pdf_bytes(
    markdown_text: str,
    *,
    font_directory: str | Path,
    font_face: FontFace | Mapping[str, str],
    formatting_options: dict | None = None,
    image_resolver=None,
    image_base_dir: str | Path | None = None,
) -> bytes:
    renderer = MarkdownPdfRenderer(
        font_directory=font_directory,
        font_face=font_face,
        formatting_options=formatting_options,
        image_resolver=image_resolver,
        image_base_dir=image_base_dir,
    )
    return renderer.render_to_bytes(markdown_text)


def render_markdown_to_pdf_file(
    markdown_text: str,
    output_path: str | Path,
    *,
    font_directory: str | Path,
    font_face: FontFace | Mapping[str, str],
    formatting_options: dict | None = None,
    image_resolver=None,
    image_base_dir: str | Path | None = None,
) -> Path:
    renderer = MarkdownPdfRenderer(
        font_directory=font_directory,
        font_face=font_face,
        formatting_options=formatting_options,
        image_resolver=image_resolver,
        image_base_dir=image_base_dir,
    )
    return renderer.render_to_file(markdown_text, output_path)
