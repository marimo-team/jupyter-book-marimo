from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from helpers import compiled_cell, compiled_page

from jupyter_book_marimo.plugin import directive_nodes, transform_document


def test_plugin_command_declares_directives_and_document_transform() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "jupyter_book_marimo"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    spec = json.loads(result.stdout)
    assert {directive["name"] for directive in spec["directives"]} == {
        "marimo",
        "marimo-config",
    }
    assert [
        (transform["name"], transform["stage"]) for transform in spec["transforms"]
    ] == [("marimo-islands", "document")]


def test_transform_compiles_page_once_and_projects_all_cells(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tree = {
        "type": "root",
        "children": [
            *directive_nodes(
                "marimo",
                {"arg": "python", "body": "x = 1", "options": {}},
            ),
            *directive_nodes(
                "marimo",
                {"arg": "python", "body": "x + 1", "options": {}},
            ),
        ],
    }
    monkeypatch.chdir(tmp_path)
    with patch(
        "jupyter_book_marimo.plugin.run_page_compiler",
        return_value=compiled_page(compiled_cell(0), compiled_cell(1)),
    ) as run:
        result = transform_document(tree)

    assert run.call_count == 1
    assert [node["type"] for node in result["children"]] == [
        "anywidget",
        "anywidget",
    ]
    assert result["children"][0]["model"]["payload"]["app"]["id"] == "marimo-test"
    assert result["children"][1]["model"]["payload"]["appId"] == "marimo-test"


def test_transform_consumes_config_from_pages_without_cells() -> None:
    tree = {
        "type": "root",
        "children": [
            {"type": "marimoConfig", "config": {}},
            {"type": "paragraph", "children": []},
        ],
    }

    assert transform_document(tree)["children"] == [
        {"type": "paragraph", "children": []}
    ]
