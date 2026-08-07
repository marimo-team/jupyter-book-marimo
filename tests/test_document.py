from __future__ import annotations

import pytest

from jupyter_book_marimo.document import (
    collect_document,
)


def cell_node(source: str, line: int = 1) -> dict[str, object]:
    return {
        "type": "marimoCell",
        "value": source,
        "options": {"language": "python"},
        "position": {
            "start": {"line": line},
            "end": {"line": line + 2},
        },
    }


def test_document_collects_nested_cells_into_one_page_request() -> None:
    first = cell_node("x = 1", 4)
    second = cell_node("x + 1", 12)
    tree = {
        "type": "root",
        "children": [
            {
                "type": "marimoConfig",
                "config": {
                    "defaults": {"render": {"source": True}},
                    "header": "seed = 4",
                    "pyproject": "",
                    "externalEnv": False,
                },
            },
            first,
            {"type": "section", "children": [second]},
        ],
    }

    document = collect_document(tree)
    request = document.page_request()

    assert [cell.source for cell in request.cells] == ["x = 1", "x + 1"]
    assert request.cells[1].start_line == 12
    assert request.defaults == {"render": {"source": True}}
    assert request.metadata.setup_cells[0].source == "seed = 4"


def test_page_identity_uses_content_and_ignores_source_positions() -> None:
    first = collect_document(
        {"type": "root", "children": [cell_node("x = 1", 2)]}
    ).page_request()
    moved = collect_document(
        {"type": "root", "children": [cell_node("x = 1", 200)]}
    ).page_request()
    changed = collect_document(
        {"type": "root", "children": [cell_node("x = 2", 2)]}
    ).page_request()

    assert first.identity == moved.identity
    assert first.identity != changed.identity


def test_document_rejects_multiple_page_configs() -> None:
    tree = {
        "type": "root",
        "children": [
            {"type": "marimoConfig", "config": {}},
            {"type": "marimoConfig", "config": {}},
        ],
    }

    with pytest.raises(ValueError, match="Only one marimo-config"):
        collect_document(tree)
