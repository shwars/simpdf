from __future__ import annotations

from simpdf.markdown import inline_fragments_from_node, parse_markdown_tree, plain_text_from_node, table_rows_from_node


def test_inline_fragments_capture_bold_italic_code_and_links():
    tree = parse_markdown_tree("[link](https://example.com) and **bold** *italic* `code`")
    paragraph = tree.children[0]
    fragments = inline_fragments_from_node(paragraph.children[0])

    assert any(fragment.link == "https://example.com" and fragment.text == "link" for fragment in fragments)
    assert any(fragment.bold and fragment.text == "bold" for fragment in fragments)
    assert any(fragment.italic and fragment.text == "italic" for fragment in fragments)
    assert any(fragment.code and fragment.text == "code" for fragment in fragments)


def test_plain_text_from_node_flattens_inline_markup():
    tree = parse_markdown_tree("This is **bold** and [a link](https://example.com).")
    paragraph = tree.children[0]
    assert plain_text_from_node(paragraph.children[0]) == "This is bold and a link."


def test_table_rows_from_node_extracts_header_and_body():
    tree = parse_markdown_tree("| Name | Value |\n| --- | --- |\n| One | 1 |\n| Two | 2 |")
    table = tree.children[0]
    header, rows = table_rows_from_node(table)

    assert header == ["Name", "Value"]
    assert rows == [["One", "1"], ["Two", "2"]]
