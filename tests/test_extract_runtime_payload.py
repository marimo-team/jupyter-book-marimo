from __future__ import annotations

import ast

from extract_helpers import marimo_island_indices, run_extract


def imported_modules(code: str) -> set[str]:
    tree = ast.parse(code)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".", maxsplit=1)[0])
    return modules


def app_id_for_identity(identity: str) -> str:
    result = run_extract(
        {
            "file": identity,
            "identity": identity,
            "metadata": {},
            "cells": [{"code": "x = 1"}],
        }
    )
    return str(result["outputs"][0]["appId"])


def test_runtime_app_id_is_stable_for_page_identity() -> None:
    assert app_id_for_identity("docs/api/intro.md") == app_id_for_identity(
        "docs/api/intro.md"
    )
    assert app_id_for_identity("docs/api/intro.md") != app_id_for_identity(
        "docs/api/reference.md"
    )


def test_extract_emits_runtime_fields_once_for_executable_cells() -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {},
            "cells": [
                {"code": "x = 1"},
                {"code": "x"},
            ],
        }
    )

    first, second = result["outputs"]
    assert first["appId"] == second["appId"]
    assert first["runtimeCellCount"] == 2
    for field in ("notebookCode", "molabNotebookCode"):
        code = first[field]
        compile(code, f"<{field}>", "exec")
        assert "jupyter_book_marimo" not in imported_modules(code)
    assert first["assets"]["version"]
    assert first["assets"]["moduleScripts"]
    runtime_outputs = [
        output
        for output in result["outputs"]
        if output.get("notebookCode") and output.get("assets")
    ]
    assert runtime_outputs == [first]
    assert [marimo_island_indices(output["html"]) for output in result["outputs"]] == [
        ["0"],
        ["1"],
    ]
