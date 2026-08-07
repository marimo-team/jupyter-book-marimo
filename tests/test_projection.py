from __future__ import annotations

from pathlib import Path

import pytest
from helpers import compiled_cell, compiled_page

from jupyter_book_marimo.document import CollectedDocument, collect_document
from jupyter_book_marimo.projection import project_page


def collected_document() -> CollectedDocument:
    return collect_document(
        {
            "type": "root",
            "children": [
                {
                    "type": "marimoCell",
                    "value": "x = 1",
                    "options": {"language": "python"},
                },
                {
                    "type": "marimoCell",
                    "value": "x + 1",
                    "options": {"language": "python"},
                },
            ],
        }
    )


def test_projection_carries_one_app_and_references_it_for_siblings(
    tmp_path: Path,
) -> None:
    document = collected_document()
    page = compiled_page(compiled_cell(0), compiled_cell(1))

    replacements = project_page(document, page, root=tmp_path)
    nodes = [replacements[item.node_id] for item in document.cells]

    assert all(node is not None for node in nodes)
    assert nodes[0]["model"]["payload"]["app"]["id"] == "marimo-test"
    assert nodes[1]["model"]["payload"]["appId"] == "marimo-test"
    assert all("output" not in node["model"]["payload"]["cell"] for node in nodes)
    assert all(node["esm"].endswith("/container-widget.mjs") for node in nodes)
    assert all(node["css"].endswith("/islands-bridge.css") for node in nodes)
    assert (tmp_path / ".jupyter-book-marimo/container-widget.mjs").is_file()
    assert (tmp_path / ".jupyter-book-marimo/islands-bridge.css").is_file()


def test_projection_omits_cells_excluded_by_compiler(tmp_path: Path) -> None:
    document = collected_document()
    page = compiled_page(compiled_cell(0, include=False), compiled_cell(1))

    replacements = project_page(document, page, root=tmp_path)

    assert replacements[document.cells[0].node_id] is None
    included = replacements[document.cells[1].node_id]
    assert included is not None
    assert included["model"]["payload"]["app"]


def test_projection_requires_compiler_indices_to_match_document(
    tmp_path: Path,
) -> None:
    document = collected_document()
    page = compiled_page(compiled_cell(1), compiled_cell(0))

    with pytest.raises(RuntimeError, match="expected \\[0, 1\\]"):
        project_page(document, page, root=tmp_path)
