from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


@dataclass(frozen=True)
class InlineFragment:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = None


@dataclass(frozen=True)
class MarkdownImage:
    alt_text: str
    source: str


@dataclass(frozen=True)
class ParagraphElement:
    fragments: tuple[InlineFragment, ...] = ()
    image: MarkdownImage | None = None

    @property
    def is_image(self) -> bool:
        return self.image is not None


@dataclass(frozen=True)
class TableCellContent:
    text: str
    image: MarkdownImage | None = None
    has_mixed_content: bool = False


def create_markdown_parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table").enable("strikethrough")


def parse_markdown_tree(text: str, parser: MarkdownIt | None = None) -> SyntaxTreeNode:
    active_parser = parser or create_markdown_parser()
    return SyntaxTreeNode(active_parser.parse(text or ""))


def inline_fragments_from_node(node: SyntaxTreeNode) -> list[InlineFragment]:
    return _collect_inline_fragments(node, bold=False, italic=False, code=False, link=None)


def plain_text_from_node(node: SyntaxTreeNode) -> str:
    return "".join(fragment.text for fragment in inline_fragments_from_node(node))


def paragraph_elements_from_node(node: SyntaxTreeNode) -> list[ParagraphElement]:
    if not node.children:
        return []

    elements: list[ParagraphElement] = []
    current_fragments: list[InlineFragment] = []

    for child in node.children:
        if child.type == "image":
            if current_fragments:
                elements.append(ParagraphElement(fragments=tuple(current_fragments)))
                current_fragments = []
            elements.append(ParagraphElement(image=_image_from_node(child)))
            continue
        current_fragments.extend(
            _collect_inline_fragments(child, bold=False, italic=False, code=False, link=None)
        )

    if current_fragments:
        elements.append(ParagraphElement(fragments=tuple(current_fragments)))
    return elements


def table_rows_from_node(table_node: SyntaxTreeNode) -> tuple[list[TableCellContent], list[list[TableCellContent]]]:
    header: list[TableCellContent] = []
    rows: list[list[TableCellContent]] = []

    for child in table_node.children or []:
        if child.type == "thead":
            header = [_cell_content(cell) for row in child.children or [] for cell in row.children or []]
        elif child.type == "tbody":
            for row in child.children or []:
                rows.append([_cell_content(cell) for cell in row.children or []])

    return header, rows


def _cell_content(cell_node: SyntaxTreeNode) -> TableCellContent:
    if not cell_node.children:
        return TableCellContent(text="")

    elements = paragraph_elements_from_node(cell_node.children[0])
    image_parts = [element.image for element in elements if element.image is not None]
    text_parts = [fragment.text for element in elements for fragment in element.fragments]
    alt_text_parts = [image.alt_text for image in image_parts if image and image.alt_text]
    normalized_text = "".join(text_parts + alt_text_parts).strip()

    if len(elements) == 1 and image_parts and not text_parts:
        return TableCellContent(text=image_parts[0].alt_text, image=image_parts[0], has_mixed_content=False)

    return TableCellContent(
        text=normalized_text,
        image=image_parts[0] if image_parts else None,
        has_mixed_content=bool(image_parts) and bool(text_parts or len(image_parts) > 1),
    )


def _image_from_node(node: SyntaxTreeNode) -> MarkdownImage:
    source = node.attrs.get("src", "")
    alt_text = node.content or "".join(child.content for child in node.children or [] if child.type == "text")
    return MarkdownImage(alt_text=alt_text, source=source)


def _collect_inline_fragments(
    node: SyntaxTreeNode,
    *,
    bold: bool,
    italic: bool,
    code: bool,
    link: str | None,
) -> list[InlineFragment]:
    node_type = node.type
    if node_type == "text":
        if not node.content:
            return []
        return [InlineFragment(text=node.content, bold=bold, italic=italic, code=code, link=link)]

    if node_type in {"softbreak", "hardbreak"}:
        return [InlineFragment(text="\n", bold=bold, italic=italic, code=code, link=link)]

    if node_type == "code_inline":
        return [InlineFragment(text=node.content, bold=bold, italic=italic, code=True, link=link)]

    next_bold = bold or node_type == "strong"
    next_italic = italic or node_type == "em"
    next_link = node.attrs.get("href", link) if node_type == "link" else link

    fragments: list[InlineFragment] = []
    for child in node.children or []:
        fragments.extend(
            _collect_inline_fragments(
                child,
                bold=next_bold,
                italic=next_italic,
                code=code,
                link=next_link,
            )
        )
    return fragments
