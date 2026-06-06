from __future__ import annotations

import pytest
from extract_helpers import (
    MarimoCellOutputParser,
    assignment_values,
    future_import_names,
    marimo_cell_output_tags,
    marimo_cell_output_text,
    marimo_cell_output_texts,
    marimo_island_attrs,
    marimo_island_indices,
    marimo_mime_payloads,
    run_extract,
)


def test_markdown_directive_executes_without_user_marimo_import() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "hello **marimo**",
                    "options": {"language": "markdown"},
                }
            ],
        }
    )

    assert marimo_cell_output_text(result["outputs"][0]["html"]) == "hello marimo"
    assert "strong" in marimo_cell_output_tags(result["outputs"][0]["html"])


def test_repeated_markdown_directives_share_default_marimo_alias() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "identity": "docs/api/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "first **cell**",
                    "options": {"language": "markdown"},
                },
                {
                    "code": "second **cell**",
                    "options": {"language": "markdown"},
                },
            ],
        }
    )

    first, second = result["outputs"]
    assert marimo_island_indices(first["html"]) == ["0", "1"]
    assert marimo_island_indices(second["html"]) == ["2"]
    assert [text for text in marimo_cell_output_texts(first["html"]) if text] == [
        "first cell"
    ]
    assert marimo_cell_output_text(second["html"]) == "second cell"


def test_python_cell_does_not_receive_default_marimo_import() -> None:
    with pytest.raises(RuntimeError, match=r"docs/api/test.md:1"):
        run_extract(
            {
                "file": "docs/api/test.md",
                "metadata": {"error": False},
                "cells": [
                    {
                        "startLine": 1,
                        "code": "mo.md('plain python')",
                        "options": {"language": "python"},
                    }
                ],
            }
        )


def test_markdown_directive_reuses_user_marimo_import() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "identity": "docs/api/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "import marimo as mo",
                    "options": {"language": "python"},
                },
                {
                    "code": "uses **authored import**",
                    "options": {"language": "markdown"},
                },
            ],
        }
    )

    compile(result["outputs"][0]["notebookCode"], "<notebookCode>", "exec")
    assert marimo_cell_output_text(result["outputs"][1]["html"]) == (
        "uses authored import"
    )
    assert marimo_island_indices(result["outputs"][1]["html"]) == ["1"]


def test_converted_cells_keep_future_import_header_first() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "identity": "docs/api/test.md",
            "metadata": {
                "header": (
                    "from __future__ import annotations\nlabel: str = 'future header'"
                )
            },
            "cells": [
                {
                    "code": "uses **generated import**",
                    "options": {"language": "markdown"},
                }
            ],
        }
    )

    output = result["outputs"][0]
    assert future_import_names(output["notebookCode"]) == {"annotations"}
    assert future_import_names(output["molabNotebookCode"]) == {"annotations"}
    assert marimo_island_indices(output["html"]) == ["0", "1", "2"]
    assert [text for text in marimo_cell_output_texts(output["html"]) if text] == [
        "uses generated import"
    ]


def test_future_import_header_exports_executable_header_body() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "identity": "docs/api/test.md",
            "metadata": {
                "header": (
                    "from __future__ import annotations\nlabel: str = 'future header'"
                )
            },
            "cells": [
                {
                    "code": "label",
                    "options": {"language": "python"},
                }
            ],
        }
    )

    output = result["outputs"][0]
    assert len(marimo_island_attrs(output["html"])) == 2
    assert [text for text in marimo_cell_output_texts(output["html"]) if text] == [
        "'future header'"
    ]
    for code in (output["notebookCode"], output["molabNotebookCode"]):
        assert future_import_names(code) == {"annotations"}
        assert assignment_values(code, "label") == ["future header"]


def test_sql_directive_uses_default_marimo_import_before_sql_dependency_error() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "select 1 as value",
                    "options": {"language": "sql", "query": "rows"},
                }
            ],
        }
    )

    [payload] = marimo_mime_payloads(result["outputs"][0]["html"])
    [error] = payload
    assert error["exception_type"] == "ManyModulesNotFoundError"


def test_page_header_executes_before_cells_and_offsets_browser_indexes() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "identity": "docs/api/test.md",
            "metadata": {"header": "import marimo as mo\nlabel = 'from header'"},
            "cells": [
                {"code": "mo.md(label)"},
                {"code": "label"},
            ],
        }
    )

    first, second = result["outputs"]
    assert marimo_cell_output_text(first["html"]) == "from header"
    assert marimo_cell_output_text(second["html"]) == "'from header'"
    first_islands = marimo_island_attrs(first["html"])
    assert [attrs["data-cell-idx"] for attrs in first_islands] == ["0", "1"]
    assert first_islands[0]["hidden"] is None
    assert first_islands[0]["data-jupyter-book-marimo-hidden-cell"] == "true"
    assert marimo_island_indices(second["html"]) == ["2"]
    assert assignment_values(first["notebookCode"], "label") == ["from header"]
    compile(first["notebookCode"], "<notebookCode>", "exec")
    assert assignment_values(first["molabNotebookCode"], "label") == ["from header"]


def test_header_prefix_does_not_capture_first_cell_hide_output() -> None:
    result = run_extract(
        {
            "file": "docs/api/test.md",
            "identity": "docs/api/test.md",
            "metadata": {"header": "import marimo as mo\nlabel = 'from header'"},
            "cells": [
                {
                    "code": "mo.md(label)",
                    "options": {"output": False, "editor": True},
                }
            ],
        }
    )

    output = result["outputs"][0]
    islands = marimo_island_attrs(output["html"])
    assert len(islands) == 2
    header_attrs, authored_attrs = islands
    assert header_attrs["data-cell-idx"] == "0"
    assert header_attrs["hidden"] is None
    assert header_attrs["data-jupyter-book-marimo-hidden-cell"] == "true"
    assert authored_attrs["data-cell-idx"] == "1"
    assert authored_attrs["data-jupyter-book-marimo-hide-output"] == "true"
    parser = MarimoCellOutputParser()
    parser.feed(output["html"])
    assert all(cell_output.strip() == "" for cell_output in parser.outputs)


def test_header_execution_error_fails_the_build() -> None:
    with pytest.raises(RuntimeError, match=r"docs/api/test.md:header"):
        run_extract(
            {
                "file": "docs/api/test.md",
                "metadata": {
                    "header": "raise RuntimeError('header boom')",
                },
                "cells": [{"code": "1"}],
            }
        )
