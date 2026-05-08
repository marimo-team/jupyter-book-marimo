from __future__ import annotations

import asyncio
import warnings

from jupyter_book_marimo import extract


def test_marimo_version_is_a_floor() -> None:
    assert extract.MIN_MARIMO_VERSION == "0.23.5"
    assert extract.version_tuple("0.23.6") > extract.version_tuple(
        extract.MIN_MARIMO_VERSION
    )


def test_output_model_omits_empty_runtime_fields() -> None:
    assert extract.output_model("<p>ok</p>") == {"html": "<p>ok</p>"}


def test_output_model_includes_page_runtime_fields() -> None:
    assert extract.output_model(
        "<marimo-island></marimo-island>",
        app_id="jb-test",
        notebook_code="app code",
        assets={"moduleScripts": ["/runtime.js"], "links": []},
    ) == {
        "html": "<marimo-island></marimo-island>",
        "appId": "jb-test",
        "notebookCode": "app code",
        "assets": {"moduleScripts": ["/runtime.js"], "links": []},
    }


def test_source_for_plain_python_cell_is_passthrough() -> None:
    assert extract.source_for_cell({"code": "x = 1"}) == "x = 1"


def test_source_for_sql_cell_uses_inferred_language() -> None:
    source = extract.source_for_cell(
        {
            "code": "select * from numbers",
            "options": {"language": "sql", "query": "numbers"},
        }
    )

    assert "mo.sql" in source
    assert "select * from numbers" in source


def test_disabled_sql_fallback_displays_original_source() -> None:
    result = asyncio.run(
        extract.extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {},
                "cells": [
                    {
                        "code": "select * from numbers",
                        "options": {
                            "language": "sql",
                            "disabled": True,
                            "echo": True,
                        },
                    }
                ],
            }
        )
    )

    html = result["outputs"][0]["html"]
    assert "select * from numbers" in html
    assert "language-sql" in html
    assert "mo.sql" not in html


def test_as_bool_defaults_missing_values() -> None:
    assert extract.as_bool(None, True) is True
    assert extract.as_bool(None) is False


def test_pyproject_to_script_metadata_wraps_toml() -> None:
    assert (
        extract.pyproject_to_script_metadata('dependencies = ["marimo>=0.23.5"]')
        == '# /// script\n# dependencies = ["marimo>=0.23.5"]\n# ///\n'
    )


def test_page_cell_prefix_is_stable_and_page_specific() -> None:
    assert extract.page_cell_prefix(
        "docs/tutorials/intro.md"
    ) == extract.page_cell_prefix("docs/tutorials/intro.md")
    assert extract.page_cell_prefix(
        "docs/tutorials/intro.md"
    ) != extract.page_cell_prefix("docs/tutorials/dataflow.md")


def test_reactive_islands_use_browser_cell_indexes() -> None:
    island = (
        '<marimo-island data-app-id="jb-test" '
        'data-cell-id="server-cell" data-reactive="true"></marimo-island>'
    )

    rewritten = extract.use_browser_cell_index(island, 3)

    assert 'data-cell-id="server-cell"' not in rewritten
    assert 'data-cell-idx="3"' in rewritten


def test_browser_notebook_uses_page_cell_prefix() -> None:
    notebook_code = "\n".join(
        [
            "import marimo",
            "",
            "app = marimo.App()",
            "",
            "@app.cell",
            "def _():",
            "    return",
        ]
    )

    rewritten = extract.install_browser_cell_prefix(notebook_code, "jbpage")

    assert "from marimo._ast.cell_manager import CellManager" in rewritten
    assert 'app._cell_manager = CellManager(prefix="jbpage")' in rewritten


def test_browser_notebook_cell_prefix_handles_formatted_app_constructor() -> None:
    notebook_code = "\n".join(
        [
            "import marimo as mo",
            "import marimo",
            "",
            'app = marimo.App(width="full")',
            "",
        ]
    )

    rewritten = extract.install_browser_cell_prefix(notebook_code, "jbpage")

    assert 'app = marimo.App(width="full")' in rewritten
    assert 'app._cell_manager = CellManager(prefix="jbpage")' in rewritten


def test_browser_notebook_cell_prefix_reports_missing_app_constructor() -> None:
    try:
        extract.install_browser_cell_prefix("import marimo\n", "jbpage")
    except ValueError as exc:
        assert "cell prefix" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_extract_repeats_runtime_fields_for_executable_cells() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            module=r"marimo\._session\.session",
        )
        result = asyncio.run(
            extract.extract(
                {
                    "file": "docs/tutorials/test.md",
                    "metadata": {},
                    "cells": [
                        {"code": "x = 1"},
                        {"code": "x"},
                    ],
                }
            )
        )

    for output in result["outputs"]:
        assert output["appId"] == result["outputs"][0]["appId"]
        assert "notebookCode" in output
        assert (
            f'CellManager(prefix="{extract.page_cell_prefix("docs/tutorials/test.md")}")'
            in output["notebookCode"]
        )
        assert output["assets"]["moduleScripts"]
        assert "data-cell-idx" in output["html"]
        assert 'data-cell-id="' not in output["html"]
