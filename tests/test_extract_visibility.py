from __future__ import annotations

import pytest
from extract_helpers import (
    assignment_values,
    code_blocks,
    code_editor_values,
    marimo_cell_output_html,
    marimo_cell_output_text,
    marimo_island_attrs,
    run_extract,
    single_marimo_island_attrs,
)


def test_page_eval_false_skips_execution_and_honors_echo() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {"eval": False, "echo": True},
            "cells": [
                {
                    "code": 'raise RuntimeError("should not run")',
                    "options": {"language": "python"},
                }
            ],
        }
    )

    output = result["outputs"][0]
    assert code_blocks(output["html"]) == [
        ("python", 'raise RuntimeError("should not run")')
    ]
    assert "appId" not in output
    assert marimo_island_attrs(output["html"]) == []


def test_page_eval_false_with_header_does_not_render_unbuilt_header() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {
                "eval": False,
                "echo": True,
                "header": "import marimo as mo\nsetup_value = 1",
            },
            "cells": [
                {
                    "code": "setup_value",
                    "options": {"language": "python"},
                }
            ],
        }
    )

    output = result["outputs"][0]
    assert code_blocks(output["html"]) == [("python", "setup_value")]
    assert "appId" not in output
    assert marimo_island_attrs(output["html"]) == []
    assert output["widgetConfig"] == {"molab": {"enabled": True}}


def test_cell_eval_false_skips_execution() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": 'raise RuntimeError("should not run")',
                    "options": {"language": "python", "eval": False, "echo": True},
                }
            ],
        }
    )

    output = result["outputs"][0]
    assert code_blocks(output["html"]) == [
        ("python", 'raise RuntimeError("should not run")')
    ]
    assert "appId" not in output
    assert marimo_island_attrs(output["html"]) == []


def test_include_false_renders_intentionally_empty_output() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "x = 1",
                    "options": {"language": "python", "include": False},
                }
            ],
        }
    )

    assert result["outputs"] == [
        {"html": "", "widgetConfig": {"molab": {"enabled": True}}}
    ]


def test_include_false_still_executes_for_later_cells() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {
                    "startLine": 1,
                    "code": "hidden_value = 41",
                    "options": {"include": False},
                },
                {
                    "startLine": 5,
                    "code": "hidden_value + 1",
                },
            ],
        }
    )

    assert result["outputs"][0]["appId"] == result["outputs"][1]["appId"]
    assert (
        single_marimo_island_attrs(result["outputs"][0]["html"])["data-cell-idx"] == "0"
    )
    assert marimo_cell_output_html(result["outputs"][0]["html"]).strip() == ""
    assert marimo_cell_output_text(result["outputs"][1]["html"]) == "42"
    assert (
        single_marimo_island_attrs(result["outputs"][1]["html"])["data-cell-idx"] == "1"
    )


def test_error_false_fails_the_build_on_execution_error() -> None:
    with pytest.raises(RuntimeError, match=r"docs/tutorials/test.md:2"):
        run_extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {"error": False},
                "cells": [
                    {"startLine": 2, "code": "planet = 'Mars'\nplanet"},
                    {"startLine": 7, "code": "planet = 'Earth'\nplanet"},
                ],
            }
        )


def test_error_false_marks_output_for_browser_mime_suppression() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {"error": False},
            "cells": [{"code": "1"}],
        }
    )

    assert set(result["outputs"][0]["suppressMimetypes"]) == {
        "application/vnd.marimo+error",
        "application/vnd.marimo+traceback",
    }


def test_error_false_fails_with_server_output_false() -> None:
    with pytest.raises(RuntimeError, match=r"docs/tutorials/test.md:2"):
        run_extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {"error": False, "server_output": False},
                "cells": [
                    {"startLine": 2, "code": 'raise RuntimeError("boom")'},
                ],
            }
        )


def test_error_false_fails_on_compile_error() -> None:
    with pytest.raises(RuntimeError, match=r"docs/tutorials/test.md:2"):
        run_extract(
            {
                "file": "docs/tutorials/test.md",
                "metadata": {"error": False},
                "cells": [
                    {
                        "startLine": 2,
                        "code": "print('broken'",
                        "options": {"language": "python", "echo": True},
                    },
                ],
            }
        )


def test_output_false_cell_executes_for_later_cells() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {"code": "hidden_value = 41", "options": {"output": False}},
                {"code": "hidden_value + 1"},
            ],
        }
    )

    first, second = result["outputs"]
    assert first["appId"] == second["appId"]
    assert single_marimo_island_attrs(first["html"])["data-cell-idx"] == "0"
    assert marimo_cell_output_html(first["html"]).strip() == ""
    assert assignment_values(first["notebookCode"], "hidden_value") == [41]
    assert first["assets"]["moduleScripts"]
    assert second["appId"]
    assert marimo_cell_output_text(second["html"]) == "42"
    assert single_marimo_island_attrs(second["html"])["data-cell-idx"] == "1"


def test_output_false_with_editor_keeps_source_editor_and_empty_output() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "hidden_value = 41\nhidden_value",
                    "options": {"output": False, "editor": True},
                },
            ],
        }
    )

    output = result["outputs"][0]
    assert output["appId"]
    assert assignment_values(output["notebookCode"], "hidden_value") == [41]
    assert output["assets"]["moduleScripts"]
    island_attrs = single_marimo_island_attrs(output["html"])
    assert island_attrs["data-jupyter-book-marimo-hide-output"] == "true"
    assert code_editor_values(output["html"]) == ["hidden_value = 41\nhidden_value"]
    assert marimo_cell_output_html(output["html"]).strip() == ""


def test_output_false_single_cell_carries_runtime_payload() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "hidden_value = 41\nhidden_value",
                    "options": {"output": False},
                },
            ],
        }
    )

    output = result["outputs"][0]
    assert output["appId"]
    assert assignment_values(output["notebookCode"], "hidden_value") == [41]
    assert output["assets"]["moduleScripts"]
    assert output["runtimeCellCount"] == 1
    assert single_marimo_island_attrs(output["html"])["data-cell-idx"] == "0"
    assert marimo_cell_output_html(output["html"]).strip() == ""


def test_output_false_with_editor_preserves_later_cell_index() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {
                    "code": "hidden_value = 41\nhidden_value",
                    "options": {"output": False, "editor": True},
                },
                {"code": "hidden_value + 1"},
            ],
        }
    )

    first, second = result["outputs"]
    assert first["appId"] == second["appId"]
    assert first["assets"]["moduleScripts"]
    assert assignment_values(first["notebookCode"], "hidden_value") == [41]
    first_attrs = single_marimo_island_attrs(first["html"])
    assert first_attrs["data-cell-idx"] == "0"
    assert first_attrs["data-jupyter-book-marimo-hide-output"] == "true"
    assert code_editor_values(first["html"]) == ["hidden_value = 41\nhidden_value"]
    assert marimo_cell_output_text(second["html"]) == "42"
    assert single_marimo_island_attrs(second["html"])["data-cell-idx"] == "1"


def test_page_hide_output_allows_later_output_override() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {"hide_output": True},
            "cells": [
                {"code": "hidden_value = 41"},
                {"code": "hidden_value + 1", "options": {"hide_output": False}},
            ],
        }
    )

    first, second = result["outputs"]
    assert first["appId"] == second["appId"]
    assert single_marimo_island_attrs(first["html"])["data-cell-idx"] == "0"
    assert marimo_cell_output_html(first["html"]).strip() == ""
    assert marimo_cell_output_text(second["html"]) == "42"


def test_server_output_false_keeps_runtime_payload_and_empty_static_html() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {"server_output": False},
            "cells": [
                {"code": "x = 1"},
                {"code": "x"},
            ],
        }
    )

    first, second = result["outputs"]
    assert first["appId"] == second["appId"]
    assert assignment_values(first["notebookCode"], "x") == [1]
    assert first["assets"]["moduleScripts"]
    assert single_marimo_island_attrs(first["html"])["data-cell-idx"] == "0"
    assert single_marimo_island_attrs(second["html"])["data-cell-idx"] == "1"
    assert marimo_cell_output_html(first["html"]).strip() == ""
    assert marimo_cell_output_html(second["html"]).strip() == ""


def test_cell_server_output_overrides_page_server_output_default() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {"server_output": False},
            "cells": [
                {"code": "value = 7"},
                {
                    "code": "value",
                    "options": {"server_output": True},
                },
            ],
        }
    )

    first, second = result["outputs"]
    assert marimo_cell_output_html(first["html"]).strip() == ""
    assert marimo_cell_output_text(second["html"]) == "7"
