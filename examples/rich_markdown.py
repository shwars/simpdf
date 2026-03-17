from pathlib import Path

from simpdf import FontFace, MarkdownPdfRenderer


ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
OUTPUT = ROOT / "examples" / "rich_markdown.pdf"

markdown_text = """
# Rich Markdown

Параграф со [ссылкой](https://example.com), **жирным** текстом, *курсивом* и `inline code`.

> Это блок-цитата. Она рендерится с отступом и вертикальной линией.

1. Первый шаг
2. Второй шаг

---

| Имя | Значение | Описание |
| --- | --- | --- |
| Один | 1 | Таблица с длинным текстом для проверки переноса и ширины колонок. |
| Два | 2 | Вторая строка для проверки общего вида таблицы. |

```python
def hello(name: str) -> str:
    return f"Hello, {name}"
```
"""

renderer = MarkdownPdfRenderer(
    font_directory=FONTS_DIR,
    font_face=FontFace.dejavu_sans(),
)

renderer.render_to_file(markdown_text, OUTPUT)
print(f"Wrote {OUTPUT}")
