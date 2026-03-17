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


def create_markdown_parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table").enable("strikethrough")


def parse_markdown_tree(text: str, parser: MarkdownIt | None = None) -> SyntaxTreeNode:
    active_parser = parser or create_markdown_parser()
    return SyntaxTreeNode(active_parser.parse(text or ""))


def inline_fragments_from_node(node: SyntaxTreeNode) -> list[InlineFragment]:
    return _collect_inline_fragments(node, bold=False, italic=False, code=False, link=None)


def plain_text_from_node(node: SyntaxTreeNode) -> str:
    return "".join(fragment.text for fragment in inline_fragments_from_node(node))


def table_rows_from_node(table_node: SyntaxTreeNode) -> tuple[list[str], list[list[str]]]:
    header: list[str] = []
    rows: list[list[str]] = []

    for child in table_node.children or []:
        if child.type == "thead":
            header = [_cell_text(cell) for row in child.children or [] for cell in row.children or []]
        elif child.type == "tbody":
            for row in child.children or []:
                rows.append([_cell_text(cell) for cell in row.children or []])

    return header, rows


def _cell_text(cell_node: SyntaxTreeNode) -> str:
    if not cell_node.children:
        return ""
    return plain_text_from_node(cell_node.children[0]).strip()


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
