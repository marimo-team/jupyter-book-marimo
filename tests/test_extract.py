from __future__ import annotations

import ast

import pytest
from extract_helpers import (
    code_blocks,
    marimo_mime_payloads,
    marimo_mimetypes,
    run_extract,
)

from jupyter_book_marimo.cell_plan import CellPlan
from jupyter_book_marimo.island_output import (
    suppress_mime_renderers,
)


def sql_assignment(source: str) -> tuple[str, ast.Call]:
    tree = ast.parse(source)
    [assign] = [node for node in tree.body if isinstance(node, ast.Assign)]
    [target] = assign.targets
    assert isinstance(target, ast.Name)
    assert isinstance(assign.value, ast.Call)
    assert isinstance(assign.value.func, ast.Attribute)
    assert isinstance(assign.value.func.value, ast.Name)
    assert assign.value.func.value.id == "mo"
    assert assign.value.func.attr == "sql"
    return target.id, assign.value


def sql_contains(source: str, text: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and text in node.value
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize(
    ("metadata", "widget_config"),
    [
        ({}, {"molab": {"enabled": True}}),
        ({"molab": False}, {"molab": {"enabled": False}}),
        ({"molab": True}, {"molab": {"enabled": True}}),
    ],
)
def test_extract_attaches_widget_config_to_static_outputs(
    metadata: dict[str, object],
    widget_config: dict[str, object],
) -> None:
    result = run_extract(
        {
            "file": "docs/tutorials/test.md",
            "metadata": {"eval": False, **metadata},
            "cells": [{"code": "x = 1"}],
        }
    )

    output = result["outputs"][0]
    assert output == {"html": "", "widgetConfig": widget_config}


def test_suppress_mime_renderers_keeps_unblocked_mime_output() -> None:
    html = (
        "<marimo-cell-output>"
        "<marimo-mime-renderer "
        "data-mime='&quot;application/vnd.marimo+error&quot;' "
        "data-data='[]'></marimo-mime-renderer>"
        "<marimo-mime-renderer "
        "data-mime='&quot;text/plain&quot;' "
        "data-data='&quot;ok&quot;'></marimo-mime-renderer>"
        "</marimo-cell-output>"
    )

    filtered = suppress_mime_renderers(
        html,
        {"application/vnd.marimo+error"},
    )

    assert marimo_mimetypes(filtered) == ["text/plain"]
    assert marimo_mime_payloads(filtered) == ["ok"]


def test_suppress_mime_renderers_matches_data_mime_not_payload_text() -> None:
    html = (
        "<marimo-cell-output>"
        "<marimo-mime-renderer "
        "data-mime='&quot;text/plain&quot;' "
        "data-data='&quot;application/vnd.marimo+error&quot;'>"
        "</marimo-mime-renderer>"
        "</marimo-cell-output>"
    )

    filtered = suppress_mime_renderers(
        html,
        {"application/vnd.marimo+error"},
    )

    assert marimo_mimetypes(filtered) == ["text/plain"]
    assert marimo_mime_payloads(filtered) == ["application/vnd.marimo+error"]


def test_sql_cell_plan_uses_query_visibility_and_engine_in_executable_source() -> None:
    plan = CellPlan.from_payload(
        0,
        {
            "code": "select 1 as value",
            "options": {
                "language": "sql",
                "query": "rows",
                "hide_output": True,
                "engine": "engine",
            },
        },
        {},
    )

    target, call = sql_assignment(plan.executable_source)
    kwargs = {keyword.arg: keyword.value for keyword in call.keywords}
    assert target == "rows"
    assert isinstance(kwargs["output"], ast.Constant)
    assert kwargs["output"].value is False
    assert isinstance(kwargs["engine"], ast.Name)
    assert kwargs["engine"].id == "engine"
    assert sql_contains(plan.executable_source, "select 1 as value")


@pytest.mark.parametrize("query", ["not-valid", "class", "mo"])
def test_sql_query_target_falls_back_for_unsafe_names(query: str) -> None:
    plan = CellPlan.from_payload(
        0,
        {
            "code": "select 1 as value",
            "options": {"language": "sql", "query": query},
        },
        {},
    )

    fallback, _call = sql_assignment(plan.executable_source)
    assert fallback != query
    assert fallback.isidentifier()
    assert fallback != "mo"


def test_disabled_sql_fallback_displays_original_source() -> None:
    result = run_extract(
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

    html = result["outputs"][0]["html"]
    assert code_blocks(html) == [("sql", "select * from numbers")]
