from __future__ import annotations

import pytest

from jupyter_book_marimo.authoring import (
    cell_from_directive,
    config_from_directive,
)


def directive(
    arg: str = "python",
    body: str = "x = 1",
    options: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "name": "marimo",
        "arg": arg,
        "body": body,
        "options": options or {},
        "node": {"position": {"start": {"line": 3}}},
    }


def test_marimo_directive_accepts_supported_languages() -> None:
    assert cell_from_directive(directive("python")).options["language"] == "python"
    assert cell_from_directive(directive("sql")).options["language"] == "sql"
    assert cell_from_directive(directive("markdown")).options["language"] == "markdown"


def test_marimo_directive_normalizes_canonical_kebab_case_options() -> None:
    cell = cell_from_directive(
        directive(
            "sql",
            "select 1",
            {
                "query": "rows",
                "hide-output": True,
                "hide-code": True,
                "column": 2,
            },
        )
    )

    assert cell.options == {
        "language": "sql",
        "query": "rows",
        "hide_output": True,
        "hide_code": True,
        "column": 2,
    }


def test_marimo_directive_rejects_unknown_language() -> None:
    with pytest.raises(ValueError, match="Unsupported marimo language"):
        cell_from_directive(directive("py"))


def test_marimo_directive_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match="Unsupported marimo option"):
        cell_from_directive(directive(options={"hide_code": True}))


def test_marimo_directive_rejects_unimplemented_warning_option() -> None:
    with pytest.raises(ValueError, match="Unsupported marimo option"):
        cell_from_directive(directive(options={"warning": False}))


def test_marimo_directive_rejects_sql_options_on_python() -> None:
    with pytest.raises(ValueError, match="SQL-only"):
        cell_from_directive(directive("python", options={"query": "rows"}))


def test_marimo_directive_rejects_conflicting_options() -> None:
    with pytest.raises(ValueError, match="Conflicting"):
        cell_from_directive(directive(options={"echo": True, "hide-code": True}))


def test_marimo_config_directive_uses_canonical_options() -> None:
    config = config_from_directive(
        {
            "name": "marimo-config",
            "options": {
                "eval": False,
                "external-env": True,
                "header": "import marimo as mo",
            },
        }
    )

    assert config == {
        "eval": False,
        "external_env": True,
        "header": "import marimo as mo",
    }


def test_marimo_config_rejects_pyproject_with_external_env() -> None:
    with pytest.raises(ValueError, match="external-env and pyproject"):
        config_from_directive(
            {
                "name": "marimo-config",
                "options": {
                    "external-env": True,
                    "pyproject": 'dependencies = ["marimo"]',
                },
            }
        )
