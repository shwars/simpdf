from __future__ import annotations

from copy import deepcopy


DEFAULT_FORMATTING_OPTIONS = {
    "page": {
        "format": "A4",
        "orientation": "P",
        "margins": {
            "left": 15,
            "top": 15,
            "right": 15,
            "bottom": 15,
        },
    },
    "text": {
        "font_size": 12,
        "line_height": 1.5,
        "color": (0, 0, 0),
    },
    "headings": {
        "sizes": {
            1: 22,
            2: 20,
            3: 18,
            4: 16,
            5: 14,
            6: 12,
        },
        "line_height": 1.3,
        "spacing_before": {
            1: 2.0,
            2: 1.8,
            3: 1.6,
            4: 1.4,
            5: 1.2,
            6: 1.0,
        },
        "spacing_after": {
            1: 3.5,
            2: 3.0,
            3: 2.5,
            4: 2.0,
            5: 1.5,
            6: 1.5,
        },
    },
    "paragraph": {
        "spacing_after": 3.0,
    },
    "lists": {
        "indent": 7.0,
        "bullet": "\u2022",
        "item_spacing_after": 1.5,
        "block_spacing_after": 1.5,
    },
    "blockquote": {
        "indent": 8.0,
        "bar_width": 0.8,
        "bar_gap": 2.0,
        "text_color": (90, 90, 90),
        "spacing_after": 3.0,
    },
    "table": {
        "font_size": 11,
        "heading_font_size": 12,
        "line_height": 6.0,
        "cell_padding": 1.3,
        "min_col_width": 24.0,
        "spacing_after": 2.5,
    },
    "code_block": {
        "font_size": 10,
        "line_height": 5.5,
        "padding": 2.0,
        "background_color": (245, 245, 245),
        "text_color": (40, 40, 40),
        "spacing_after": 3.0,
    },
    "inline_code": {
        "text_color": (120, 50, 20),
    },
    "images": {
        "max_width": 160.0,
        "max_height": 120.0,
        "spacing_before": 2.0,
        "spacing_after": 3.0,
        "align": "center",
        "table_cell_max_height": 24.0,
    },
    "links": {
        "color": (0, 102, 204),
        "underline": True,
    },
    "thematic_break": {
        "spacing_before": 2.0,
        "spacing_after": 4.0,
        "width": 0.4,
        "color": (160, 160, 160),
    },
}


def merge_formatting_options(overrides: dict | None = None) -> dict:
    merged = deepcopy(DEFAULT_FORMATTING_OPTIONS)
    if overrides:
        _deep_update(merged, overrides)
    _normalize_heading_keys(merged.get("headings", {}))
    return merged


def _deep_update(target: dict, updates: dict) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
            continue
        target[key] = value


def _normalize_heading_keys(headings: dict) -> None:
    for key in ("sizes", "spacing_before", "spacing_after"):
        values = headings.get(key)
        if not isinstance(values, dict):
            continue
        normalized = {}
        for subkey, value in values.items():
            try:
                normalized[int(subkey)] = value
            except (TypeError, ValueError):
                normalized[subkey] = value
        headings[key] = normalized
